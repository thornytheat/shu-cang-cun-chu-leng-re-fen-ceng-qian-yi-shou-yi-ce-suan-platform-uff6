"""AccessStat：按天的访问统计（热度算法的唯一输入）。"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, new_uuid


class AccessStat(Base):
    __tablename__ = "access_stats"
    __table_args__ = (
        UniqueConstraint("table_id", "stat_date", name="uq_access_stats_table_date"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.table_profiles.id", ondelete="CASCADE"), index=True
    )
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scan_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
