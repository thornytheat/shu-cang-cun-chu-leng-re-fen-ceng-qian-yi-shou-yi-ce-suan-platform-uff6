"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 品牌与业务
    brand: str = "coldtier"
    org_name: str = "青禾零售 · 数据平台组"

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "coldtier"
    db_user: str = "coldtier"
    db_password: str = "coldtier_pw_2026"
    db_schema: str = "coldtier"

    # 安全
    jwt_secret: str = "coldtier-jwt-secret-change-me-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 7

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    seed_demo: bool = True
    rate_limit_trial_per_minute: int = 20
    rate_limit_plan_per_minute: int = 14
    rate_limit_default_per_minute: int = 240

    # 热度算法参数（与 README「算法口径」一致；前端只展示后端回传值）
    heat_window_days: int = 90
    heat_half_life_days: float = 14.0
    report_bonus_per_ref: int = 8
    report_bonus_cap: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
