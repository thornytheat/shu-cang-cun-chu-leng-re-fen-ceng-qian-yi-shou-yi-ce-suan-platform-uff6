"""存储概览出参。"""
from __future__ import annotations

from pydantic import BaseModel


class TierBucket(BaseModel):
    tier: str
    table_count: int
    size_gb: float
    monthly_cost: float
    unit_price: float
    share_pct: float


class LayerCell(BaseModel):
    layer: str
    tier: str
    table_count: int
    size_gb: float
    monthly_cost: float


class OverviewOut(BaseModel):
    brand: str
    org_name: str
    generated_at: str
    table_count: int
    total_size_gb: float
    total_size_tb: float
    monthly_cost: float
    year_cost: float
    tier_buckets: list[TierBucket]
    layer_cells: list[LayerCell]
    cold_saving_month: float
    cold_saving_year: float
    candidate_count: int
    block_count: int
    warn_count: int
    hot_table: dict | None
    coldest_candidate: dict | None
    policy_version: int
    last_heat_at: str | None
    audit_tail: list[dict]


class AuditEntryOut(BaseModel):
    id: str
    action: str
    actor_email: str
    actor_role: str
    entity_type: str
    entity_id: str
    detail: dict
    trace_id: str
    created_at: str
