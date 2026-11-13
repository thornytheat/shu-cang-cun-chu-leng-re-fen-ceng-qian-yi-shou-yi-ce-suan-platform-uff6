"""TierPolicy：热/温/冷三档的判级条件、单价与迁移成本，版本化（is_current 标识当前版本）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class TierPolicy(Base, TimestampMixin):
    __tablename__ = "tier_policies"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_tier_policies_code_version"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # code 固定为 POL-HOT / POL-WARM / POL-COLD，version 递增；code+version 唯一
    tier: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    score_min: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    target_region: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    # 冷区前置条件与风险闸门（挂在冷档策略上，一处维护）
    quiet_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    block_recent_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    min_partition: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    migrate_price: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    migrate_fixed: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
