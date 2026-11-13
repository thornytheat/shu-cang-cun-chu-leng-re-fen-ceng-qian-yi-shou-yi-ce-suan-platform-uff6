"""执行回执与按表对账的纯函数层（结算口径唯一真源）。

与 heat_core / cost_core / savings_core 同层：**不 import Session / 不查库**，
只吃 dict 与数值，可被 pytest 直接单测；`execution_service.py` 负责 ORM 读写后委托这里。

结算口径（对账接口 / 页面 / 工单 CSV 三处共用，改这里即全改）：

  成功回执   -> 实际迁移成本计费一次；同一 receipt_no 幂等，重试 / 整批重跑不重复计费
  失败表     -> 不计节省、不计迁移成本（实际月省 = 0）；重试成功回执才重新计费
  账单先到   -> 允许（回执迟到）：先记账，成功回执到达时立即结算
  已结算     -> 实际月省以实际账单为准；结算净年省 = 实际月省 × 12 − 实际迁移成本
  不回退     -> 已结算 / 待对账的表，后续批次与回执一律忽略（applied=False）

计划状态机（由逐表回执推进，derive_plan_status 派生）：
  submitted -> executing（批次启动）-> reconciling（有成功回执，待账单）-> settled（全部结清）
"""
from __future__ import annotations

from src.constants.enums import PlanItemStatus, PlanStatus, ReceiptResult
from src.utils.numeric import money

# 计划可登记执行的状态（草稿不可执行；已结算 / 已撤销终态）
EXECUTABLE_PLAN_STATUSES = (PlanStatus.SUBMITTED, PlanStatus.EXECUTING, PlanStatus.RECONCILING)

# 回执不生效的原因（响应 reason 字段，前端直接展示）
REASON_RECEIVED = "received"                       # 成功回执已登记，进入待对账
REASON_SETTLED = "settled"                         # 直接结算（账单先到）
REASON_FAILED = "failed"                           # 失败回执已登记，不计节省
REASON_DUPLICATE = "duplicate"                     # 同一回执 / 账单重试，幂等忽略
REASON_ALREADY_RECEIVED = "already_received"       # 已有成功回执，忽略迟到回执
REASON_ALREADY_SETTLED = "already_settled"         # 已结算，不回退
REASON_NOT_EXECUTABLE = "not_executable"           # 计划项不在可执行状态
REASON_ITEM_FAILED = "item_failed"                 # 失败表需先重试成功，再结账
REASON_RECORDED_PENDING = "recorded_pending_receipt"  # 账单先到，等待回执

# 缺失项标记（对账行 missing 字段）
MISSING_RECEIPT = "receipt"
MISSING_BILL = "bill"
MISSING_RETRY = "retry"


def receipt_transition(status: str, result: str, has_bill: bool) -> tuple[str, bool, str]:
    """回执驱动的计划项状态机。返回 (新状态, applied, reason)。

    applied=False 表示幂等忽略：状态不变、不计费（同一回执重试 / 已完成项不回退）。
    """
    if status in (PlanItemStatus.SETTLED,):
        return status, False, REASON_ALREADY_SETTLED
    if status == PlanItemStatus.RECONCILING:
        return status, False, REASON_ALREADY_RECEIVED
    if status in (PlanItemStatus.PENDING, PlanItemStatus.REMOVED):
        return status, False, REASON_NOT_EXECUTABLE
    # submitted / executing / failed：失败表允许凭新回执重试
    if result == ReceiptResult.FAILED:
        return PlanItemStatus.FAILED, True, REASON_FAILED
    if has_bill:
        return PlanItemStatus.SETTLED, True, REASON_SETTLED
    return PlanItemStatus.RECONCILING, True, REASON_RECEIVED


def bill_transition(status: str, has_bill: bool) -> tuple[str, bool, str]:
    """账单驱动的计划项状态机。返回 (新状态, applied, reason)。"""
    if has_bill or status == PlanItemStatus.SETTLED:
        return status, False, REASON_DUPLICATE
    if status == PlanItemStatus.FAILED:
        return status, False, REASON_ITEM_FAILED
    if status in (PlanItemStatus.PENDING, PlanItemStatus.REMOVED):
        return status, False, REASON_NOT_EXECUTABLE
    if status == PlanItemStatus.RECONCILING:
        return PlanItemStatus.SETTLED, True, REASON_SETTLED
    # submitted / executing：账单先到（回执迟到），先记账不回退状态
    return status, True, REASON_RECORDED_PENDING


def derive_plan_status(item_statuses: list[str], current: str) -> str:
    """由逐表状态派生计划状态（只前进，不回退草稿 / 撤销 / 已结算终态）。"""
    if current in (PlanStatus.DRAFT, PlanStatus.CANCELLED, PlanStatus.APPROVED, PlanStatus.SETTLED):
        return current
    active = [s for s in item_statuses if s != PlanItemStatus.REMOVED]
    if not active:
        return current
    if all(s == PlanItemStatus.SETTLED for s in active):
        return PlanStatus.SETTLED
    if any(s in (PlanItemStatus.RECONCILING, PlanItemStatus.SETTLED, PlanItemStatus.FAILED) for s in active):
        return PlanStatus.RECONCILING
    if any(s == PlanItemStatus.EXECUTING for s in active):
        return PlanStatus.EXECUTING
    return current


def settled_figures(
    status: str,
    actual_save_month: float | None,
    actual_migrate_cost: float | None,
) -> dict:
    """单项结算口径：失败 / 未回执 -> 0；待对账 -> 只计已发生迁移成本；已结算 -> 实际账单。"""
    if status == PlanItemStatus.SETTLED:
        save = money(actual_save_month or 0)
        migrate = money(actual_migrate_cost or 0)
    elif status == PlanItemStatus.RECONCILING:
        save = 0.0
        migrate = money(actual_migrate_cost or 0)
    else:
        save = 0.0
        migrate = 0.0
    return {
        "save_month": save,
        "migrate_cost": migrate,
        "net_save_year": money(save * 12 - migrate),
    }


def reconcile_row(item: dict) -> dict:
    """逐表对账行：预估 / 实际 / 差异 / 缺失项。

    item 需要的键：table_name, status, save_month, migration_cost, net_save_year,
    actual_save_month, actual_migrate_cost, receipt_no, bill_no, batch_no, result, message。
    """
    status = item["status"]
    est_save = money(item["save_month"])
    est_migrate = money(item["migration_cost"])
    est_net = money(item["net_save_year"])
    figures = settled_figures(status, item.get("actual_save_month"), item.get("actual_migrate_cost"))

    missing: list[str] = []
    if status in (PlanItemStatus.SUBMITTED, PlanItemStatus.EXECUTING):
        missing.append(MISSING_RECEIPT)
    elif status == PlanItemStatus.RECONCILING:
        missing.append(MISSING_BILL)
    elif status == PlanItemStatus.FAILED:
        missing.append(MISSING_RETRY)

    if status == PlanItemStatus.SETTLED:
        actual_save = figures["save_month"]
        actual_migrate = figures["migrate_cost"]
        settled_net = figures["net_save_year"]
    elif status == PlanItemStatus.FAILED:
        actual_save = 0.0
        actual_migrate = 0.0
        settled_net = 0.0
    elif status == PlanItemStatus.RECONCILING:
        actual_save = None
        actual_migrate = figures["migrate_cost"]
        settled_net = None
    else:
        actual_save = None
        actual_migrate = None
        settled_net = None

    return {
        "item_id": str(item.get("item_id") or item.get("id") or ""),
        "table_name": item["table_name"],
        "status": status,
        "result": item.get("result") or "",
        "est_save_month": est_save,
        "est_migrate_cost": est_migrate,
        "est_net_save_year": est_net,
        "actual_save_month": actual_save,
        "actual_migrate_cost": actual_migrate,
        "save_diff": money(actual_save - est_save) if actual_save is not None else None,
        "migrate_diff": money(actual_migrate - est_migrate) if actual_migrate is not None else None,
        "settled_net_save_year": settled_net,
        "missing": missing,
        "receipt_no": item.get("receipt_no") or "",
        "bill_no": item.get("bill_no") or "",
        "batch_no": item.get("batch_no") or "",
        "message": item.get("message") or "",
    }


def aggregate(rows: list[dict]) -> dict:
    """对账汇总：预估合计 vs 实际合计（已知部分）vs 差异 + 状态计数 + 缺失清单。

    实际合计只含已知口径：已结算的实际值 + 失败表的 0（失败表不计节省）；
    未回执 / 待账单的部分由 missing_* 计数单独暴露，不估算、不摊派。
    """
    est_save = sum(row["est_save_month"] for row in rows)
    est_migrate = sum(row["est_migrate_cost"] for row in rows)
    est_net = sum(row["est_net_save_year"] for row in rows)
    actual_save = sum(row["actual_save_month"] or 0.0 for row in rows)
    actual_migrate = sum(row["actual_migrate_cost"] or 0.0 for row in rows)
    settled_net = sum(row["settled_net_save_year"] or 0.0 for row in rows)

    def names(flag: str) -> list[str]:
        return [row["table_name"] for row in rows if flag in row["missing"]]

    return {
        "item_count": len(rows),
        "est_save_month": money(est_save),
        "est_migrate_cost": money(est_migrate),
        "est_net_save_year": money(est_net),
        "actual_save_month": money(actual_save),
        "actual_migrate_cost": money(actual_migrate),
        "settled_net_save_year": money(settled_net),
        "save_diff": money(actual_save - est_save),
        "migrate_diff": money(actual_migrate - est_migrate),
        "net_diff": money(settled_net - est_net),
        "executing": sum(1 for row in rows if row["status"] == PlanItemStatus.EXECUTING),
        "reconciling": sum(1 for row in rows if row["status"] == PlanItemStatus.RECONCILING),
        "settled": sum(1 for row in rows if row["status"] == PlanItemStatus.SETTLED),
        "failed": sum(1 for row in rows if row["status"] == PlanItemStatus.FAILED),
        "missing_receipt": sum(1 for row in rows if MISSING_RECEIPT in row["missing"]),
        "missing_bill": sum(1 for row in rows if MISSING_BILL in row["missing"]),
        "no_receipt": names(MISSING_RECEIPT),
        "no_bill": names(MISSING_BILL),
        "failed_tables": names(MISSING_RETRY),
    }
