"""迁移计划：建计划 → 风险复检 → 移除阻断 → 提交 → 导出。

计划汇总口径与 TrialResultOut 一致：
  save_month = Σ 逐表月省；save_year = save_month × 12
  migration_cost = Σ (size × 迁移单价 + 每表固定工单成本)
  net_save_year = save_year - migration_cost
  avg_payback = migration_cost / save_month（加权，1.8 月即此口径）
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import PLAN_STATUS_LABELS, PlanItemStatus, PlanStatus, StorageTier
from src.constants.limits import MAX_PLAN_ITEMS
from src.constants.log_templates import (
    ACTION_PLAN_CREATE,
    ACTION_PLAN_EXPORT,
    ACTION_PLAN_ITEM_ADD,
    ACTION_PLAN_ITEM_REMOVE,
    ACTION_PLAN_RECHECK,
    ACTION_PLAN_SUBMIT,
)
from src.models.migration_plan import MigrationPlan
from src.models.migration_plan_item import MigrationPlanItem
from src.models.table_profile import TableProfile
from src.models.user import User
from src.services import audit_service, cost_service, heat_service, savings_core
from src.utils.errors import AppError, not_found
from src.utils.ids import parse_uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_code(db: Session, moment: datetime) -> str:
    quarter = (moment.month - 1) // 3 + 1
    prefix = f"MP-{moment.year}Q{quarter}-"
    existing = db.execute(
        select(MigrationPlan.code).where(MigrationPlan.code.like(f"{prefix}%"))
    ).scalars().all()
    seq = 1
    for code in existing:
        try:
            seq = max(seq, int(code.rsplit("-", 1)[1]) + 1)
        except (IndexError, ValueError):
            continue
    return f"{prefix}{seq:03d}"


def active_items(db: Session, plan_id) -> list[MigrationPlanItem]:
    return list(
        db.execute(
            select(MigrationPlanItem)
            .where(
                MigrationPlanItem.plan_id == plan_id,
                MigrationPlanItem.status != PlanItemStatus.REMOVED,
            )
            .order_by(MigrationPlanItem.save_month.desc())
        ).scalars().all()
    )


def recount(db: Session, plan: MigrationPlan) -> dict:
    """把计划项汇总写回计划头（口径见 savings_core.aggregate，与试算共用）。"""
    items = active_items(db, plan.id)
    summary = savings_core.aggregate(items)
    plan.total_size_gb = summary["size_total_gb"]
    plan.save_month = summary["save_month"]
    plan.save_year = summary["save_year"]
    plan.migration_cost = summary["migration_cost"]
    plan.net_save_year = summary["net_save_year"]
    plan.avg_payback = summary["avg_payback"]
    plan.risk_block_count = summary["risk_block_count"]
    plan.risk_warn_count = summary["risk_warn_count"]
    db.flush()
    return {
        "item_count": summary["count"],
        "total_size_gb": plan.total_size_gb,
        "save_month": plan.save_month,
        "save_year": plan.save_year,
        "migration_cost": plan.migration_cost,
        "net_save_year": plan.net_save_year,
        "avg_payback": float(plan.avg_payback) if plan.avg_payback is not None else None,
        "risk_block_count": plan.risk_block_count,
        "risk_warn_count": plan.risk_warn_count,
    }


def serialize_item(item: MigrationPlanItem) -> dict:
    return {
        "id": str(item.id),
        "table_id": str(item.table_id),
        "table_name": item.table_name,
        "from_tier": item.from_tier,
        "suggested_tier": item.suggested_tier,
        "size_gb": float(item.size_gb),
        "hot_score": float(item.hot_score),
        "save_month": float(item.save_month),
        "migration_cost": float(item.migration_cost),
        "payback_months": float(item.payback_months) if item.payback_months is not None else None,
        "net_save_year": float(item.net_save_year),
        "risk": item.risk,
        "reasons": item.reasons,
        "status": item.status,
    }


def serialize_plan(db: Session, plan: MigrationPlan, with_items: bool = True) -> dict:
    items = active_items(db, plan.id)
    payload = {
        "id": str(plan.id),
        "code": plan.code,
        "title": plan.title,
        "status": plan.status,
        "status_label": PLAN_STATUS_LABELS.get(plan.status, plan.status),
        "policy_version": int(plan.policy_version),
        "threshold": float(plan.threshold),
        "total_size_gb": float(plan.total_size_gb),
        "save_month": float(plan.save_month),
        "save_year": float(plan.save_year),
        "migration_cost": float(plan.migration_cost),
        "net_save_year": float(plan.net_save_year),
        "avg_payback": float(plan.avg_payback) if plan.avg_payback is not None else None,
        "risk_block_count": int(plan.risk_block_count),
        "risk_warn_count": int(plan.risk_warn_count),
        "created_by": plan.created_by,
        "submitted_by": plan.submitted_by,
        "submitted_at": plan.submitted_at.isoformat() if plan.submitted_at else None,
        "rechecked_at": plan.rechecked_at.isoformat() if plan.rechecked_at else None,
        "note": plan.note,
        "item_count": len(items),
        "items": [serialize_item(item) for item in items] if with_items else [],
    }
    return payload


def list_plans(db: Session) -> dict:
    rows = db.execute(select(MigrationPlan).order_by(MigrationPlan.created_at.desc())).scalars().all()
    items = [serialize_plan(db, plan, with_items=False) for plan in rows]
    return {"items": items, "meta": {"total": len(items), "returned": len(items), "filters": {}}}


def get_plan(db: Session, plan_id: str) -> dict:
    return serialize_plan(db, load_plan(db, plan_id))


def _plan_or_404(db: Session, plan_id) -> MigrationPlan:
    """非法 UUID 与不存在 UUID 统一 404（避免驱动层 500）。"""
    key = parse_uuid(plan_id)
    plan = db.get(MigrationPlan, key) if key is not None else None
    if plan is None:
        raise not_found("MigrationPlan", plan_id)
    return plan


def build_item(db: Session, plan: MigrationPlan, profile: TableProfile, hot, group) -> MigrationPlanItem:
    econ = cost_service.economics(float(profile.size_gb), profile.tier, group)
    verdict = cost_service.assess_risk(profile, hot, group)
    return MigrationPlanItem(
        plan_id=plan.id,
        table_id=profile.id,
        table_name=profile.full_name,
        from_tier=profile.tier,
        suggested_tier=hot.suggested_tier,
        size_gb=float(profile.size_gb),
        hot_score=hot.hot_score,
        save_month=econ.save_month,
        migration_cost=econ.migration_cost,
        payback_months=econ.payback_months,
        net_save_year=econ.net_save_year,
        risk=verdict.risk,
        reasons=verdict.reasons,
        status=PlanItemStatus.PENDING,
    )


def create_plan(
    db: Session,
    group,
    payload,
    actor: User | None = None,
    trace_id: str = "",
    code: str | None = None,
) -> dict:
    table_ids = [str(tid) for tid in payload.table_ids]
    try:
        savings_core.check_plan_size(table_ids)
    except ValueError:
        raise AppError(
            codes.VALIDATION_ERROR, f"单次最多 {MAX_PLAN_ITEMS} 张表", f"count={len(table_ids)}"
        ) from None
    now = _now()
    plan = MigrationPlan(
        code=code or _next_code(db, now),
        title=payload.title,
        status=PlanStatus.DRAFT,
        policy_version=group.version,
        threshold=payload.threshold,
        created_by=actor.email if actor else "system",
        note=payload.note,
    )
    db.add(plan)
    db.flush()

    scores = heat_service.compute_scores(db, group)
    added = 0
    for table_id in table_ids:
        profile_key = parse_uuid(table_id)
        profile = db.get(TableProfile, profile_key) if profile_key is not None else None
        if profile is None:
            raise not_found("TableProfile", table_id)
        hot = scores.get(str(profile.id))
        if hot is None:
            continue
        if profile.tier == StorageTier.COLD:
            continue
        db.add(build_item(db, plan, profile, hot, group))
        added += 1
    db.flush()
    summary = recount(db, plan)
    if actor is not None:
        audit_service.record(
            db,
            action=ACTION_PLAN_CREATE,
            actor=actor,
            entity_type="MigrationPlan",
            entity_id=plan.code,
            detail={"items": added, "threshold": float(payload.threshold), **summary},
            trace_id=trace_id,
        )
    return serialize_plan(db, plan)


def add_items(db: Session, group, plan_id: str, table_ids: list[str], actor: User, trace_id: str = "") -> dict:
    plan = _plan_or_404(db, plan_id)
    if plan.status != PlanStatus.DRAFT:
        raise AppError(codes.PLAN_NOT_DRAFT, "只有草稿状态的计划可以添加表", f"status={plan.status}")

    existing = {str(item.table_id) for item in active_items(db, plan.id)}
    scores = heat_service.compute_scores(db, group)
    added = 0
    for table_id in table_ids:
        table_key = str(table_id)
        if table_key in existing:
            continue
        profile_key = parse_uuid(table_id)
        profile = db.get(TableProfile, profile_key) if profile_key is not None else None
        if profile is None:
            raise not_found("TableProfile", table_id)
        hot = scores.get(table_key)
        if hot is None or profile.tier == StorageTier.COLD:
            continue
        db.add(build_item(db, plan, profile, hot, group))
        existing.add(table_key)
        added += 1
    db.flush()
    summary = recount(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_ITEM_ADD,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={"added": added, **summary},
        trace_id=trace_id,
    )
    return serialize_plan(db, plan)


def remove_item(db: Session, plan_id: str, item_id: str, actor: User, trace_id: str = "") -> dict:
    plan = _plan_or_404(db, plan_id)
    if plan.status != PlanStatus.DRAFT:
        raise AppError(codes.PLAN_NOT_DRAFT, "只有草稿状态的计划可以移除表", f"status={plan.status}")
    item_key = parse_uuid(item_id)
    item = db.get(MigrationPlanItem, item_key) if item_key is not None else None
    if item is None or str(item.plan_id) != str(plan.id):
        raise not_found("MigrationPlanItem", item_id)
    item.status = PlanItemStatus.REMOVED
    db.flush()
    summary = recount(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_ITEM_REMOVE,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={"removed": item.table_name, "risk": item.risk, **summary},
        trace_id=trace_id,
    )
    return serialize_plan(db, plan)


def recheck(db: Session, group, plan_id: str, actor: User, trace_id: str = "") -> dict:
    """风险复检：按最新访问数据重算每张表的风险与收益，同步刷新汇总。"""
    plan = _plan_or_404(db, plan_id)
    scores = heat_service.compute_scores(db, group)
    for item in active_items(db, plan.id):
        profile = db.get(TableProfile, item.table_id)
        hot = scores.get(str(item.table_id))
        if profile is None or hot is None:
            continue
        econ = cost_service.economics(float(profile.size_gb), profile.tier, group)
        verdict = cost_service.assess_risk(profile, hot, group)
        item.size_gb = float(profile.size_gb)
        item.hot_score = hot.hot_score
        item.suggested_tier = hot.suggested_tier
        item.save_month = econ.save_month
        item.migration_cost = econ.migration_cost
        item.payback_months = econ.payback_months
        item.net_save_year = econ.net_save_year
        item.risk = verdict.risk
        item.reasons = verdict.reasons
    plan.rechecked_at = _now()
    db.flush()
    summary = recount(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_RECHECK,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={**summary},
        trace_id=trace_id,
    )
    return serialize_plan(db, plan)


def submit(db: Session, plan_id: str, actor: User, trace_id: str = "") -> dict:
    plan = _plan_or_404(db, plan_id)
    if plan.status != PlanStatus.DRAFT:
        raise AppError(codes.PLAN_NOT_DRAFT, "该计划已提交，不能重复提交", f"status={plan.status}")
    items = active_items(db, plan.id)
    if not items:
        raise AppError(codes.PLAN_EMPTY, "计划中没有可提交的表", f"plan={plan.code}")
    blockers = savings_core.blockers(items)
    if blockers:
        raise AppError(
            codes.PLAN_HAS_BLOCKERS,
            f"仍有 {len(blockers)} 张表被风险闸门阻断，请先移除",
            ",".join(blockers),
            extra={"blockers": blockers},
        )
    now = _now()
    for item in items:
        item.status = PlanItemStatus.SUBMITTED
    plan.status = PlanStatus.SUBMITTED
    plan.submitted_at = now
    plan.submitted_by = actor.email
    db.flush()
    summary = recount(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_SUBMIT,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={**summary},
        trace_id=trace_id,
    )
    return serialize_plan(db, plan)


def record_export(db: Session, plan: MigrationPlan, actor: User, row_count: int, trace_id: str = "") -> None:
    audit_service.record(
        db,
        action=ACTION_PLAN_EXPORT,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={"rows": row_count},
        trace_id=trace_id,
    )


def load_plan(db: Session, plan_id: str) -> MigrationPlan:
    return _plan_or_404(db, plan_id)


def summary_of(db: Session, plan_id: str) -> dict:
    plan = load_plan(db, plan_id)
    counts = recount(db, plan)
    return {
        "plan_id": str(plan.id),
        "status": plan.status,
        "rechecked_at": plan.rechecked_at.isoformat() if plan.rechecked_at else None,
        **counts,
    }


def plan_item_rows(db: Session, plan: MigrationPlan) -> list[MigrationPlanItem]:
    return active_items(db, plan.id)


def stats(db: Session) -> dict:
    total = db.query(func.count(MigrationPlan.id)).scalar() or 0
    return {"plan_total": int(total)}
