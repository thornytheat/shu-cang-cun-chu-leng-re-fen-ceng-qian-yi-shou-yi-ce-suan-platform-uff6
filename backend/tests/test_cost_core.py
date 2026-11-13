"""算法 2（净收益 / 回收期 / 风险闸门）纯函数单测。

期望值来源：batch-plan §5.6 的口径手算（热区 1.05 / 冷区 0.55 / 迁移 0.75+270/表），
体积取 seed 真实表（4800 GB 交易明细、240 GB 单分区看板缓存等）。
"""
from __future__ import annotations

import pytest

from src.services import cost_core

# seed 策略单价
HOT, WARM, COLD = 1.05, 0.85, 0.55
MIGRATE_PRICE, MIGRATE_FIXED = 0.75, 270.0


def _econ(size_gb: float, price_before: float = HOT) -> dict:
    return cost_core.economics(
        size_gb,
        price_before,
        COLD,
        migrate_price=MIGRATE_PRICE,
        migrate_fixed=MIGRATE_FIXED,
    )


# --------------------------------------------------------------- 正常路径 ----
def test_economics_real_seed_row() -> None:
    """dwd.trade_order_detail：4800 GB 热区 -> 冷区，全部字段手算。"""
    payload = _econ(4800)
    assert payload == {
        "price_before": 1.05,
        "price_after": 0.55,
        "cost_before": 5040.0,       # 4800 × 1.05
        "cost_after": 2640.0,        # 4800 × 0.55
        "save_month": 2400.0,        # 4800 × 0.50
        "save_year": 28800.0,
        "migration_cost": 3870.0,    # 4800 × 0.75 + 270
        "payback_months": 1.6,       # 3870 / 2400 = 1.6125 -> 1.6
        "net_save_year": 24930.0,    # 28800 - 3870
    }


def test_economics_small_table_rounds_payback_half_up() -> None:
    """ads.bi_dashboard_cache：240 GB -> 月省 120，回收期 450/120 = 3.75 -> 3.8。"""
    payload = _econ(240)
    assert payload["save_month"] == 120.0
    assert payload["migration_cost"] == 450.0
    assert payload["payback_months"] == 3.8
    assert payload["net_save_year"] == 990.0


def test_economics_uses_current_tier_price() -> None:
    """温区表按 0.85 计价（不是热区 1.05）：960 GB 月省 288，回收期 990/288 = 3.4。"""
    payload = _econ(960, price_before=WARM)
    assert payload["cost_before"] == 816.0
    assert payload["cost_after"] == 528.0
    assert payload["save_month"] == 288.0
    assert payload["payback_months"] == 3.4      # 3.4375 -> 3.4（1 位小数）
    assert payload["net_save_year"] == 2466.0    # 3456 - 990


# ------------------------------------------------------------------ 边界 ----
def test_economics_zero_size_degrades_to_no_saving() -> None:
    """0 GB：月省 0 -> 回收期 None（不返回 inf），首年净省 = -270 工单成本。"""
    payload = _econ(0)
    assert payload["save_month"] == 0.0
    assert payload["payback_months"] is None
    assert payload["migration_cost"] == 270.0
    assert payload["net_save_year"] == -270.0


def test_economics_equal_prices_have_no_payback() -> None:
    """价差为 0（已在冷区价）：月省 0，回收期 None。"""
    payload = _econ(1000, price_before=COLD)
    assert payload["save_month"] == 0.0
    assert payload["payback_months"] is None
    assert payload["net_save_year"] == -1020.0   # 0 - (750 + 270)


def test_payback_months_none_when_no_saving() -> None:
    assert cost_core.payback_months(1000.0, 0.0) is None
    assert cost_core.payback_months(1000.0, -5.0) is None
    assert cost_core.payback_months(1000.0, 400.0) == 2.5


# ------------------------------------------------------- 风险闸门（分级） ----
def test_assess_risk_block_wins_over_warn() -> None:
    """近 7 天有访问 + 报表引用 + 单分区：block 优先级最高，三条检查全量返回。"""
    verdict = cost_core.assess_risk(
        recent_block_access=103,
        report_refs=2,
        partition_count=1,
        report_names=["促销效果周报", "渠道费用月报"],
    )
    assert verdict["risk"] == "block"
    assert [check["name"] for check in verdict["checks"]] == [
        "recent_access",
        "report_refs",
        "partition_count",
    ]
    assert [check["level"] for check in verdict["checks"]] == ["block", "warn", "warn"]
    assert "近 7 天仍有 103 次访问" in verdict["reasons"]
    assert "被 2 张报表引用（促销效果周报、渠道费用月报）" in verdict["reasons"]


def test_assess_risk_report_refs_is_warn() -> None:
    verdict = cost_core.assess_risk(recent_block_access=0, report_refs=2, partition_count=12)
    assert verdict["risk"] == "warn"
    assert "需报表 owner 确认" in verdict["reasons"]


def test_assess_risk_low_partition_is_warn() -> None:
    verdict = cost_core.assess_risk(recent_block_access=0, report_refs=0, partition_count=1)
    assert verdict["risk"] == "warn"
    assert verdict["reasons"] == "仅 1 个分区（< 3），无法按分区灰度回迁"


def test_assess_risk_ok_reason_is_canonical() -> None:
    verdict = cost_core.assess_risk(recent_block_access=0, report_refs=0, partition_count=36)
    assert verdict["risk"] == "ok"
    assert verdict["reasons"] == "近 7 天零访问、无报表引用、分区数满足灰度要求"
    assert [check["level"] for check in verdict["checks"]] == ["ok", "ok", "ok"]


def test_assess_risk_missing_fields_degrade_to_warn() -> None:
    """字段缺失（None）：按 0 降级 —— 分区数未知会被判 warn，绝不静默放过。"""
    verdict = cost_core.assess_risk(recent_block_access=None, report_refs=None, partition_count=None)
    assert verdict["risk"] == "warn"
    assert verdict["checks"][1] == {"name": "report_refs", "level": "ok", "value": 0}
    assert verdict["checks"][2] == {"name": "partition_count", "level": "warn", "value": 0}


_RANK = {"ok": 0, "warn": 1, "block": 2}

# 异常程度递增的输入序列：期望风险等级按 ok <= warn <= block 单调不减
_ANOMALY_LADDER = [
    (0, 0, 36),      # 全部干净 -> ok
    (0, 0, 2),       # 分区不足 -> warn
    (0, 2, 36),      # 报表引用 -> warn
    (0, 2, 1),       # warn + warn 仍是 warn
    (5, 0, 36),      # 近 7 天有访问 -> block
    (5, 2, 1),       # 三重异常 -> block
]


def test_assess_risk_level_monotonic_by_anomaly() -> None:
    ranks = [
        _RANK[
            cost_core.assess_risk(
                recent_block_access=recent, report_refs=refs, partition_count=partitions
            )["risk"]
        ]
        for recent, refs, partitions in _ANOMALY_LADDER
    ]
    assert ranks == [0, 1, 1, 1, 2, 2]
    assert all(later >= earlier for earlier, later in zip(ranks, ranks[1:]))


# ------------------------------------------------------------ 异常输入 ----
@pytest.mark.parametrize("size_gb", [-1, -4800.5])
def test_economics_rejects_negative_size(size_gb: float) -> None:
    with pytest.raises(ValueError, match="size_gb 必须 >= 0"):
        _econ(size_gb)


@pytest.mark.parametrize(
    ("price_before", "price_after"),
    [(-1.0, 0.55), (1.05, -0.55)],
)
def test_economics_rejects_negative_prices(price_before: float, price_after: float) -> None:
    with pytest.raises(ValueError, match="必须 >= 0"):
        cost_core.economics(100, price_before, price_after, 0.75, 270)
