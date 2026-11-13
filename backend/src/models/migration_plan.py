"""MigrationPlan：迁移计划（一次季度降冷动作的汇总与审批载体）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class MigrationPlan(Base, TimestampMixin):
    __tablename__ = "migration_plans"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    threshold: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=20)
    total_size_gb: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    save_month: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    save_year: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    migration_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_save_year: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    avg_payback: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    risk_block_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_warn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    submitted_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rechecked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
