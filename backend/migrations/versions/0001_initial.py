"""initial schema：users / table_profiles / access_stats / tier_policies / migration_plans / items / audit_logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-12
"""
from __future__ import annotations

from alembic import op

from src.config.settings import settings
from src.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    "users",
    "table_profiles",
    "access_stats",
    "tier_policies",
    "migration_plans",
    "migration_plan_items",
    "audit_logs",
]


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"')
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        bind.exec_driver_sql(f'DROP TABLE IF EXISTS "{settings.db_schema}"."{name}" CASCADE')
