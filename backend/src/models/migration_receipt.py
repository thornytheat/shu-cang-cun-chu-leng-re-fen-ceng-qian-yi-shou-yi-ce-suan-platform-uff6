"""MigrationReceipt：逐表迁移回执（平台组执行反馈）。

幂等键 `receipt_no`：同一回执重试（网络重发 / 整批重跑）只认第一次，
重复登记返回 applied=False，不重复计费。`applied=False` 的行保留作审计痕迹
（例如已结算表上迟到的重复回执），不参与任何汇总。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class MigrationReceipt(Base, TimestampMixin):
    __tablename__ = "migration_receipts"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.migration_plans.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.migration_plan_items.id", ondelete="CASCADE"),
        index=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.migration_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    receipt_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(10), nullable=False, default="success")
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actual_size_gb: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_migrate_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
