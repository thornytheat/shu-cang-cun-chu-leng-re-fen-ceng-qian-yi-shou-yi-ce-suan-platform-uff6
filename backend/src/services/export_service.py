"""工单 CSV 导出（业务链路最后一环）。"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import RISK_LABELS, TIER_LABELS
from src.models.migration_plan import MigrationPlan
from src.models.user import User
from src.services import plan_service
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
    "负责人",
    "生成时间",
]


def build_ticket_csv(db: Session, plan: MigrationPlan, actor: User | None = None, trace_id: str = "") -> tuple[str, int]:
    rows = plan_service.plan_item_rows(db, plan)
    if not rows:
        raise AppError(codes.EXPORT_EMPTY, "没有可导出的计划项", f"plan={plan.code}")

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
                "",
                stamp,
            ]
        )
    if actor is not None:
        plan_service.record_export(db, plan, actor, len(rows), trace_id)
    return buffer.getvalue(), len(rows)
