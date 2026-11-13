"""beat：每 30s 写心跳（compose healthcheck 读这个 key）。"""
from __future__ import annotations

import time

from worker_src.config.celery_app import celery_app
from worker_src.config.settings import HEARTBEAT_KEY

from src.utils.logger import get_logger
from src.utils.redis_client import get_redis

logger = get_logger("coldtier.worker.heartbeat")


@celery_app.task(name="coldtier.heartbeat")
def heartbeat() -> dict:
    stamp = time.time()
    try:
        get_redis().set(HEARTBEAT_KEY, str(stamp), ex=300)
    except Exception as exc:  # noqa: BLE001 - 心跳失败不抛出，健康检查会兜底
        logger.warning("heartbeat failed: %s", exc)
        return {"ok": False, "at": stamp}
    return {"ok": True, "at": stamp}
