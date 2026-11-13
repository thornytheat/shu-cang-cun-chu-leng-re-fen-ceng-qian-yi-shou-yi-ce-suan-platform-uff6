from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import plan_controller
from src.middlewares.rbac import require_permission
from src.middlewares.rate_limit import rate_limit
from src.models.user import User
from src.schemas.plan import (
    BatchAckOut,
    BatchStartIn,
    BillsAckOut,
    BillsIn,
    PlanCreateIn,
    PlanItemsIn,
    PlanOut,
    PlanSummaryOut,
    ReceiptsAckOut,
    ReceiptsIn,
    ReconciliationOut,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("")
def list_plans(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("plans:read")),
) -> dict:
    return plan_controller.list_plans(db)


@router.post("", response_model=PlanOut, dependencies=[rate_limit("plan")])
def create_plan(
    payload: PlanCreateIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:write")),
) -> dict:
    return plan_controller.create_plan(payload, request, db, user)


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("plans:read")),
) -> dict:
    return plan_controller.get_plan(db, plan_id)


@router.get("/{plan_id}/summary", response_model=PlanSummaryOut)
def summary(
    plan_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("plans:read")),
) -> dict:
    return plan_controller.summary(plan_id, db)


@router.post("/{plan_id}/items", response_model=PlanOut, dependencies=[rate_limit("plan")])
def add_items(
    plan_id: str,
    payload: PlanItemsIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:write")),
) -> dict:
    return plan_controller.add_items(plan_id, payload, request, db, user)


@router.delete("/{plan_id}/items/{item_id}", response_model=PlanOut, dependencies=[rate_limit("plan")])
def remove_item(
    plan_id: str,
    item_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:write")),
) -> dict:
    return plan_controller.remove_item(plan_id, item_id, request, db, user)


@router.post("/{plan_id}/recheck", response_model=PlanOut, dependencies=[rate_limit("plan")])
def recheck(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:write")),
) -> dict:
    return plan_controller.recheck(plan_id, request, db, user)


@router.post("/{plan_id}/submit", response_model=PlanOut, dependencies=[rate_limit("plan")])
def submit(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:submit")),
) -> dict:
    return plan_controller.submit(plan_id, request, db, user)


@router.post("/{plan_id}/batches", response_model=BatchAckOut, dependencies=[rate_limit("plan")])
def start_batch(
    plan_id: str,
    payload: BatchStartIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:execute")),
) -> dict:
    return plan_controller.start_batch(plan_id, payload, request, db, user)


@router.post("/{plan_id}/receipts", response_model=ReceiptsAckOut, dependencies=[rate_limit("plan")])
def post_receipts(
    plan_id: str,
    payload: ReceiptsIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:execute")),
) -> dict:
    return plan_controller.post_receipts(plan_id, payload, request, db, user)


@router.post("/{plan_id}/bills", response_model=BillsAckOut, dependencies=[rate_limit("plan")])
def post_bills(
    plan_id: str,
    payload: BillsIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:execute")),
) -> dict:
    return plan_controller.post_bills(plan_id, payload, request, db, user)


@router.get("/{plan_id}/reconciliation", response_model=ReconciliationOut)
def reconciliation(
    plan_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("plans:read")),
) -> dict:
    return plan_controller.reconciliation(plan_id, db)


@router.get("/{plan_id}/export.csv")
def export_tickets(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("plans:export")),
) -> Response:
    return plan_controller.export_tickets(plan_id, request, db, user)
