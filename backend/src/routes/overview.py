from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import overview_controller
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.overview import OverviewOut

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewOut)
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tables:read")),
) -> dict:
    return overview_controller.overview(db)
