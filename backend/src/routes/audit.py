from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
def list_audit(
    limit: int = Query(default=50, ge=1, le=200),
    action_prefix: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:read")),
) -> dict:
    return audit_controller.list_audit(db, limit, action_prefix)
