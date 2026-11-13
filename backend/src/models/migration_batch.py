"""MigrationBatch：迁移执行批次（一次工单排期）。

幂等键 `batch_no`：整批重跑时携带同一批次号，服务端直接返回已存在的批次，
不重复置位计划项、不重复计费。
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class MigrationBatch(Base, TimestampMixin):
    __tablename__ = "migration_batches"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.migration_plans.id", ondelete="CASCADE"), index=True
    )
    batch_no: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
