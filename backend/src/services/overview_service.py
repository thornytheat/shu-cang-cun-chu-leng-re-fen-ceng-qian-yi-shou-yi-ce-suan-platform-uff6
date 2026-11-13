"""存储概览：分层体积/成本、温区分布、候选项统计。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.enums import StorageTier
from src.models.table_profile import TableProfile
from src.services import audit_service, cost_service, heat_service, trial_service
from src.utils.numeric import money


def build(db: Session, group, audit_limit: int = 6) -> dict:
    profiles = list(db.execute(select(TableProfile)).scalars().all())
    scores = heat_service.compute_scores(db, group)

    buckets: dict[str, dict] = {
        tier: {"tier": tier, "table_count": 0, "size_gb": 0.0, "monthly_cost": 0.0, "unit_price": group.price(tier)}
        for tier in (StorageTier.HOT, StorageTier.WARM, StorageTier.COLD)
    }
    layer_cells: dict[tuple[str, str], dict] = {}
    total_size = 0.0
    total_cost = 0.0
    for profile in profiles:
        size = float(profile.size_gb)
        price = group.price(profile.tier)
        cost = size * price
        total_size += size
        total_cost += cost
        bucket = buckets.setdefault(
            profile.tier,
            {"tier": profile.tier, "table_count": 0, "size_gb": 0.0, "monthly_cost": 0.0, "unit_price": price},
        )
        bucket["table_count"] += 1
        bucket["size_gb"] = money(bucket["size_gb"] + size)
        bucket["monthly_cost"] = money(bucket["monthly_cost"] + cost)
        key = (profile.layer, profile.tier)
        cell = layer_cells.setdefault(
            key, {"layer": profile.layer, "tier": profile.tier, "table_count": 0, "size_gb": 0.0, "monthly_cost": 0.0}
        )
        cell["table_count"] += 1
        cell["size_gb"] = money(cell["size_gb"] + size)
        cell["monthly_cost"] = money(cell["monthly_cost"] + cost)

    for bucket in buckets.values():
        bucket["share_pct"] = round(bucket["size_gb"] / total_size * 100, 1) if total_size else 0.0

    trial = trial_service.run_trial(db, group, group.warm_score_min)

    hot_profile = (
        max(profiles, key=lambda item: scores[str(item.id)].weighted_access) if profiles else None
    )
    coldest = max(
        (item for item in trial["hits"] if item["risk"] == "ok"),
        key=lambda item: item["save_month"],
        default=None,
    )
    last_heat = max(
        (profile.heat_computed_at for profile in profiles if profile.heat_computed_at),
        default=None,
    )

    return {
        "brand": settings.brand,
        "org_name": settings.org_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table_count": len(profiles),
        "total_size_gb": money(total_size),
        "total_size_tb": round(total_size / 1024, 2),
        "monthly_cost": money(total_cost),
        "year_cost": money(total_cost * 12),
        "tier_buckets": list(buckets.values()),
        "layer_cells": sorted(layer_cells.values(), key=lambda item: (item["layer"], item["tier"])),
        "cold_saving_month": trial["save_month"],
        "cold_saving_year": trial["save_year"],
        "candidate_count": trial["hit_count"],
        "block_count": trial["risk_block_count"],
        "warn_count": trial["risk_warn_count"],
        "hot_table": (
            {
                "full_name": hot_profile.full_name,
                "hot_score": scores[str(hot_profile.id)].hot_score,
                "size_gb": float(hot_profile.size_gb),
                "tier": hot_profile.tier,
                "report_refs": int(hot_profile.report_refs or 0),
            }
            if hot_profile
            else None
        ),
        "coldest_candidate": (
            {
                "full_name": coldest["full_name"],
                "size_gb": coldest["size_gb"],
                "save_month": coldest["save_month"],
                "payback_months": coldest["payback_months"],
                "hot_score": coldest["hot_score"],
                "table_id": coldest["table_id"],
                "economics": cost_service.economics(coldest["size_gb"], coldest["tier"], group).to_dict(),
            }
            if coldest
            else None
        ),
        "policy_version": group.version,
        "last_heat_at": last_heat.isoformat() if last_heat else None,
        "audit_tail": audit_service.recent(db, audit_limit),
    }
