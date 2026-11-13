"""worker 侧最小配置（业务配置/算法复用 backend 的 src.config.settings）。"""
from __future__ import annotations

import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
HEARTBEAT_KEY = "coldtier:worker:heartbeat"
LAST_RUN_KEY = "coldtier:heat:last_run"
HEARTBEAT_INTERVAL_SECONDS = 30.0
HEAT_RECOMPUTE_HOURS = 6
