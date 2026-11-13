from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import table_controller
from src.middlewares.rbac import require_permission
from src.middlewares.rate_limit import rate_limit
from src.models.user import User
from src.schemas.common import ListResponse
from src.schemas.table import HeatStatusOut, RecomputeResponse, TableDetailOut, TableListItem

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=ListResponse[TableListItem])
def list_tables(
    tier: str | None = Query(default=None),
    layer: str | None = Query(default=None),
    q: str | None = Query(default=None),
    sort: str = Query(default="size", pattern="^(size|score|name|save)$"),
    only_candidates: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tables:read")),
) -> dict:
    return table_controller.list_tables(db, tier, layer, q, sort, only_candidates)


@router.get("/heat/status", response_model=HeatStatusOut)
def heat_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tables:read")),
) -> dict:
    return table_controller.heat_status(db)


@router.post("/heat/recompute", response_model=RecomputeResponse, dependencies=[rate_limit("default")])
def recompute(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("tables:recompute")),
) -> dict:
    return table_controller.recompute(db, request, user)


@router.get("/{table_id}", response_model=TableDetailOut)
def detail(
    table_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tables:read")),
) -> dict:
    return table_controller.detail(db, table_id)
