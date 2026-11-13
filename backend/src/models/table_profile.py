"""TableProfile：数仓表档案（大小 / 分区 / 压缩 / 引用报表 / 当前所在温区）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class TableProfile(Base, TimestampMixin):
    __tablename__ = "table_profiles"
    __table_args__ = (
        Index("ix_table_profiles_tier", "tier"),
        Index("ix_table_profiles_layer", "layer"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    full_name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    layer: Mapped[str] = mapped_column(String(12), nullable=False, default="dwd")
    tier: Mapped[str] = mapped_column(String(12), nullable=False, default="hot")
    size_gb: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    partition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    compression: Mapped[str] = mapped_column(String(12), nullable=False, default="zstd")
    report_refs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_names: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    owner: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    storage_region: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    last_write_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 最近一次 Celery 重算写入的热度快照（GET 接口仍按 AccessStat 现算，二者可对照）
    hot_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    suggested_tier: Mapped[str | None] = mapped_column(String(12), nullable=True)
    heat_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
