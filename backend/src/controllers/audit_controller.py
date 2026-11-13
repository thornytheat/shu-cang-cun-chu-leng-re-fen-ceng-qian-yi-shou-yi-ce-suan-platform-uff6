"""审计台账（仅 admin）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import audit_service


def list_audit(db: Session, limit: int = 50, action_prefix: str | None = None) -> dict:
    limit = max(1, min(limit, 200))
    items = audit_service.recent(db, limit=limit, action_prefix=action_prefix)
    return {"items": items, "meta": {"total": len(items), "returned": len(items), "filters": {"limit": limit}}}
