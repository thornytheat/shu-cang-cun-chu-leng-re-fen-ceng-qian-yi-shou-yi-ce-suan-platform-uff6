"""登录 / 当前用户。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.middlewares.auth import trace_of
from src.models.user import User
from src.schemas.auth import LoginRequest
from src.services import auth_service


def login(payload: LoginRequest, request: Request, db: Session) -> dict:
    return auth_service.authenticate(db, payload.email, payload.password, trace_of(request))


def me(user: User) -> dict:
    return {"user": auth_service.serialize_user(user)}
