"""登录 / 当前用户序列化。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.log_templates import ACTION_LOGIN, ACTION_LOGIN_FAILED
from src.constants.roles import ROLE_LABELS, role_permissions
from src.models.user import User
from src.services import audit_service
from src.utils.errors import AppError
from src.utils.jwt import create_access_token
from src.utils.password import verify_password


def serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "team": user.team,
        "permissions": role_permissions(user.role),
    }


def authenticate(db: Session, email: str, password: str, trace_id: str = "") -> dict:
    user = db.execute(select(User).where(User.email == email.lower().strip())).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        audit_service.record(
            db,
            action=ACTION_LOGIN_FAILED,
            entity_type="User",
            entity_id=email,
            detail={"reason": "bad_credentials"},
            trace_id=trace_id,
        )
        raise AppError(codes.AUTH_INVALID, "邮箱或密码不正确", "credentials rejected")
    if not user.is_active:
        raise AppError(codes.AUTH_INVALID, "账号已停用", "user inactive")

    token = create_access_token(str(user.id), user.role, user.email)
    audit_service.record(
        db,
        action=ACTION_LOGIN,
        actor=user,
        entity_type="User",
        entity_id=user.id,
        detail={"role": user.role},
        trace_id=trace_id,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_minutes * 60,
        "user": serialize_user(user),
    }
