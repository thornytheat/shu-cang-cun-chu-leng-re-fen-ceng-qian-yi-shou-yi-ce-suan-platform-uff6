"""存储概览。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import overview_service, policy_service


def overview(db: Session) -> dict:
    group = policy_service.load_current(db)
    return overview_service.build(db, group)
