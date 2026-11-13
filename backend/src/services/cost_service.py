"""算法 2（收益部分）：净收益、回收期与风险闸门。

口径与实现分层：
  - 纯函数在 `cost_core.py`（被 pytest 直接单测，不碰 DB）；
  - 本模块负责从 TierPolicy 策略组 / ORM 档案取值，再委托 core，返回结构化结果。

  price_before = 表当前所在层的单价（热区候选即 hot_price）
  price_after  = 冷区单价
  cost_before  = size_GB × price_before
  cost_after   = size_GB × price_after
  save_month   = cost_before - cost_after
  migration_cost = size_GB × migrate_price + migrate_fixed      # 跨区重写流量 + 每表工单/校验人工
  payback_months = migration_cost / save_month
  net_save_year  = save_month × 12 - migration_cost             # 首年净省（扣掉一次性迁移成本）

风险闸门（优先级 block > warn > ok）：
  近 block_recent_days(7) 天有访问          -> block（违反冷存前置条件，必须打回）
  被报表引用 report_refs > 0                -> warn（需报表 owner 书面确认）
  分区数 < min_partition(3)                 -> warn（无法按分区灰度、回迁成本高）
"""
from __future__ import annotations

from dataclasses import dataclass

from src.constants.enums import StorageTier
from src.services import cost_core


@dataclass
class Economics:
    price_before: float
    price_after: float
    cost_before: float
    cost_after: float
    save_month: float
    save_year: float
    migration_cost: float
    payback_months: float | None
    net_save_year: float

    def to_dict(self) -> dict:
        return {
            "price_before": self.price_before,
            "price_after": self.price_after,
            "cost_before": self.cost_before,
            "cost_after": self.cost_after,
            "save_month": self.save_month,
            "save_year": self.save_year,
            "migration_cost": self.migration_cost,
            "payback_months": self.payback_months,
            "net_save_year": self.net_save_year,
        }


@dataclass
class RiskVerdict:
    risk: str
    reasons: str
    checks: list[dict]


def economics(size_gb: float, from_tier: str, group) -> Economics:
    payload = cost_core.economics(
        size_gb,
        group.price(from_tier),
        group.price(StorageTier.COLD),
        migrate_price=group.migrate_price,
        migrate_fixed=group.migrate_fixed,
    )
    return Economics(**payload)


def assess_risk(profile, hot, group) -> RiskVerdict:
    payload = cost_core.assess_risk(
        recent_block_access=getattr(hot, "recent_7_access", 0),
        report_refs=getattr(profile, "report_refs", 0),
        partition_count=getattr(profile, "partition_count", 0),
        report_names=getattr(profile, "report_names", None),
        block_recent_days=group.block_recent_days,
        min_partition=group.min_partition,
        quiet_days=group.quiet_days,
    )
    return RiskVerdict(payload["risk"], payload["reasons"], payload["checks"])
