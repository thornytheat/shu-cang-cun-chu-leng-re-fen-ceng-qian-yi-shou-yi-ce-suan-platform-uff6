"""聚合口径纯函数层（试算 / 计划汇总 / 候选排序 / 阈值校验）。

试算与计划提交共用同一套汇总口径（batch-plan §5.6）：

  save_month     = Σ 逐表月省
  save_year      = save_month × 12
  migration_cost = Σ（size × 迁移单价 + 每表固定工单成本）
  net_save_year  = Σ 逐表首年净省 = save_year - migration_cost
  avg_payback    = migration_cost / save_month（总量加权，1.8 月即此口径）

只吃 dict 或带同名属性的对象，不 import Session，可被 pytest 直接单测。
"""
from __future__ import annotations

from src.constants.enums import RiskLevel, StorageTier
from src.services.cost_core import payback_months
from src.utils.numeric import money

MAX_TRIAL_ROWS = 200
MAX_PLAN_ITEMS = 60

_FIELDS = (
    "size_gb",
    "save_month",
    "migration_cost",
    "net_save_year",
    "risk",
    "hot_score",
    "tier",
    "table_name",
    "full_name",
)


def _field(item, name):
    if isinstance(item, dict):
        return item[name]
    return getattr(item, name)


def aggregate(items: list) -> dict:
    """一次汇总。空输入 -> 全 0 且 avg_payback=None（明确降级，不抛异常）。"""
    count = len(items)
    size_total = sum(float(_field(item, "size_gb")) for item in items)
    save_month = sum(float(_field(item, "save_month")) for item in items)
    migration = sum(float(_field(item, "migration_cost")) for item in items)
    net = sum(float(_field(item, "net_save_year")) for item in items)
    return {
        "count": count,
        "size_total_gb": money(size_total),
        "save_month": money(save_month),
        "save_year": money(save_month * 12),
        "migration_cost": money(migration),
        "net_save_year": money(net),
        "avg_payback": payback_months(migration, save_month),
        "risk_block_count": sum(1 for item in items if _field(item, "risk") == RiskLevel.BLOCK),
        "risk_warn_count": sum(1 for item in items if _field(item, "risk") == RiskLevel.WARN),
    }


def validate_threshold(value) -> float:
    """试算阈值必须落在 [0, 100]；非法值抛 ValueError（由 service 转成 422）。"""
    try:
        threshold = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - 路由层 schema 已经拦住
        raise ValueError(f"threshold 必须是数字，收到 {value!r}") from exc
    if threshold < 0 or threshold > 100:
        raise ValueError(f"threshold 必须落在 0 到 100 之间，收到 {value!r}")
    return threshold


def select_candidates(
    rows: list[dict],
    threshold: float,
    *,
    cold_tier: str = StorageTier.COLD,
    max_rows: int = MAX_TRIAL_ROWS,
) -> list[dict]:
    """降冷候选：非冷区 + 热度分 < 阈值；按（月省, 体积）倒序，截断到 max_rows。

    排序键与 tier 过滤和 trial_service 原实现一致，保证「试算前 8 行」就是主流程 8 张表。
    """
    hits = [
        row
        for row in rows
        if row["tier"] != cold_tier and float(row["hot_score"]) < float(threshold)
    ]
    hits.sort(key=lambda item: (item["save_month"], item["size_gb"]), reverse=True)
    return hits[:max_rows]


def blockers(items: list) -> list[str]:
    """提交前剩余阻断项的表名（保持输入顺序，用于 409 的 extra.blockers）。"""
    names = []
    for item in items:
        if _field(item, "risk") == RiskLevel.BLOCK:
            names.append(_field(item, "table_name") or _field(item, "full_name"))
    return names


def check_plan_size(table_ids: list) -> None:
    """单次建计划的表数量上限校验（超限抛 ValueError）。"""
    if len(table_ids) > MAX_PLAN_ITEMS:
        raise ValueError(f"单次最多 {MAX_PLAN_ITEMS} 张表，收到 {len(table_ids)}")
