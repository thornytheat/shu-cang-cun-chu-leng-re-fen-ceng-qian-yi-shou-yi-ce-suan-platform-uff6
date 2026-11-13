"""ActualBill：逐表实际账单（财务口径的首月实际月省）。

幂等键 `bill_no`：同一账单重复登记只认第一次，不重复计费；
每张计划表至多一张生效账单（`uq_actual_bills_item`），结算后不再接受新账单。
未生效的登记（失败表 / 已移除表）不落库，只在响应里回执 applied=False。
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class ActualBill(Base, TimestampMixin):
    __tablename__ = "actual_bills"
    __table_args__ = (
        UniqueConstraint("item_id", name="uq_actual_bills_item"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.db_schema}.migration_plans.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.migration_plan_items.id", ondelete="CASCADE"),
        index=True,
    )
    bill_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    bill_month: Mapped[str] = mapped_column(String(7), nullable=False, default="")
    actual_save_month: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
