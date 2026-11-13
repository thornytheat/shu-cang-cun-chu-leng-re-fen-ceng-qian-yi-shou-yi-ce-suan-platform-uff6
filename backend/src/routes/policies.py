from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import policy_controller
from src.middlewares.rbac import require_permission
from src.middlewares.rate_limit import rate_limit
from src.models.user import User
from src.schemas.policy import PolicyGroupOut, PolicyUpdateIn, TrialRequest, TrialResultOut

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/current", response_model=PolicyGroupOut)
def current(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("policies:read")),
) -> dict:
    return policy_controller.current(db)


@router.get("/history")
def history(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("policies:read")),
) -> dict:
    return policy_controller.history(db)


@router.put("/current", response_model=PolicyGroupOut)
def update(
    payload: PolicyUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("policies:write")),
) -> dict:
    return policy_controller.update(payload, request, db, user)


@router.post("/trial", response_model=TrialResultOut, dependencies=[rate_limit("trial")])
def trial(
    payload: TrialRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("trial:run")),
) -> dict:
    return policy_controller.trial(payload, request, db, user)
