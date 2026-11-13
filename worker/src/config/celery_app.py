"""Worker 侧 Celery 应用：消费 coldtier.recompute_heat，beat 负责心跳与定期重算。

任务名与 backend/src/config/celery_app.py 完全一致（跨容器只传任务名）。
算法与模型只有一份实现：任务内部复用 /app/backend 下的 src.*（PYTHONPATH 已设置）。
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab, schedule

from worker_src.config.settings import (
    HEARTBEAT_INTERVAL_SECONDS,
    HEAT_RECOMPUTE_HOURS,
    REDIS_URL,
)

celery_app = Celery(
    "coldtier-worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "worker_src.tasks.heat_task",
        "worker_src.tasks.heartbeat_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=False,
    broker_transport_options={"socket_connect_timeout": 5, "socket_timeout": 5},
    beat_schedule={
        "worker-heartbeat": {
            "task": "coldtier.heartbeat",
            "schedule": schedule(run_every=HEARTBEAT_INTERVAL_SECONDS),
        },
        "heat-recompute": {
            "task": "coldtier.recompute_heat",
            "schedule": crontab(minute="7", hour=f"*/{HEAT_RECOMPUTE_HOURS}"),
            "args": ("",),
        },
    },
)
