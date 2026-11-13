"""表档案 / 热度详情 / 热度重算（Celery 异步）。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.orm import Session

from src.config.celery_app import TASK_RECOMPUTE_HEAT, celery_app
from src.constants.log_templates import ACTION_HEAT_RECOMPUTE
from src.middlewares.auth import trace_of
from src.models.user import User
from src.services import audit_service, policy_service, table_service
from src.utils.redis_client import get_redis


def list_tables(
    db: Session,
    tier: str | None = None,
    layer: str | None = None,
    q: str | None = None,
    sort: str = "size",
    only_candidates: bool = False,
) -> dict:
    group = policy_service.load_current(db)
    return table_service.list_tables(db, group, tier=tier, layer=layer, q=q, sort=sort, only_candidates=only_candidates)


def detail(db: Session, table_id: str) -> dict:
    group = policy_service.load_current(db)
    return table_service.get_detail(db, group, table_id)


def recompute(db: Session, request: Request, user: User) -> dict:
    result = celery_app.send_task(TASK_RECOMPUTE_HEAT, args=[user.email])
    now = datetime.now(timezone.utc)
    try:
        get_redis().set("coldtier:heat:queued", now.isoformat(), ex=3600)
    except Exception:  # noqa: BLE001 - Redis 不可用不应阻断投递
        pass
    audit_service.record(
        db,
        action=ACTION_HEAT_RECOMPUTE,
        actor=user,
        entity_type="TableProfile",
        entity_id="all",
        detail={"task_id": result.id},
        trace_id=trace_of(request),
    )
    table_count = table_service.list_tables(db, policy_service.load_current(db))["meta"]["total"]
    return {"task_id": str(result.id), "queued_at": now.isoformat(), "tables": table_count}


def heat_status(db: Session) -> dict:
    payload = table_service.list_tables(db, policy_service.load_current(db))
    profiles = [item for item in payload["items"]]
    client = get_redis()
    heartbeat = None
    online = False
    try:
        heartbeat = client.get("coldtier:worker:heartbeat")
        if heartbeat:
            online = (datetime.now(timezone.utc).timestamp() - float(heartbeat)) < 120
    except Exception:  # noqa: BLE001
        online = False
    last = None
    try:
        last = client.get("coldtier:heat:last_run")
    except Exception:  # noqa: BLE001
        last = None
    return {
        "last_computed_at": last,
        "table_count": len(profiles),
        "scored_count": len(profiles),
        "worker_heartbeat": heartbeat,
        "worker_online": online,
    }
