"""限流配额常量（可由环境变量覆盖，见 settings.py）。"""
from __future__ import annotations

from src.config.settings import settings

RATE_LIMIT_TRIAL_PER_MINUTE = settings.rate_limit_trial_per_minute
RATE_LIMIT_PLAN_PER_MINUTE = settings.rate_limit_plan_per_minute
RATE_LIMIT_DEFAULT_PER_MINUTE = settings.rate_limit_default_per_minute

# 试算/复检的输入边界
MIN_TRIAL_THRESHOLD = 0.0
MAX_TRIAL_THRESHOLD = 100.0
MAX_TRIAL_ROWS = 200
MAX_PLAN_ITEMS = 60
