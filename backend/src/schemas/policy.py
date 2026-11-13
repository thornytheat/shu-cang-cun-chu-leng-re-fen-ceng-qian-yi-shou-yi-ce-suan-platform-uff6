"""策略与试算入出参。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PolicyTierOut(BaseModel):
    code: str
    tier: str
    title: str
    version: int
    score_min: float
    unit_price: float
    target_region: str
    quiet_days: int
    block_recent_days: int
    min_partition: int
    migrate_price: float
    migrate_fixed: float
    updated_by: str
    updated_at: str
    is_current: bool


class PolicyGroupOut(BaseModel):
    version: int
    is_current: bool
    tiers: list[PolicyTierOut]
    heat_window_days: int
    heat_half_life_days: float
    report_bonus_per_ref: int
    report_bonus_cap: int


class PolicyTierIn(BaseModel):
    tier: str
    score_min: float = Field(ge=0, le=100)
    unit_price: float = Field(ge=0, le=100)
    target_region: str = Field(min_length=1, max_length=40)


class PolicyUpdateIn(BaseModel):
    tiers: list[PolicyTierIn]
    quiet_days: int = Field(default=30, ge=1, le=365)
    block_recent_days: int = Field(default=7, ge=1, le=90)
    min_partition: int = Field(default=3, ge=1, le=365)
    migrate_price: float = Field(default=0.75, ge=0, le=100)
    migrate_fixed: float = Field(default=270, ge=0, le=100000)
    note: str = ""


class TrialRequest(BaseModel):
    threshold: float = Field(default=20, ge=0, le=100)
    include_warm: bool = True


class TrialHitOut(BaseModel):
    table_id: str
    full_name: str
    layer: str
    tier: str
    size_gb: float
    partition_count: int
    report_refs: int
    hot_score: float
    suggested_tier: str
    save_month: float
    migration_cost: float
    payback_months: float | None
    net_save_year: float
    risk: str
    reasons: str
    recent_7_access: int
    recent_30_access: int


class TrialResultOut(BaseModel):
    policy_version: int
    threshold: float
    hit_count: int
    evaluated_count: int
    size_total_gb: float
    save_month: float
    save_year: float
    migration_cost: float
    net_save_year: float
    avg_payback: float | None
    risk_block_count: int
    risk_warn_count: int
    hits: list[TrialHitOut]
    computed_at: str
