"""迁移计划：列表 / 建计划 / 加表 / 移除 / 复检 / 提交 / 导出 CSV / 汇总。"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.middlewares.auth import trace_of
from src.models.user import User
from src.schemas.plan import PlanCreateIn, PlanItemsIn
from src.services import export_service, plan_service, policy_service


def list_plans(db: Session) -> dict:
    return plan_service.list_plans(db)


def create_plan(payload: PlanCreateIn, request: Request, db: Session, user: User) -> dict:
    group = policy_service.load_current(db)
    return plan_service.create_plan(db, group, payload, user, trace_of(request))


def get_plan(db: Session, plan_id: str) -> dict:
    return plan_service.get_plan(db, plan_id)


def add_items(plan_id: str, payload: PlanItemsIn, request: Request, db: Session, user: User) -> dict:
    group = policy_service.load_current(db)
    return plan_service.add_items(db, group, plan_id, payload.table_ids, user, trace_of(request))


def remove_item(plan_id: str, item_id: str, request: Request, db: Session, user: User) -> dict:
    return plan_service.remove_item(db, plan_id, item_id, user, trace_of(request))


def recheck(plan_id: str, request: Request, db: Session, user: User) -> dict:
    group = policy_service.load_current(db)
    return plan_service.recheck(db, group, plan_id, user, trace_of(request))


def submit(plan_id: str, request: Request, db: Session, user: User) -> dict:
    return plan_service.submit(db, plan_id, user, trace_of(request))


def summary(plan_id: str, db: Session) -> dict:
    return plan_service.summary_of(db, plan_id)


def export_tickets(plan_id: str, request: Request, db: Session, user: User) -> Response:
    plan = plan_service.load_plan(db, plan_id)
    content, rows = export_service.build_ticket_csv(db, plan, user, trace_of(request))
    filename = f"coldtier-{plan.code}-tickets.csv"
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Ticket-Rows": str(rows),
            "X-Trace-Id": trace_of(request),
        },
    )
