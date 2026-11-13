"""策略读取 / 版本化编辑 / 试算。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.middlewares.auth import trace_of
from src.models.user import User
from src.schemas.policy import PolicyUpdateIn, TrialRequest
from src.services import policy_service, trial_service


def current(db: Session) -> dict:
    return policy_service.serialize_group(policy_service.load_current(db))


def history(db: Session) -> dict:
    items = policy_service.list_history(db)
    return {"items": items, "meta": {"total": len(items), "returned": len(items), "filters": {}}}


def update(payload: PolicyUpdateIn, request: Request, db: Session, user: User) -> dict:
    return policy_service.update(db, payload, user, trace_of(request))


def trial(payload: TrialRequest, request: Request, db: Session, user: User) -> dict:
    group = policy_service.load_current(db)
    return trial_service.run_trial(db, group, payload.threshold, actor=user, trace_id=trace_of(request))
