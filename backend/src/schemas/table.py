"""表档案 / 热度算法输出的入出参。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AccessPointOut(BaseModel):
    stat_date: str
    access_count: int
    query_count: int
    scan_bytes: int
    decay_weight: float = 0.0
    weighted_access: float = 0.0


class HotScoreOut(BaseModel):
    table_id: str
    full_name: str
    hot_score: float
    decay_score: float
    report_bonus: float
    weighted_access: float
    recent_7_access: int
    recent_30_access: int
    total_90_access: int
    suggested_tier: str
    suggested_reason: str
    computed_at: str
    window_days: int
    half_life_days: float


class TableListItem(BaseModel):
    id: str
    full_name: str
    layer: str
    tier: str
    size_gb: float
    partition_count: int
    compression: str
    report_refs: int
    report_names: list[str]
    owner: str
    storage_region: str
    last_write_at: str | None
    hot_score: float
    suggested_tier: str
    monthly_cost: float
    cold_save_month: float
    risk: str
    risk_reason: str


class TableDetailOut(BaseModel):
    profile: TableListItem
    heat: HotScoreOut
    series: list[AccessPointOut]
    economics: dict
    risk: dict
    neighbours: list[dict]


class RecomputeResponse(BaseModel):
    task_id: str
    queued_at: str
    tables: int


class HeatStatusOut(BaseModel):
    last_computed_at: str | None
    table_count: int
    scored_count: int
    worker_heartbeat: str | None
    worker_online: bool
