"""执行回执与按表对账纯函数单测（结算口径唯一真源 settlement_core）。

覆盖验收口径：
  - 计划按逐表回执推进 执行中 -> 待对账 -> 已结算；
  - 失败表不计节省，重试成功再结算且不回退已完成项；
  - 同一回执重试 / 整批重跑不重复计费（状态机幂等）；
  - 预估 / 实际 / 差异 / 缺失项的逐表与汇总口径。
"""
from __future__ import annotations

from src.constants.enums import PlanItemStatus as S
from src.constants.enums import PlanStatus as P
from src.constants.enums import ReceiptResult as R
from src.services import settlement_core as core


# ------------------------------------------------------------------ 回执状态机 ----
def test_receipt_success_moves_to_reconciling() -> None:
    status, applied, reason = core.receipt_transition(S.EXECUTING, R.SUCCESS, has_bill=False)
    assert (status, applied, reason) == (S.RECONCILING, True, "received")


def test_receipt_success_with_early_bill_settles_immediately() -> None:
    """账单先到（回执迟到）：成功回执到达时直接结算。"""
    status, applied, reason = core.receipt_transition(S.EXECUTING, R.SUCCESS, has_bill=True)
    assert (status, applied, reason) == (S.SETTLED, True, "settled")


def test_receipt_failed_counts_no_saving_but_retryable() -> None:
    status, applied, reason = core.receipt_transition(S.EXECUTING, R.FAILED, has_bill=False)
    assert (status, applied, reason) == (S.FAILED, True, "failed")
    # 重试成功 -> 重新进入待对账（带回执计费）
    status, applied, reason = core.receipt_transition(S.FAILED, R.SUCCESS, has_bill=False)
    assert (status, applied, reason) == (S.RECONCILING, True, "received")


def test_receipt_retry_on_settled_is_idempotent_no_rollback() -> None:
    """已结算不回退：迟到 / 重复回执一律忽略。"""
    for result in (R.SUCCESS, R.FAILED):
        status, applied, reason = core.receipt_transition(S.SETTLED, result, has_bill=True)
        assert (status, applied, reason) == (S.SETTLED, False, "already_settled")


def test_receipt_after_success_is_ignored() -> None:
    """待对账（已有成功回执）不再接受任何回执：不重复计费。"""
    status, applied, reason = core.receipt_transition(S.RECONCILING, R.SUCCESS, has_bill=False)
    assert (status, applied, reason) == (S.RECONCILING, False, "already_received")


def test_receipt_on_draft_or_removed_is_rejected() -> None:
    for status in (S.PENDING, S.REMOVED):
        _, applied, reason = core.receipt_transition(status, R.SUCCESS, has_bill=False)
        assert (applied, reason) == (False, "not_executable")


# ------------------------------------------------------------------ 账单状态机 ----
def test_bill_settles_reconciling_item() -> None:
    status, applied, reason = core.bill_transition(S.RECONCILING, has_bill=False)
    assert (status, applied, reason) == (S.SETTLED, True, "settled")


def test_bill_before_receipt_is_recorded_without_rollback() -> None:
    """账单先到：记账但状态不动，等迟到回执来结算。"""
    status, applied, reason = core.bill_transition(S.EXECUTING, has_bill=False)
    assert (status, applied, reason) == (S.EXECUTING, True, "recorded_pending_receipt")


def test_bill_duplicate_is_idempotent() -> None:
    """同一表重复账单 / 已结算再收账单：幂等忽略，不重复计费。"""
    _, applied, reason = core.bill_transition(S.RECONCILING, has_bill=True)
    assert (applied, reason) == (False, "duplicate")
    _, applied, reason = core.bill_transition(S.SETTLED, has_bill=True)
    assert (applied, reason) == (False, "duplicate")


def test_bill_on_failed_item_is_rejected() -> None:
    """失败表不计节省：必须先重试成功，账单才生效。"""
    _, applied, reason = core.bill_transition(S.FAILED, has_bill=False)
    assert (applied, reason) == (False, "item_failed")


# ------------------------------------------------------------------ 计划状态派生 ----
def test_plan_status_progresses_with_receipts() -> None:
    assert core.derive_plan_status([S.SUBMITTED, S.SUBMITTED], P.SUBMITTED) == P.SUBMITTED
    assert core.derive_plan_status([S.EXECUTING, S.SUBMITTED], P.SUBMITTED) == P.EXECUTING
    assert core.derive_plan_status([S.RECONCILING, S.EXECUTING], P.EXECUTING) == P.RECONCILING
    assert core.derive_plan_status([S.SETTLED, S.SETTLED], P.RECONCILING) == P.SETTLED


def test_plan_status_failed_keeps_reconciling_until_retried() -> None:
    assert core.derive_plan_status([S.SETTLED, S.FAILED], P.RECONCILING) == P.RECONCILING
    assert core.derive_plan_status([S.FAILED, S.FAILED], P.EXECUTING) == P.RECONCILING


def test_plan_status_terminal_states_never_rollback() -> None:
    assert core.derive_plan_status([S.SETTLED], P.SETTLED) == P.SETTLED
    assert core.derive_plan_status([S.PENDING], P.DRAFT) == P.DRAFT
    assert core.derive_plan_status([], P.SUBMITTED) == P.SUBMITTED


# ------------------------------------------------------------------ 结算口径 ----
def test_settled_figures_caliber() -> None:
    # 已结算：全部按实际
    figures = core.settled_figures(S.SETTLED, 800.0, 1150.0)
    assert figures == {"save_month": 800.0, "migrate_cost": 1150.0, "net_save_year": 8450.0}
    # 待对账：只计已发生迁移成本，月省未结
    figures = core.settled_figures(S.RECONCILING, None, 1150.0)
    assert figures == {"save_month": 0.0, "migrate_cost": 1150.0, "net_save_year": -1150.0}
    # 失败表：不计节省也不计费
    figures = core.settled_figures(S.FAILED, None, None)
    assert figures == {"save_month": 0.0, "migrate_cost": 0.0, "net_save_year": 0.0}
    # 执行中：未回执不计费
    figures = core.settled_figures(S.EXECUTING, None, None)
    assert figures == {"save_month": 0.0, "migrate_cost": 0.0, "net_save_year": 0.0}


# ------------------------------------------------------------------ 对账行与汇总 ----
def _item(name: str, status: str, **overrides) -> dict:
    base = {
        "item_id": name,
        "table_name": name,
        "status": status,
        "save_month": 840.0,
        "migration_cost": 1035.0,
        "net_save_year": 9045.0,
        "actual_save_month": None,
        "actual_migrate_cost": None,
        "receipt_no": "",
        "bill_no": "",
        "batch_no": "",
        "result": "",
        "message": "",
    }
    base.update(overrides)
    return base


def test_reconcile_row_estimated_actual_diff_missing() -> None:
    settled = core.reconcile_row(
        _item(
            "dws.a",
            S.SETTLED,
            actual_save_month=800.0,
            actual_migrate_cost=1100.0,
            receipt_no="RC-1",
            bill_no="B-1",
            result="success",
        )
    )
    assert settled["est_save_month"] == 840.0
    assert settled["actual_save_month"] == 800.0
    assert settled["save_diff"] == -40.0
    assert settled["migrate_diff"] == 65.0
    assert settled["settled_net_save_year"] == 800.0 * 12 - 1100.0
    assert settled["missing"] == []

    failed = core.reconcile_row(_item("dws.b", S.FAILED, receipt_no="RC-2", result="failed"))
    assert failed["actual_save_month"] == 0.0          # 失败表不计节省
    assert failed["save_diff"] == -840.0
    assert failed["missing"] == ["retry"]

    waiting = core.reconcile_row(_item("dws.c", S.EXECUTING))
    assert waiting["actual_save_month"] is None        # 未回执：实际未知（缺失项）
    assert waiting["missing"] == ["receipt"]

    recon = core.reconcile_row(_item("dws.d", S.RECONCILING, actual_migrate_cost=1035.0))
    assert recon["actual_save_month"] is None
    assert recon["actual_migrate_cost"] == 1035.0
    assert recon["missing"] == ["bill"]


def test_aggregate_totals_and_missing_lists() -> None:
    rows = [
        core.reconcile_row(
            _item("t.settled", S.SETTLED, actual_save_month=800.0, actual_migrate_cost=1100.0)
        ),
        core.reconcile_row(_item("t.recon", S.RECONCILING, actual_migrate_cost=1035.0)),
        core.reconcile_row(_item("t.failed", S.FAILED, result="failed")),
        core.reconcile_row(_item("t.running", S.EXECUTING)),
    ]
    totals = core.aggregate(rows)
    assert totals["item_count"] == 4
    assert totals["est_save_month"] == 3360.0
    assert totals["actual_save_month"] == 800.0        # 已结算实际值 + 失败 0，未回执不计
    assert totals["actual_migrate_cost"] == 2135.0     # 1100 + 1035，失败 / 未回执不计费
    assert totals["save_diff"] == 800.0 - 3360.0
    assert totals["settled_net_save_year"] == 800.0 * 12 - 1100.0
    assert totals["net_diff"] == totals["settled_net_save_year"] - totals["est_net_save_year"]
    assert (totals["settled"], totals["reconciling"], totals["failed"], totals["executing"]) == (1, 1, 1, 1)
    assert totals["missing_receipt"] == 1
    assert totals["missing_bill"] == 1
    assert totals["no_receipt"] == ["t.running"]
    assert totals["no_bill"] == ["t.recon"]
    assert totals["failed_tables"] == ["t.failed"]


def test_aggregate_is_order_independent() -> None:
    rows = [
        core.reconcile_row(_item("t.a", S.SETTLED, actual_save_month=800.0, actual_migrate_cost=1100.0)),
        core.reconcile_row(_item("t.b", S.FAILED)),
        core.reconcile_row(_item("t.c", S.RECONCILING, actual_migrate_cost=900.0)),
    ]
    forward = core.aggregate(rows)
    backward = core.aggregate(list(reversed(rows)))
    assert {k: v for k, v in forward.items() if not isinstance(v, list)} == {
        k: v for k, v in backward.items() if not isinstance(v, list)
    }


def test_aggregate_empty_degrades_to_zero() -> None:
    totals = core.aggregate([])
    assert totals["item_count"] == 0
    assert totals["est_save_month"] == 0.0
    assert totals["actual_save_month"] == 0.0
    assert totals["save_diff"] == 0.0
    assert totals["no_receipt"] == [] and totals["no_bill"] == [] and totals["failed_tables"] == []


# ------------------------------------------------------------------ 全链路剧本 ----
def test_full_execution_journey_matches_business_story() -> None:
    """提交 -> 批次 -> 失败/迟到回执 -> 重试 -> 账单 -> 全部结算，且不回退、不重复计费。"""
    # 3 张表的计划提交后启动批次：全部进入执行中
    statuses = {name: S.SUBMITTED for name in ("t.a", "t.b", "t.c")}
    statuses = {name: S.EXECUTING for name in statuses}
    assert core.derive_plan_status(list(statuses.values()), P.SUBMITTED) == P.EXECUTING

    bills: set[str] = set()
    # t.a 成功回执 -> 待对账；同一回执重试 -> 幂等忽略（不重复计费）
    statuses["t.a"], applied, _ = core.receipt_transition(statuses["t.a"], R.SUCCESS, "t.a" in bills)
    assert applied and statuses["t.a"] == S.RECONCILING
    _, applied, reason = core.receipt_transition(statuses["t.a"], R.SUCCESS, "t.a" in bills)
    assert (applied, reason) == (False, "already_received")

    # t.b 失败回执 -> 失败（不计节省）；账单直接打给失败表 -> 拒绝
    statuses["t.b"], applied, _ = core.receipt_transition(statuses["t.b"], R.FAILED, False)
    assert applied and statuses["t.b"] == S.FAILED
    _, applied, reason = core.bill_transition(statuses["t.b"], "t.b" in bills)
    assert (applied, reason) == (False, "item_failed")

    # t.c 账单先到（回执迟到）-> 先记账不回退；成功回执到达 -> 立即结算
    statuses["t.c"], applied, reason = core.bill_transition(statuses["t.c"], "t.c" in bills)
    assert (applied, reason) == (True, "recorded_pending_receipt") and statuses["t.c"] == S.EXECUTING
    bills.add("t.c")
    statuses["t.c"], applied, reason = core.receipt_transition(statuses["t.c"], R.SUCCESS, True)
    assert (applied, reason) == (True, "settled") and statuses["t.c"] == S.SETTLED

    # t.a 账单 -> 已结算；t.b 新回执重试成功 -> 待对账 -> 账单 -> 已结算
    statuses["t.a"], applied, _ = core.bill_transition(statuses["t.a"], False)
    assert applied and statuses["t.a"] == S.SETTLED
    bills.update(("t.a",))
    statuses["t.b"], applied, _ = core.receipt_transition(statuses["t.b"], R.SUCCESS, False)
    assert applied and statuses["t.b"] == S.RECONCILING
    statuses["t.b"], applied, _ = core.bill_transition(statuses["t.b"], False)
    assert applied and statuses["t.b"] == S.SETTLED

    # 全部结清 -> 计划已结算；迟到的重复回执不再回退任何已完成项
    assert core.derive_plan_status(list(statuses.values()), P.RECONCILING) == P.SETTLED
    for name in statuses:
        _, applied, reason = core.receipt_transition(statuses[name], R.FAILED, True)
        assert (applied, reason) == (False, "already_settled")
        assert statuses[name] == S.SETTLED
