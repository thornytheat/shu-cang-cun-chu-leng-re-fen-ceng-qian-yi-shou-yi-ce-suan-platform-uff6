"""TierPolicy 读取 / 版本化写入。

三档（热/温/冷）各一行，同一 version 构成一个"策略版本"；is_current=true 的那一组生效。
编辑 = 生成 version+1 的一组新行，旧组 is_current=false（历史留档，可追溯季度口径变化）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import StorageTier
from src.constants.log_templates import ACTION_POLICY_UPDATE
from src.models.tier_policy import TierPolicy
from src.models.user import User
from src.services import audit_service
from src.utils.errors import AppError
from src.utils.numeric import money

POLICY_CODES = {
    StorageTier.HOT: "POL-HOT",
    StorageTier.WARM: "POL-WARM",
    StorageTier.COLD: "POL-COLD",
}
POLICY_TITLES = {
    StorageTier.HOT: "热区：在线高带宽存储",
    StorageTier.WARM: "温区：低频标准存储",
    StorageTier.COLD: "冷区：对象存储归档",
}


@dataclass
class PolicyGroup:
    version: int
    rows: dict[str, TierPolicy]

    def price(self, tier: str) -> float:
        row = self.rows.get(tier)
        return float(row.unit_price) if row else 0.0

    @property
    def hot(self) -> TierPolicy:
        return self.rows[StorageTier.HOT]

    @property
    def warm(self) -> TierPolicy:
        return self.rows[StorageTier.WARM]

    @property
    def cold(self) -> TierPolicy:
        return self.rows[StorageTier.COLD]

    @property
    def hot_score_min(self) -> float:
        return float(self.hot.score_min)

    @property
    def warm_score_min(self) -> float:
        return float(self.warm.score_min)

    @property
    def quiet_days(self) -> int:
        return int(self.cold.quiet_days)

    @property
    def block_recent_days(self) -> int:
        return int(self.cold.block_recent_days)

    @property
    def min_partition(self) -> int:
        return int(self.cold.min_partition)

    @property
    def migrate_price(self) -> float:
        return float(self.cold.migrate_price)

    @property
    def migrate_fixed(self) -> float:
        return float(self.cold.migrate_fixed)


def _tier_rows(db: Session, is_current: bool) -> list[TierPolicy]:
    stmt = (
        select(TierPolicy)
        .where(TierPolicy.is_current.is_(is_current))
        .order_by(TierPolicy.tier)
    )
    return list(db.execute(stmt).scalars().all())


def load_current(db: Session) -> PolicyGroup:
    rows = _tier_rows(db, True)
    if not rows:
        raise AppError(codes.NOT_FOUND, "策略尚未初始化", "no current tier_policies")
    keyed = {row.tier: row for row in rows}
    version = max(int(row.version) for row in rows)
    return PolicyGroup(version=version, rows=keyed)


def serialize_row(row: TierPolicy) -> dict:
    return {
        "code": row.code,
        "tier": row.tier,
        "title": row.title,
        "version": int(row.version),
        "score_min": float(row.score_min),
        "unit_price": float(row.unit_price),
        "target_region": row.target_region,
        "quiet_days": int(row.quiet_days),
        "block_recent_days": int(row.block_recent_days),
        "min_partition": int(row.min_partition),
        "migrate_price": float(row.migrate_price),
        "migrate_fixed": float(row.migrate_fixed),
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "is_current": bool(row.is_current),
    }


def serialize_group(group: PolicyGroup) -> dict:
    order = [StorageTier.HOT, StorageTier.WARM, StorageTier.COLD]
    return {
        "version": group.version,
        "is_current": True,
        "tiers": [serialize_row(group.rows[tier]) for tier in order if tier in group.rows],
        "heat_window_days": settings.heat_window_days,
        "heat_half_life_days": settings.heat_half_life_days,
        "report_bonus_per_ref": settings.report_bonus_per_ref,
        "report_bonus_cap": settings.report_bonus_cap,
    }


def list_history(db: Session, limit: int = 6) -> list[dict]:
    rows = db.execute(
        select(TierPolicy).order_by(TierPolicy.version.desc(), TierPolicy.tier.asc())
    ).scalars().all()
    groups: dict[int, list[dict]] = {}
    for row in rows:
        groups.setdefault(int(row.version), []).append(serialize_row(row))
    out = []
    for version in sorted(groups.keys(), reverse=True)[:limit]:
        out.append({"version": version, "tiers": groups[version]})
    return out


def update(db: Session, payload, actor: User, trace_id: str = "") -> dict:
    """生成新版本：新三行 is_current=true，旧行归档。"""
    current = load_current(db)
    base_rows = current.rows
    next_version = current.version + 1
    now = datetime.now(timezone.utc)

    incoming = {item.tier: item for item in payload.tiers}
    for tier in (StorageTier.HOT, StorageTier.WARM, StorageTier.COLD):
        if tier not in incoming:
            raise AppError(codes.VALIDATION_ERROR, f"缺少 {tier} 档策略", f"tier={tier}")

    for row in base_rows.values():
        row.is_current = False

    created = []
    for tier in (StorageTier.HOT, StorageTier.WARM, StorageTier.COLD):
        src = base_rows[tier]
        spec = incoming[tier]
        row = TierPolicy(
            code=POLICY_CODES[tier],
            tier=tier,
            title=POLICY_TITLES[tier],
            version=next_version,
            is_current=True,
            score_min=spec.score_min,
            unit_price=spec.unit_price,
            target_region=spec.target_region,
            quiet_days=payload.quiet_days,
            block_recent_days=payload.block_recent_days,
            min_partition=payload.min_partition,
            migrate_price=payload.migrate_price,
            migrate_fixed=payload.migrate_fixed,
            activated_at=now,
            updated_by=actor.email,
        )
        db.add(row)
        created.append(row)
        # 保底：旧版本字段原样保留在归档行（src 只读引用，避免未使用告警）
        _ = src

    db.flush()
    audit_service.record(
        db,
        action=ACTION_POLICY_UPDATE,
        actor=actor,
        entity_type="TierPolicy",
        entity_id=f"v{next_version}",
        detail={
            "version": next_version,
            "previous_version": current.version,
            "hot_price": money(incoming[StorageTier.HOT].unit_price),
            "warm_price": money(incoming[StorageTier.WARM].unit_price),
            "cold_price": money(incoming[StorageTier.COLD].unit_price),
            "migrate_price": money(payload.migrate_price),
        },
        trace_id=trace_id,
    )
    return serialize_group(load_current(db))
