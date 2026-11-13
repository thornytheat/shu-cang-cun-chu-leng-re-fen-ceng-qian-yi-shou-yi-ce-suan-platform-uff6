"""迁移计划入出参。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanItemOut(BaseModel):
    id: str
    table_id: str
    table_name: str
    from_tier: str
    suggested_tier: str
    size_gb: float
    hot_score: float
    save_month: float
    migration_cost: float
    payback_months: float | None
    net_save_year: float
    risk: str
    reasons: str
    status: str
    status_label: str = ""
    actual_save_month: float | None = None
    actual_migrate_cost: float | None = None
    last_receipt_no: str = ""
    settled_at: str | None = None


class PlanOut(BaseModel):
    id: str
    code: str
    title: str
    status: str
    status_label: str
    policy_version: int
    threshold: float
    total_size_gb: float
    save_month: float
    save_year: float
    migration_cost: float
    net_save_year: float
    avg_payback: float | None
    risk_block_count: int
    risk_warn_count: int
    created_by: str
    submitted_by: str
    submitted_at: str | None
    rechecked_at: str | None
    note: str
    item_count: int
    items: list[PlanItemOut] = Field(default_factory=list)


class PlanCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    threshold: float = Field(default=20, ge=0, le=100)
    table_ids: list[str] = Field(default_factory=list)
    note: str = ""


class PlanItemsIn(BaseModel):
    table_ids: list[str] = Field(min_length=1)


class PlanSummaryOut(BaseModel):
    plan_id: str
    status: str
    item_count: int
    total_size_gb: float
    save_month: float
    save_year: float
    migration_cost: float
    net_save_year: float
    avg_payback: float | None
    risk_block_count: int
    risk_warn_count: int
    rechecked_at: str | None


# ---------------------------------------------------------------- 执行与对账 ----
class BatchStartIn(BaseModel):
    batch_no: str = Field(default="", max_length=48)
    note: str = Field(default="", max_length=500)


class ReceiptIn(BaseModel):
    receipt_no: str = Field(min_length=1, max_length=64)
    item_id: str | None = None
    table_name: str | None = None
    result: str = Field(pattern="^(success|failed)$")
    actual_size_gb: float | None = Field(default=None, ge=0)
    actual_migrate_cost: float | None = Field(default=None, ge=0)
    message: str = Field(default="", max_length=500)


class ReceiptsIn(BaseModel):
    batch_no: str = Field(default="", max_length=48)
    receipts: list[ReceiptIn] = Field(min_length=1, max_length=60)


class BillIn(BaseModel):
    bill_no: str = Field(min_length=1, max_length=64)
    item_id: str | None = None
    table_name: str | None = None
    bill_month: str = Field(default="", max_length=7)
    actual_save_month: float = Field(ge=0)
    note: str = Field(default="", max_length=500)


class BillsIn(BaseModel):
    bills: list[BillIn] = Field(min_length=1, max_length=60)


class BatchOut(BaseModel):
    id: str
    batch_no: str
    note: str
    created_by: str
    receipt_count: int
    created_at: str | None


class ReconRowOut(BaseModel):
    item_id: str
    table_name: str
    status: str
    result: str
    est_save_month: float
    est_migrate_cost: float
    est_net_save_year: float
    actual_save_month: float | None
    actual_migrate_cost: float | None
    save_diff: float | None
    migrate_diff: float | None
    settled_net_save_year: float | None
    missing: list[str]
    receipt_no: str
    bill_no: str
    batch_no: str
    message: str


class ReconTotalsOut(BaseModel):
    item_count: int
    est_save_month: float
    est_migrate_cost: float
    est_net_save_year: float
    actual_save_month: float
    actual_migrate_cost: float
    settled_net_save_year: float
    save_diff: float
    migrate_diff: float
    net_diff: float
    executing: int
    reconciling: int
    settled: int
    failed: int
    missing_receipt: int
    missing_bill: int


class ReconMissingOut(BaseModel):
    no_receipt: list[str]
    no_bill: list[str]
    failed: list[str]


class ReconciliationOut(BaseModel):
    plan_id: str
    code: str
    status: str
    status_label: str
    totals: ReconTotalsOut
    missing: ReconMissingOut
    batches: list[BatchOut]
    rows: list[ReconRowOut]
    generated_at: str


class BatchAckOut(BaseModel):
    created: bool
    touched: int
    batch: BatchOut
    reconciliation: ReconciliationOut


class ReceiptAck(BaseModel):
    receipt_no: str
    table_name: str
    applied: bool
    reason: str
    status: str
    status_label: str


class ReceiptsAckOut(BaseModel):
    results: list[ReceiptAck]
    reconciliation: ReconciliationOut


class BillAck(BaseModel):
    bill_no: str
    table_name: str
    applied: bool
    reason: str
    status: str
    status_label: str


class BillsAckOut(BaseModel):
    results: list[BillAck]
    reconciliation: ReconciliationOut
