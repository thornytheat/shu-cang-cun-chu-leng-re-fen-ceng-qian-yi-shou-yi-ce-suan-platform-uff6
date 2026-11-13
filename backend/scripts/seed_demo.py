"""幂等演示数据入口：`python -m scripts.seed_demo`（SEED_DEMO=true 容器启动自动跑一次）。

自然键：
  User.email / TierPolicy(code, version) / TableProfile.full_name
  / AccessStat(table_id, stat_date) / MigrationPlan.code

首次期望：
  42 表（热 12 / 温 18 / 冷 12，合计 43,008 GB = 42.0 TB）
  3,600 行日访问统计（39 表 × 90 天 + 2 表 × 40 天 + 1 表 × 10 天）
  3 档策略（version=3，含冷区前置条件与迁移成本）
  1 份 14 项草稿计划 + 3 个账号
重复执行只打印 SEED_SKIPPED，末尾 SEED_SUMMARY 行逐字一致，供幂等校验。
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import func, select

from src.config.database import session_scope
from src.config.settings import settings
from src.constants.enums import PlanStatus, StorageTier
from src.models.access_stat import AccessStat
from src.models.migration_plan import MigrationPlan
from src.models.migration_plan_item import MigrationPlanItem
from src.models.table_profile import TableProfile
from src.models.tier_policy import TierPolicy
from src.models.user import User
from src.services import heat_service, plan_service, policy_service
from src.utils.password import hash_password
from scripts import fixtures

CREATED = 0
SKIPPED = 0
LABEL = settings.brand


def _log(kind: str, entity: str, key: str) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def _created(entity: str, key: str) -> None:
    _log("SEED_CREATED", entity, key)


def _skipped(entity: str, key: str) -> None:
    _log("SEED_SKIPPED", entity, key)


# ------------------------------------------------------------------ 账号 ----
def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for spec in fixtures.DEMO_USERS:
        user = db.execute(select(User).where(User.email == spec["email"])).scalar_one_or_none()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(fixtures.DEMO_PASSWORD),
                display_name=spec["display_name"],
                role=spec["role"],
                team=spec["team"],
                is_active=True,
            )
            db.add(user)
            db.flush()
            _created("User", spec["email"])
        else:
            _skipped("User", spec["email"])
        users[spec["role"]] = user
    return users


# ------------------------------------------------------------------ 策略 ----
def seed_policies(db) -> bool:
    current = db.execute(select(TierPolicy).where(TierPolicy.is_current.is_(True))).scalars().all()
    if current:
        _skipped("TierPolicy", f"version={fixtures.POLICY_VERSION}")
        return False
    now = datetime.now(timezone.utc)
    for spec in fixtures.POLICY_TIERS:
        db.add(
            TierPolicy(
                code=spec["code"],
                tier=spec["tier"],
                title=spec["title"],
                version=fixtures.POLICY_VERSION,
                is_current=True,
                score_min=spec["score_min"],
                unit_price=spec["unit_price"],
                target_region=spec["target_region"],
                quiet_days=fixtures.POLICY_COLD_RULES["quiet_days"],
                block_recent_days=fixtures.POLICY_COLD_RULES["block_recent_days"],
                min_partition=fixtures.POLICY_COLD_RULES["min_partition"],
                migrate_price=fixtures.POLICY_COLD_RULES["migrate_price"],
                migrate_fixed=fixtures.POLICY_COLD_RULES["migrate_fixed"],
                activated_at=now,
                updated_by="admin@coldtier.io",
            )
        )
        _created("TierPolicy", spec["code"])
    db.flush()
    return True


# ------------------------------------------------------------------ 表档案 ----
def _jitter(name: str, offset: int) -> float:
    digest = hashlib.sha256(f"{name}:{offset}".encode("utf-8")).digest()
    return 0.82 + 0.36 * (int.from_bytes(digest[:2], "big") / 65535.0)


def _row_count(size_gb: float, layer: str) -> int:
    bytes_per_row = {"ods": 220, "dwd": 260, "dws": 180, "ads": 96}.get(layer, 240)
    return int(size_gb * 1024 ** 3 / bytes_per_row)


def seed_tables(db, today: date) -> dict[str, TableProfile]:
    tables: dict[str, TableProfile] = {}
    for spec in fixtures.TABLES:
        existing = db.execute(
            select(TableProfile).where(TableProfile.full_name == spec.full_name)
        ).scalar_one_or_none()
        if existing is not None:
            _skipped("TableProfile", spec.full_name)
            tables[spec.full_name] = existing
            continue
        table = TableProfile(
            full_name=spec.full_name,
            layer=spec.layer,
            tier=spec.tier,
            size_gb=spec.size_gb,
            row_count=_row_count(spec.size_gb, spec.layer),
            partition_count=spec.partition_count,
            compression=spec.compression,
            report_refs=spec.report_refs,
            report_names=spec.report_names,
            owner=spec.owner,
            storage_region=spec.region,
            last_write_at=datetime.now(timezone.utc) - timedelta(days=spec.last_write_days, hours=3),
            note=spec.note,
        )
        db.add(table)
        db.flush()
        tables[spec.full_name] = table
        _created("TableProfile", spec.full_name)
    return tables


# --------------------------------------------------------------- 访问统计 ----
def seed_access(db, tables: dict[str, TableProfile], today: date) -> int:
    inserted = 0
    for spec in fixtures.TABLES:
        table = tables[spec.full_name]
        existing = db.execute(
            select(func.count(AccessStat.id)).where(AccessStat.table_id == table.id)
        ).scalar() or 0
        if existing >= spec.access_days:
            _skipped("AccessStat", spec.full_name)
            continue
        spikes = dict(spec.spikes)
        avg_scan_mb = 40 + spec.size_gb * 1.5
        rows = []
        for offset in range(spec.access_days):
            if spec.access_base == 0 or offset < spec.quiet_after:
                access = 0
            else:
                access = round(spec.access_base * _jitter(spec.full_name, offset))
            access += spikes.get(offset, 0)
            rows.append(
                AccessStat(
                    table_id=table.id,
                    stat_date=today - timedelta(days=offset),
                    access_count=access,
                    query_count=max(0, round(access / 1.8)),
                    scan_bytes=int(access * avg_scan_mb * 1024 * 1024),
                )
            )
        db.add_all(rows)
        db.flush()
        inserted += len(rows)
        _created("AccessStat", f"{spec.full_name} rows={len(rows)}")
    return inserted


# --------------------------------------------------------------- 草稿计划 ----
def seed_plan(db) -> None:
    existing = db.execute(
        select(MigrationPlan).where(MigrationPlan.code == fixtures.SEED_PLAN_CODE)
    ).scalar_one_or_none()
    if existing is not None:
        _skipped("MigrationPlan", fixtures.SEED_PLAN_CODE)
        return

    group = policy_service.load_current(db)
    # 14 项 = 12 张热区降冷候选 + 2 张人工加塞的温区表
    table_ids = [spec.full_name for spec in fixtures.TABLES if spec.tier == StorageTier.HOT]
    table_ids.extend(fixtures.SEED_PLAN_EXTRA_TABLES)

    name_to_id = {
        row.full_name: str(row.id)
        for row in db.execute(select(TableProfile)).scalars().all()
    }
    payload = SimpleNamespace(
        title=fixtures.SEED_PLAN_TITLE,
        threshold=20.0,
        table_ids=[name_to_id[name] for name in table_ids if name in name_to_id],
        note=fixtures.SEED_PLAN_NOTE,
    )
    result = plan_service.create_plan(
        db,
        group,
        payload,
        actor=None,
        code=fixtures.SEED_PLAN_CODE,
    )
    plan = db.get(MigrationPlan, result["id"])
    if plan is not None:
        plan.note = fixtures.SEED_PLAN_NOTE
        plan.status = PlanStatus.DRAFT
    db.flush()
    _created("MigrationPlan", fixtures.SEED_PLAN_CODE)


# ------------------------------------------------------------------ 汇总 ----
def _summary(db) -> dict:
    tables = db.query(func.count(TableProfile.id)).scalar() or 0
    access_rows = db.query(func.count(AccessStat.id)).scalar() or 0
    policies = (
        db.query(func.count(TierPolicy.id)).filter(TierPolicy.is_current.is_(True)).scalar() or 0
    )
    plan = db.execute(
        select(MigrationPlan).where(MigrationPlan.code == fixtures.SEED_PLAN_CODE)
    ).scalar_one_or_none()
    plan_items = 0
    if plan is not None:
        plan_items = (
            db.query(func.count(MigrationPlanItem.id))
            .filter(
                MigrationPlanItem.plan_id == plan.id,
                MigrationPlanItem.status != "removed",
            )
            .scalar()
            or 0
        )
    users = db.query(func.count(User.id)).scalar() or 0
    return {
        "tables": int(tables),
        "access_rows": int(access_rows),
        "policies": int(policies),
        "plan_items": int(plan_items),
        "users": int(users),
    }


def seed_all() -> dict:
    today = date.today()
    with session_scope() as db:
        seed_users(db)
        seed_policies(db)
        tables = seed_tables(db, today)
        seed_access(db, tables, today)
        group = policy_service.load_current(db)
        updated = heat_service.write_snapshot(db, group, today)
        print(f"SEED_HEAT_SNAPSHOT tables={updated}", flush=True)
        seed_plan(db)
        summary = _summary(db)
        verify = _verify(db, summary)

    line = (
        f"SEED_SUMMARY brand={LABEL} tables={summary['tables']} access_rows={summary['access_rows']} "
        f"policies={summary['policies']} plan_items={summary['plan_items']} users={summary['users']}"
    )
    print(line, flush=True)
    if not verify["ok"]:
        print(f"SEED_VERIFY_FAILED {verify['problems']}", flush=True)
    return {"created": CREATED, "skipped": SKIPPED, "summary": line}


def _verify(db, summary: dict) -> dict:
    """契约自检：数量与体积/成本口径。失败只告警，不阻塞启动。"""
    problems: list[str] = []
    expected = {
        "tables": 42,
        "access_rows": 3600,
        "policies": 3,
        "plan_items": 14,
        "users": 3,
    }
    for key, value in expected.items():
        if summary[key] != value:
            problems.append(f"{key}={summary[key]} expected={value}")

    tier_counts = {
        tier: db.query(func.count(TableProfile.id)).filter(TableProfile.tier == tier).scalar() or 0
        for tier in (StorageTier.HOT, StorageTier.WARM, StorageTier.COLD)
    }
    if tier_counts != fixtures.EXPECTED_TIER_COUNT:
        problems.append(f"tier_counts={tier_counts}")

    total_size = float(
        db.query(func.coalesce(func.sum(TableProfile.size_gb), 0)).scalar() or 0
    )
    if abs(total_size - 43008.0) > 0.01:
        problems.append(f"total_size_gb={total_size}")
    return {"ok": not problems, "problems": problems}


if __name__ == "__main__":
    result = seed_all()
    print(f"SEED_DONE created={result['created']} skipped={result['skipped']}", flush=True)
    sys.exit(0)
