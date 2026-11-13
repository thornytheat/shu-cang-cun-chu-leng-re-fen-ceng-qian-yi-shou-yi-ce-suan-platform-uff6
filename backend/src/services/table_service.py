"""表档案查询：列表 / 详情 / 邻表，全部带上后端现算的热度与收益。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import StorageTier
from src.models.table_profile import TableProfile
from src.services import cost_service, heat_service
from src.utils.errors import AppError, not_found
from src.utils.ids import parse_uuid
from src.utils.numeric import money


def _row(profile: TableProfile, hot, group) -> dict:
    econ = cost_service.economics(float(profile.size_gb), profile.tier, group)
    verdict = cost_service.assess_risk(profile, hot, group)
    monthly_cost = money(float(profile.size_gb) * group.price(profile.tier))
    cold_save = 0.0 if profile.tier == StorageTier.COLD else econ.save_month
    return {
        "id": str(profile.id),
        "full_name": profile.full_name,
        "layer": profile.layer,
        "tier": profile.tier,
        "size_gb": float(profile.size_gb),
        "partition_count": int(profile.partition_count),
        "compression": profile.compression,
        "report_refs": int(profile.report_refs or 0),
        "report_names": list(profile.report_names or []),
        "owner": profile.owner,
        "storage_region": profile.storage_region,
        "last_write_at": profile.last_write_at.isoformat() if profile.last_write_at else None,
        "hot_score": hot.hot_score,
        "suggested_tier": hot.suggested_tier,
        "monthly_cost": monthly_cost,
        "cold_save_month": cold_save,
        "risk": verdict.risk,
        "risk_reason": verdict.reasons,
    }


def list_tables(
    db: Session,
    group,
    *,
    tier: str | None = None,
    layer: str | None = None,
    q: str | None = None,
    sort: str = "size",
    only_candidates: bool = False,
) -> dict:
    scores = heat_service.compute_scores(db, group)
    stmt = select(TableProfile)
    if tier:
        stmt = stmt.where(TableProfile.tier == tier)
    if layer:
        stmt = stmt.where(TableProfile.layer == layer)
    if q:
        stmt = stmt.where(TableProfile.full_name.ilike(f"%{q.strip()}%"))
    profiles = list(db.execute(stmt).scalars().all())

    items = [_row(profile, scores[str(profile.id)], group) for profile in profiles if str(profile.id) in scores]
    if only_candidates:
        items = [item for item in items if item["tier"] != StorageTier.COLD and item["hot_score"] < group.warm_score_min]

    if sort == "score":
        items.sort(key=lambda item: (item["hot_score"], item["size_gb"]), reverse=True)
    elif sort == "name":
        items.sort(key=lambda item: item["full_name"])
    elif sort == "save":
        items.sort(key=lambda item: item["cold_save_month"], reverse=True)
    else:
        items.sort(key=lambda item: item["size_gb"], reverse=True)

    return {
        "items": items,
        "meta": {
            "total": len(items),
            "returned": len(items),
            "filters": {"tier": tier, "layer": layer, "q": q, "sort": sort},
        },
    }


def get_detail(db: Session, group, table_id: str) -> dict:
    key = parse_uuid(table_id)
    profile = db.get(TableProfile, key) if key is not None else None
    if profile is None:
        raise not_found("TableProfile", table_id)
    scores = heat_service.compute_scores(db, group)
    hot = scores.get(str(profile.id))
    if hot is None:
        raise AppError(codes.NOT_FOUND, "表热度尚未计算", f"table_id={table_id}")
    points = heat_service.load_series(db, str(profile.id))
    econ = cost_service.economics(float(profile.size_gb), profile.tier, group)
    verdict = cost_service.assess_risk(profile, hot, group)
    row = _row(profile, hot, group)

    others = [
        item
        for item in (
            _row(other, scores[str(other.id)], group)
            for other in db.execute(
                select(TableProfile)
                .where(TableProfile.layer == profile.layer, TableProfile.id != profile.id)
                .order_by(TableProfile.size_gb.desc())
                .limit(4)
            ).scalars().all()
            if str(other.id) in scores
        )
    ]

    return {
        "profile": row,
        "heat": hot.to_dict(),
        "series": heat_service.series_payload(points),
        "economics": {
            **econ.to_dict(),
            "current_tier": profile.tier,
            "monthly_cost": row["monthly_cost"],
            "size_gb": float(profile.size_gb),
            "row_count": int(profile.row_count),
            "compression": profile.compression,
            "partition_count": int(profile.partition_count),
        },
        "risk": {"risk": verdict.risk, "reasons": verdict.reasons, "checks": verdict.checks},
        "neighbours": [
            {
                "id": item["id"],
                "full_name": item["full_name"],
                "size_gb": item["size_gb"],
                "tier": item["tier"],
                "hot_score": item["hot_score"],
            }
            for item in others
        ],
    }
