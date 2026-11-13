"""工单 CSV 导出（业务链路最后一环）。

结算口径与对账接口 / 页面完全一致（settlement_core）：
  失败表不计节省（实际月省 / 结算净年省 = 0）；已结算按实际账单；
  待对账只计已发生实际迁移成本；未进入执行的项结算列留空。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import PLAN_ITEM_STATUS_LABELS, RISK_LABELS, TIER_LABELS, PlanItemStatus
from src.models.migration_plan import MigrationPlan
from src.models.user import User
from src.services import execution_service, plan_service, settlement_core
from src.utils.errors import AppError

HEADERS = [
    "工单号",
    "计划编号",
    "计划标题",
    "库表",
    "当前温区",
    "目标温区",
    "大小GB",
    "月省元",
    "迁移成本元",
    "回收期月",
    "净年省元",
    "风险",
    "风险说明",
    "执行状态",
    "实际月省元",
    "实际迁移成本元",
    "结算净年省元",
    "回执号",
    "账单号",
    "负责人",
    "生成时间",
]

# 已进入执行口径的状态（这些项的结算列按 settlement_core 输出，其余留空）
_EXECUTION_STATUSES = (
    PlanItemStatus.EXECUTING,
    PlanItemStatus.RECONCILING,
    PlanItemStatus.SETTLED,
    PlanItemStatus.FAILED,
)


def _settlement_cells(item, recon_by_item: dict[str, dict]) -> list[str]:
    """单项的结算列（与对账口径一致）：执行状态 / 实际月省 / 实际迁移成本 / 结算净年省 / 回执号 / 账单号。"""
    status_label = PLAN_ITEM_STATUS_LABELS.get(item.status, item.status)
    if item.status not in _EXECUTION_STATUSES:
        return [status_label, "", "", "", "", ""]
    figures = settlement_core.settled_figures(
        item.status, item.actual_save_month, item.actual_migrate_cost
    )
    recon = recon_by_item.get(str(item.id), {})
    if item.status == PlanItemStatus.SETTLED:
        actual_save = f"{figures['save_month']:.2f}"
        settled_net = f"{figures['net_save_year']:.2f}"
    elif item.status == PlanItemStatus.FAILED:
        actual_save = "0.00"
        settled_net = "0.00"
    else:
        actual_save = ""
        settled_net = ""
    actual_migrate = (
        f"{figures['migrate_cost']:.2f}"
        if item.status in (PlanItemStatus.RECONCILING, PlanItemStatus.SETTLED)
        else ("0.00" if item.status == PlanItemStatus.FAILED else "")
    )
    return [
        status_label,
        actual_save,
        actual_migrate,
        settled_net,
        str(recon.get("receipt_no") or item.last_receipt_no or ""),
        str(recon.get("bill_no") or ""),
    ]


def build_ticket_csv(db: Session, plan: MigrationPlan, actor: User | None = None, trace_id: str = "") -> tuple[str, int]:
    rows = plan_service.plan_item_rows(db, plan)
    if not rows:
        raise AppError(codes.EXPORT_EMPTY, "没有可导出的计划项", f"plan={plan.code}")

    recon_rows = execution_service.reconciliation(db, plan.id)["rows"]
    recon_by_item = {row["item_id"]: row for row in recon_rows}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADERS)
    for index, item in enumerate(rows, start=1):
        writer.writerow(
            [
                f"WO-{plan.code.replace('MP-', '')}-{index:02d}",
                plan.code,
                plan.title,
                item.table_name,
                TIER_LABELS.get(item.from_tier, item.from_tier),
                TIER_LABELS.get(item.suggested_tier, item.suggested_tier),
                f"{float(item.size_gb):.2f}",
                f"{float(item.save_month):.2f}",
                f"{float(item.migration_cost):.2f}",
                f"{float(item.payback_months):.2f}" if item.payback_months is not None else "",
                f"{float(item.net_save_year):.2f}",
                RISK_LABELS.get(item.risk, item.risk),
                item.reasons,
                *_settlement_cells(item, recon_by_item),
                "",
                stamp,
            ]
        )
    if actor is not None:
        plan_service.record_export(db, plan, actor, len(rows), trace_id)
    return buffer.getvalue(), len(rows)
