"""迁移执行：批次启动 → 逐表回执 → 实际账单 → 按表对账。

状态推进（口径纯函数在 settlement_core，本模块只做 ORM 读写与审计）：
  计划   submitted -> executing -> reconciling -> settled（由逐表回执派生，只前进）
  计划项 submitted/executing --成功回执--> reconciling --账单--> settled
                          \--失败回执--> failed（不计节省）--新回执重试--> reconciling/settled

幂等（两道闸，均不重复计费）：
  receipt_no / bill_no 全局唯一：同一回执、同一账单重试直接幂等忽略；
  batch_no 全局唯一：整批重跑返回已存在批次，不重复置位、不重复计费。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import (
    PLAN_ITEM_STATUS_LABELS,
    PLAN_STATUS_LABELS,
    PlanItemStatus,
    PlanStatus,
    ReceiptResult,
)
from src.constants.log_templates import ACTION_PLAN_BATCH, ACTION_PLAN_BILL, ACTION_PLAN_RECEIPT
from src.models.actual_bill import ActualBill
from src.models.migration_batch import MigrationBatch
from src.models.migration_plan import MigrationPlan
from src.models.migration_plan_item import MigrationPlanItem
from src.models.migration_receipt import MigrationReceipt
from src.models.user import User
from src.services import audit_service, plan_service, settlement_core
from src.utils.errors import AppError, not_found
from src.utils.numeric import money


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _executable_plan(db: Session, plan_id: str, *, allow_settled: bool = False) -> MigrationPlan:
    """可执行性闸门：草稿 / 撤销一律拒绝；已结算计划只允许回执与账单的幂等登记（迟到回执不报错）。"""
    plan = plan_service.load_plan(db, plan_id)
    allowed = settlement_core.EXECUTABLE_PLAN_STATUSES
    if allow_settled:
        allowed = allowed + (PlanStatus.SETTLED,)
    if plan.status not in allowed:
        label = PLAN_STATUS_LABELS.get(plan.status, plan.status)
        raise AppError(
            codes.PLAN_NOT_EXECUTABLE,
            f"计划当前为「{label}」，不能登记执行（需已提交且未结算）",
            f"plan={plan.code} status={plan.status}",
        )
    return plan


def _sync_plan_status(db: Session, plan: MigrationPlan) -> None:
    statuses = [item.status for item in plan_service.active_items(db, plan.id)]
    plan.status = settlement_core.derive_plan_status(statuses, plan.status)
    db.flush()


def serialize_batch(batch: MigrationBatch, receipt_count: int = 0) -> dict:
    return {
        "id": str(batch.id),
        "batch_no": batch.batch_no,
        "note": batch.note,
        "created_by": batch.created_by,
        "receipt_count": receipt_count,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


# ------------------------------------------------------------------ 批次 ----
def _next_batch_no(db: Session, plan: MigrationPlan) -> str:
    seq = (
        len(db.execute(select(MigrationBatch.id).where(MigrationBatch.plan_id == plan.id)).scalars().all()) + 1
    )
    while True:
        candidate = f"MB-{plan.code}-{seq:02d}"
        exists = db.execute(
            select(MigrationBatch.id).where(MigrationBatch.batch_no == candidate)
        ).scalar_one_or_none()
        if exists is None:
            return candidate
        seq += 1


def start_batch(db: Session, plan_id: str, payload, actor: User, trace_id: str = "") -> dict:
    """启动执行批次：submitted/failed 的计划项置为 executing（failed 随新批次重试）。

    整批重跑（同一 batch_no）-> created=False，不重复置位、不重复计费；
    已 reconciling / settled 的项任何批次都不触碰（不回退已完成项）。
    """
    plan = _executable_plan(db, plan_id)
    batch_no = (payload.batch_no or "").strip() or _next_batch_no(db, plan)

    existing = db.execute(
        select(MigrationBatch).where(MigrationBatch.batch_no == batch_no)
    ).scalar_one_or_none()
    if existing is not None:
        if str(existing.plan_id) != str(plan.id):
            raise AppError(
                codes.VALIDATION_ERROR,
                f"批次号 {batch_no} 已被其他计划占用",
                f"batch_no={batch_no} plan={plan.code}",
            )
        return {
            "created": False,
            "touched": 0,
            "batch": serialize_batch(existing),
            "reconciliation": reconciliation(db, plan.id),
        }

    batch = MigrationBatch(
        plan_id=plan.id,
        batch_no=batch_no,
        note=payload.note or "",
        created_by=actor.email,
    )
    db.add(batch)
    db.flush()

    touched = 0
    for item in plan_service.active_items(db, plan.id):
        if item.status in (PlanItemStatus.SUBMITTED, PlanItemStatus.FAILED):
            item.status = PlanItemStatus.EXECUTING
            touched += 1
    db.flush()
    _sync_plan_status(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_BATCH,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={"batch_no": batch.batch_no, "touched": touched, "status": plan.status},
        trace_id=trace_id,
    )
    return {
        "created": True,
        "touched": touched,
        "batch": serialize_batch(batch),
        "reconciliation": reconciliation(db, plan.id),
    }


# ------------------------------------------------------------------ 回执 ----
def _resolve_item(
    db: Session, plan: MigrationPlan, item_id: str | None, table_name: str | None
) -> MigrationPlanItem:
    stmt = select(MigrationPlanItem).where(MigrationPlanItem.plan_id == plan.id)
    candidates = list(db.execute(stmt).scalars().all())
    by_id = {str(item.id): item for item in candidates}
    by_name = {item.table_name: item for item in candidates}
    item = by_id.get(str(item_id)) if item_id else None
    if item is None and table_name:
        item = by_name.get(table_name)
    if item is None:
        raise not_found("MigrationPlanItem", item_id or table_name or "?")
    return item


def _receipt_by_no(db: Session, receipt_no: str) -> MigrationReceipt | None:
    return db.execute(
        select(MigrationReceipt).where(MigrationReceipt.receipt_no == receipt_no)
    ).scalar_one_or_none()


def _bill_of_item(db: Session, item_id) -> ActualBill | None:
    return db.execute(
        select(ActualBill).where(ActualBill.item_id == item_id)
    ).scalar_one_or_none()


def post_receipts(db: Session, plan_id: str, payload, actor: User, trace_id: str = "") -> dict:
    """登记逐表回执（可一次多条）。同一 receipt_no 重试 -> applied=False，不重复计费。

    已结算计划也接受登记：所有项只会得到 applied=False 的幂等回执（迟到回执不报错、不回退）。
    """
    plan = _executable_plan(db, plan_id, allow_settled=True)

    batch = None
    batch_no = (payload.batch_no or "").strip()
    if batch_no:
        batch = db.execute(
            select(MigrationBatch).where(MigrationBatch.batch_no == batch_no)
        ).scalar_one_or_none()
        if batch is None or str(batch.plan_id) != str(plan.id):
            raise not_found("MigrationBatch", batch_no)

    results: list[dict] = []
    applied_count = 0
    for spec in payload.receipts:
        item = _resolve_item(db, plan, spec.item_id, spec.table_name)
        receipt_no = spec.receipt_no.strip()

        if _receipt_by_no(db, receipt_no) is not None:
            results.append(_ack(receipt_no, item, False, settlement_core.REASON_DUPLICATE))
            continue

        bill = _bill_of_item(db, item.id)
        new_status, applied, reason = settlement_core.receipt_transition(
            item.status, spec.result, bill is not None
        )
        receipt = MigrationReceipt(
            plan_id=plan.id,
            item_id=item.id,
            batch_id=batch.id if batch else None,
            receipt_no=receipt_no,
            result=spec.result,
            applied=applied,
            actual_size_gb=spec.actual_size_gb,
            actual_migrate_cost=spec.actual_migrate_cost if spec.result == ReceiptResult.SUCCESS else None,
            message=spec.message or "",
            received_at=_now(),
        )
        db.add(receipt)
        if applied:
            applied_count += 1
            item.status = new_status
            item.last_receipt_no = receipt_no
            if spec.result == ReceiptResult.SUCCESS:
                # 成功回执计费一次：实际迁移成本缺省回落到预估口径
                item.actual_migrate_cost = money(
                    spec.actual_migrate_cost
                    if spec.actual_migrate_cost is not None
                    else float(item.migration_cost)
                )
                if bill is not None:
                    item.actual_save_month = money(bill.actual_save_month)
                    item.settled_at = _now()
            results.append(_ack(receipt_no, item, True, reason))
        else:
            results.append(_ack(receipt_no, item, False, reason))
        db.flush()

    _sync_plan_status(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_RECEIPT,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={
            "batch_no": batch_no,
            "applied": applied_count,
            "ignored": len(results) - applied_count,
            "status": plan.status,
        },
        trace_id=trace_id,
    )
    return {"results": results, "reconciliation": reconciliation(db, plan.id)}


def _ack(receipt_no: str, item: MigrationPlanItem, applied: bool, reason: str) -> dict:
    return {
        "receipt_no": receipt_no,
        "table_name": item.table_name,
        "applied": applied,
        "reason": reason,
        "status": item.status,
        "status_label": PLAN_ITEM_STATUS_LABELS.get(item.status, item.status),
    }


# ------------------------------------------------------------------ 账单 ----
def post_bills(db: Session, plan_id: str, payload, actor: User, trace_id: str = "") -> dict:
    """登记实际账单（首月实际月省）。同一 bill_no / 同一表重复登记 -> 幂等忽略。"""
    plan = _executable_plan(db, plan_id, allow_settled=True)
    results: list[dict] = []
    applied_count = 0
    for spec in payload.bills:
        item = _resolve_item(db, plan, spec.item_id, spec.table_name)
        bill_no = spec.bill_no.strip()

        exists = db.execute(
            select(ActualBill.id).where(ActualBill.bill_no == bill_no)
        ).scalar_one_or_none()
        if exists is not None:
            results.append(_bill_ack(bill_no, item, False, settlement_core.REASON_DUPLICATE))
            continue

        has_bill = _bill_of_item(db, item.id) is not None
        new_status, applied, reason = settlement_core.bill_transition(item.status, has_bill)
        if applied:
            applied_count += 1
            db.add(
                ActualBill(
                    plan_id=plan.id,
                    item_id=item.id,
                    bill_no=bill_no,
                    bill_month=spec.bill_month or "",
                    actual_save_month=money(spec.actual_save_month),
                    note=spec.note or "",
                )
            )
            item.status = new_status
            if new_status == PlanItemStatus.SETTLED:
                item.actual_save_month = money(spec.actual_save_month)
                item.settled_at = _now()
        results.append(_bill_ack(bill_no, item, applied, reason))
        db.flush()

    _sync_plan_status(db, plan)
    audit_service.record(
        db,
        action=ACTION_PLAN_BILL,
        actor=actor,
        entity_type="MigrationPlan",
        entity_id=plan.code,
        detail={
            "applied": applied_count,
            "ignored": len(results) - applied_count,
            "status": plan.status,
        },
        trace_id=trace_id,
    )
    return {"results": results, "reconciliation": reconciliation(db, plan.id)}


def _bill_ack(bill_no: str, item: MigrationPlanItem, applied: bool, reason: str) -> dict:
    return {
        "bill_no": bill_no,
        "table_name": item.table_name,
        "applied": applied,
        "reason": reason,
        "status": item.status,
        "status_label": PLAN_ITEM_STATUS_LABELS.get(item.status, item.status),
    }


# ------------------------------------------------------------------ 对账 ----
def reconciliation(db: Session, plan_id) -> dict:
    """按表对账视图：预估 vs 实际 vs 差异 vs 缺失项（页面 / 导出共用此口径）。"""
    plan = plan_service.load_plan(db, plan_id)
    items = plan_service.active_items(db, plan.id)

    receipts = list(
        db.execute(
            select(MigrationReceipt)
            .where(MigrationReceipt.plan_id == plan.id)
            .order_by(MigrationReceipt.created_at.asc())
        ).scalars().all()
    )
    bills = list(
        db.execute(select(ActualBill).where(ActualBill.plan_id == plan.id)).scalars().all()
    )
    batches = list(
        db.execute(
            select(MigrationBatch)
            .where(MigrationBatch.plan_id == plan.id)
            .order_by(MigrationBatch.created_at.asc())
        ).scalars().all()
    )

    last_receipt: dict[str, MigrationReceipt] = {}
    for receipt in receipts:
        if receipt.applied:
            last_receipt[str(receipt.item_id)] = receipt
    bill_by_item = {str(bill.item_id): bill for bill in bills}
    batch_no_by_id = {str(batch.id): batch.batch_no for batch in batches}
    receipt_count = {
        str(batch.id): sum(1 for r in receipts if r.batch_id is not None and str(r.batch_id) == str(batch.id))
        for batch in batches
    }

    rows = []
    for item in items:
        key = str(item.id)
        receipt = last_receipt.get(key)
        bill = bill_by_item.get(key)
        rows.append(
            settlement_core.reconcile_row(
                {
                    "item_id": key,
                    "table_name": item.table_name,
                    "status": item.status,
                    "save_month": float(item.save_month),
                    "migration_cost": float(item.migration_cost),
                    "net_save_year": float(item.net_save_year),
                    "actual_save_month": item.actual_save_month,
                    "actual_migrate_cost": item.actual_migrate_cost,
                    "receipt_no": item.last_receipt_no,
                    "bill_no": bill.bill_no if bill else "",
                    "batch_no": batch_no_by_id.get(str(receipt.batch_id), "") if receipt else "",
                    "result": receipt.result if receipt else "",
                    "message": receipt.message if receipt else "",
                }
            )
        )
    totals = settlement_core.aggregate(rows)
    return {
        "plan_id": str(plan.id),
        "code": plan.code,
        "status": plan.status,
        "status_label": PLAN_STATUS_LABELS.get(plan.status, plan.status),
        "totals": {k: v for k, v in totals.items() if k not in ("no_receipt", "no_bill", "failed_tables")},
        "missing": {
            "no_receipt": totals["no_receipt"],
            "no_bill": totals["no_bill"],
            "failed": totals["failed_tables"],
        },
        "batches": [serialize_batch(b, receipt_count.get(str(b.id), 0)) for b in batches],
        "rows": rows,
        "generated_at": _now().isoformat(),
    }
