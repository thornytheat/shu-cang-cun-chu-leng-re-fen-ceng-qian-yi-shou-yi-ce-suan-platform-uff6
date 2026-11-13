"""热度重算任务：真算 90 天指数衰减加权，写回 table_profiles 快照并记审计。"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone

from worker_src.config.celery_app import celery_app
from worker_src.config.settings import LAST_RUN_KEY

from src.config.database import session_scope
from src.constants.log_templates import ACTION_HEAT_RECOMPUTE
from src.services import audit_service, heat_service, policy_service
from src.utils.logger import get_logger
from src.utils.redis_client import get_redis

logger = get_logger("coldtier.worker.heat")


@celery_app.task(name="coldtier.recompute_heat", bind=True, max_retries=2, default_retry_delay=10)
def recompute_heat(self, email: str = "") -> dict:
    from sqlalchemy import func, select

    from src.models.table_profile import TableProfile
    from src.models.user import User

    started = time.perf_counter()
    try:
        with session_scope() as db:
            group = policy_service.load_current(db)
            updated = heat_service.write_snapshot(db, group, date.today())
            total = db.query(func.count(TableProfile.id)).scalar() or 0
            actor = None
            if email:
                actor = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            audit_service.record(
                db,
                action=ACTION_HEAT_RECOMPUTE,
                actor=actor,
                entity_type="TableProfile",
                entity_id="all",
                detail={"source": "celery", "updated": int(updated), "tables": int(total)},
                trace_id="worker",
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        stamp = datetime.now(timezone.utc).isoformat()
        try:
            get_redis().set(LAST_RUN_KEY, stamp, ex=86400 * 7)
        except Exception:  # noqa: BLE001
            pass
        logger.info("recompute_heat updated=%s tables=%s elapsed=%sms", updated, total, elapsed_ms)
        return {"updated": int(updated), "tables": int(total), "elapsed_ms": elapsed_ms, "at": stamp}
    except Exception as exc:  # noqa: BLE001
        logger.error("recompute_heat failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc) from exc
