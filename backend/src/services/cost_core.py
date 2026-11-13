"""算法 2（迁移净收益 + 回收期 + 风险闸门）纯函数层。

只吃数值与「档案事实 dict」，**不 import Session / 不查库**，可被 pytest 直接单测。
`cost_service.py` 负责从 TierPolicy 策略组 / ORM 档案取值后调用这里，口径保持不变：

  cost_before = size_GB × price_before        # 表当前所在层单价
  cost_after  = size_GB × price_after         # 目标冷区单价
  save_month  = cost_before - cost_after
  migration_cost = size_GB × migrate_price + migrate_fixed
  payback_months = migration_cost / save_month          （save_month ≤ 0 -> None）
  net_save_year  = save_month × 12 - migration_cost

风险闸门优先级 block > warn > ok：
  近 block_recent_days 天有访问 -> block
  report_refs > 0              -> warn（需报表 owner 确认）
  partition_count < min_partition -> warn（无法按分区灰度回迁）
"""
from __future__ import annotations

from src.constants.enums import RiskLevel
from src.utils.numeric import money, ratio1

DEFAULT_MIGRATE_PRICE = 0.75
DEFAULT_MIGRATE_FIXED = 270.0
DEFAULT_BLOCK_RECENT_DAYS = 7
DEFAULT_MIN_PARTITION = 3
DEFAULT_QUIET_DAYS = 30


def payback_months(migration_cost: float, save_month: float) -> float | None:
    """回收期（月，1 位小数）；月省 ≤ 0 时无意义 -> None（明确降级，不返回 inf/负值）。"""
    if save_month is None or float(save_month) <= 0:
        return None
    return ratio1(float(migration_cost) / float(save_month))


def economics(
    size_gb: float,
    price_before: float,
    price_after: float,
    migrate_price: float = DEFAULT_MIGRATE_PRICE,
    migrate_fixed: float = DEFAULT_MIGRATE_FIXED,
) -> dict:
    """单表净收益测算。负体积没有业务含义 -> ValueError（不静默返回负节省额）。"""
    size = float(size_gb)
    if size < 0:
        raise ValueError(f"size_gb 必须 >= 0，收到 {size_gb}")
    if price_before < 0 or price_after < 0 or migrate_price < 0 or migrate_fixed < 0:
        raise ValueError("单价 / 迁移成本必须 >= 0")

    cost_before = size * float(price_before)
    cost_after = size * float(price_after)
    save_month = cost_before - cost_after
    migration_cost = size * float(migrate_price) + float(migrate_fixed)
    net_save_year = save_month * 12 - migration_cost
    return {
        "price_before": money(price_before),
        "price_after": money(price_after),
        "cost_before": money(cost_before),
        "cost_after": money(cost_after),
        "save_month": money(save_month),
        "save_year": money(save_month * 12),
        "migration_cost": money(migration_cost),
        "payback_months": payback_months(migration_cost, save_month),
        "net_save_year": money(net_save_year),
    }


def assess_risk(
    *,
    recent_block_access: int | None,
    report_refs: int | None,
    partition_count: int | None,
    report_names: list[str] | None = None,
    block_recent_days: int = DEFAULT_BLOCK_RECENT_DAYS,
    min_partition: int = DEFAULT_MIN_PARTITION,
    quiet_days: int = DEFAULT_QUIET_DAYS,
) -> dict:
    """风险闸门。缺失字段（None）按 0 处理并降级为 warn，而不是崩溃或静默放过。"""
    checks: list[dict] = []
    blocked = False
    warned = False
    reasons: list[str] = []

    recent = int(recent_block_access or 0)
    if recent > 0:
        blocked = True
        checks.append({"name": "recent_access", "level": RiskLevel.BLOCK, "value": recent})
        reasons.append(
            f"近 {block_recent_days} 天仍有 {recent} 次访问（冷存要求近 {quiet_days} 天零访问）"
        )
    else:
        checks.append({"name": "recent_access", "level": RiskLevel.OK, "value": 0})

    refs = int(report_refs or 0)
    if refs > 0:
        warned = True
        names = "、".join(report_names or []) or f"{refs} 张报表"
        checks.append({"name": "report_refs", "level": RiskLevel.WARN, "value": refs})
        reasons.append(f"被 {refs} 张报表引用（{names}），需报表 owner 确认")
    else:
        checks.append({"name": "report_refs", "level": RiskLevel.OK, "value": 0})

    partitions = int(partition_count or 0)
    if partitions < min_partition:
        warned = True
        checks.append({"name": "partition_count", "level": RiskLevel.WARN, "value": partitions})
        reasons.append(f"仅 {partitions} 个分区（< {min_partition}），无法按分区灰度回迁")
    else:
        checks.append({"name": "partition_count", "level": RiskLevel.OK, "value": partitions})

    if blocked:
        risk = RiskLevel.BLOCK
    elif warned:
        risk = RiskLevel.WARN
    else:
        risk = RiskLevel.OK
        reasons = ["近 7 天零访问、无报表引用、分区数满足灰度要求"]
    return {"risk": risk, "reasons": "；".join(reasons), "checks": checks}
