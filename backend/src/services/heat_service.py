"""算法 1：热度评分（90 天指数衰减加权 + 报表引用加成）。

口径（全部由 settings 提供，前端只展示后端回传值）：
  权重      w(d) = 0.5 ^ (d / half_life)，d = 距今天的天数（0 = 今天），half_life = 14
  加权访问  W = Σ_d access_count(d) × w(d)          # d ∈ [0, window_days)
  衰减分    S_decay = 100 × W / max(W)              # 归一化 0-100（max 取当前全部表）
  引用加成  B = min(report_bonus_cap, report_bonus_per_ref × report_refs)   # +8/引用，上限 20
  热度分    S = min(100, S_decay + B)

分层建议（阈值来自 TierPolicy.hot.score_min / warm.score_min 与冷区 quiet_days）：
  S ≥ 60                            -> hot
  20 ≤ S < 60                       -> warm
  S < 20 且最近 quiet_days 天访问=0  -> cold
  S < 20 但最近 quiet_days 天有访问  -> warm（冷存前置条件不满足，保守留温区）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models.access_stat import AccessStat
from src.models.table_profile import TableProfile
from src.services import heat_core
from src.utils.numeric import score1

WINDOW_DAYS = settings.heat_window_days
HALF_LIFE_DAYS = settings.heat_half_life_days
DAY = timedelta(days=1)


@dataclass
class DayPoint:
    stat_date: date
    offset: int
    access_count: int
    query_count: int
    scan_bytes: int
    decay_weight: float
    weighted_access: float


@dataclass
class HotScore:
    table_id: str
    full_name: str
    weighted_access: float
    decay_score: float
    report_bonus: float
    hot_score: float
    recent_7_access: int
    recent_30_access: int
    total_window_access: int
    suggested_tier: str
    suggested_reason: str
    series: list[DayPoint] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "table_id": self.table_id,
            "full_name": self.full_name,
            "hot_score": self.hot_score,
            "decay_score": self.decay_score,
            "report_bonus": self.report_bonus,
            "weighted_access": round(self.weighted_access, 4),
            "recent_7_access": self.recent_7_access,
            "recent_30_access": self.recent_30_access,
            "total_90_access": self.total_window_access,
            "suggested_tier": self.suggested_tier,
            "suggested_reason": self.suggested_reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "window_days": WINDOW_DAYS,
            "half_life_days": HALF_LIFE_DAYS,
        }


def decay_weight(offset: int, half_life: float = HALF_LIFE_DAYS) -> float:
    """指数衰减权重：0.5 ** (d / 14)（实现见纯函数层 heat_core）。"""
    return heat_core.decay_weight(offset, half_life)


def _window_dates(as_of: date) -> list[date]:
    return heat_core.window_dates(as_of, WINDOW_DAYS)


def load_series(db: Session, table_id: str, as_of: date | None = None) -> list[DayPoint]:
    as_of = as_of or date.today()
    start = as_of - timedelta(days=WINDOW_DAYS - 1)
    rows = db.execute(
        select(AccessStat)
        .where(AccessStat.table_id == table_id, AccessStat.stat_date >= start, AccessStat.stat_date <= as_of)
        .order_by(AccessStat.stat_date.desc())
    ).scalars().all()
    by_date = {row.stat_date: row for row in rows}
    points: list[DayPoint] = []
    for offset, day in enumerate(_window_dates(as_of)):
        row = by_date.get(day)
        weight = decay_weight(offset)
        access = int(row.access_count) if row else 0
        points.append(
            DayPoint(
                stat_date=day,
                offset=offset,
                access_count=access,
                query_count=int(row.query_count) if row else 0,
                scan_bytes=int(row.scan_bytes) if row else 0,
                decay_weight=round(weight, 6),
                weighted_access=round(access * weight, 4),
            )
        )
    return points


def _suggest(score: float, recent_30: int, recent_7: int, group) -> tuple[str, str]:
    """分层建议（阈值全部来自 TierPolicy；实现见纯函数层 heat_core）。"""
    _ = recent_7  # 保留签名兼容：分层只看 quiet_days 窗口与两档阈值
    return heat_core.suggest_tier(
        score,
        recent_30,
        hot_score_min=group.hot_score_min,
        warm_score_min=group.warm_score_min,
        quiet_days=group.quiet_days,
    )


def compute_scores(db: Session, group, as_of: date | None = None) -> dict[str, HotScore]:
    """一次算完 42 张表：单次查访问明细，再按表聚合。"""
    as_of = as_of or date.today()
    start = as_of - timedelta(days=WINDOW_DAYS - 1)
    profiles = db.execute(select(TableProfile).order_by(TableProfile.full_name.asc())).scalars().all()
    rows = db.execute(
        select(AccessStat).where(AccessStat.stat_date >= start, AccessStat.stat_date <= as_of)
    ).scalars().all()

    by_table: dict[str, dict[date, AccessStat]] = {}
    for row in rows:
        by_table.setdefault(str(row.table_id), {})[row.stat_date] = row

    raw: dict[str, dict] = {}
    window = _window_dates(as_of)
    for profile in profiles:
        key = str(profile.id)
        day_map = by_table.get(key, {})
        counts = [int(day_map[day].access_count) if day in day_map else 0 for day in window]
        agg = heat_core.aggregate_access(
            counts,
            half_life=HALF_LIFE_DAYS,
            block_recent_days=group.block_recent_days,
            quiet_days=group.quiet_days,
        )
        raw[key] = {
            "weighted": agg["weighted"],
            "recent_7": agg["recent_block"],
            "recent_30": agg["recent_quiet"],
            "total": agg["total"],
        }

    max_weighted = max((item["weighted"] for item in raw.values()), default=0.0) or 1.0

    scores: dict[str, HotScore] = {}
    for profile in profiles:
        key = str(profile.id)
        item = raw[key]
        decay_score = 100.0 * item["weighted"] / max_weighted
        bonus = heat_core.report_bonus(
            profile.report_refs,
            per_ref=settings.report_bonus_per_ref,
            cap=settings.report_bonus_cap,
        )
        hot_score = heat_core.combine_hot_score(decay_score, bonus)
        tier, reason = _suggest(hot_score, item["recent_30"], item["recent_7"], group)
        scores[key] = HotScore(
            table_id=key,
            full_name=profile.full_name,
            weighted_access=item["weighted"],
            decay_score=score1(decay_score),
            report_bonus=bonus,
            hot_score=hot_score,
            recent_7_access=item["recent_7"],
            recent_30_access=item["recent_30"],
            total_window_access=item["total"],
            suggested_tier=tier,
            suggested_reason=reason,
        )
    return scores


def series_payload(points: list[DayPoint]) -> list[dict]:
    return [
        {
            "stat_date": point.stat_date.isoformat(),
            "access_count": point.access_count,
            "query_count": point.query_count,
            "scan_bytes": point.scan_bytes,
            "decay_weight": point.decay_weight,
            "weighted_access": point.weighted_access,
        }
        for point in points
    ]


def write_snapshot(db: Session, group, as_of: date | None = None) -> int:
    """把热度快照写回 table_profiles（worker 的 recompute_heat 任务用）。"""
    scores = compute_scores(db, group, as_of)
    now = datetime.now(timezone.utc)
    updated = 0
    profiles = db.execute(select(TableProfile)).scalars().all()
    for profile in profiles:
        hit = scores.get(str(profile.id))
        if hit is None:
            continue
        profile.hot_score = hit.hot_score
        profile.suggested_tier = hit.suggested_tier
        profile.heat_computed_at = now
        updated += 1
    db.flush()
    return updated
