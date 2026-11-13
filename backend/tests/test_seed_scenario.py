"""真实 seed 场景复算：不连库，用 fixtures 定义 + 纯函数层复现 batch-plan §5.6 的验收数字。

这层测试的价值：算法一旦改动（半衰期、加成、排序键、回收期口径），
文档里承诺的 12 张 / ¥6,840 / ¥51,300 / 1.8 月会立刻失败。
"""
from __future__ import annotations

import pytest

from scripts import fixtures
from src.services import cost_core, heat_core, savings_core

from tests.conftest import (
    HEAT_HALF_LIFE_DAYS,
    PRICES,
    build_candidate_rows,
    build_seed_metrics,
    seeded_counts,
)


def test_seed_fixture_shape() -> None:
    """seed 契约：42 表 = 12 热 + 18 温 + 12 冷；43,008 GB = 42 TB；访问行 3,600。"""
    counts = {"hot": 0, "warm": 0, "cold": 0}
    for spec in fixtures.TABLES:
        counts[spec.tier] += 1
    assert len(fixtures.TABLES) == 42
    assert counts == fixtures.EXPECTED_TIER_COUNT
    assert sum(spec.size_gb for spec in fixtures.TABLES) == pytest.approx(43008.0)
    assert sum(spec.size_gb for spec in fixtures.TABLES if spec.tier == "hot") == pytest.approx(13680.0)
    assert sum(spec.access_days for spec in fixtures.TABLES) == 3600


def test_heat_scores_reproduce_seeded_snapshot(seed_metrics: dict[str, dict]) -> None:
    """复算出的热度分与真机验收逐字一致：交易明细 3.5、优惠券 16.4、最热表 100。"""
    assert seed_metrics["dwd.trade_order_detail"]["hot_score"] == pytest.approx(3.5)
    assert seed_metrics["dwd.coupon_use_detail"]["hot_score"] == pytest.approx(16.4)
    assert seed_metrics["dwd.member_order_fact"]["hot_score"] == pytest.approx(100.0)
    # 12 张热区表全部低于阈值 20（这才是它们能被降冷的前提）
    hot_tier = [item for item in seed_metrics.values() if item["spec"].tier == "hot"]
    assert len(hot_tier) == 12
    assert all(item["hot_score"] < 20 for item in hot_tier)
    # 优惠券表引用 2 张报表 -> 加成 16 分（decay 0.4 左右）
    assert seed_metrics["dwd.coupon_use_detail"]["decay_score"] == pytest.approx(0.418, abs=0.01)


def test_trial_scenario_reproduces_documented_numbers(trial_hits: list[dict]) -> None:
    """试算（阈值 20）：命中 12 张 / 13,680 GB / 月省 6,840 / 年省 82,080 / 2 block + 2 warn。"""
    summary = savings_core.aggregate(trial_hits)
    assert summary["count"] == 12
    assert summary["size_total_gb"] == 13680.0
    assert summary["save_month"] == 6840.0
    assert summary["save_year"] == 82080.0
    assert (summary["risk_block_count"], summary["risk_warn_count"]) == (2, 2)
    assert all(item["tier"] == "hot" for item in trial_hits)
    assert sum(1 for spec in fixtures.TABLES if spec.tier != "cold") == 30   # evaluated_count


def test_recheck_and_blocker_removal_flow(trial_hits: list[dict]) -> None:
    """风险复检（前 8 张）：2 block + 1 warn；移除 2 张阻断后 6 张 = ¥51,300 / 1.8 月。"""
    top8 = trial_hits[:8]
    assert [item["full_name"] for item in top8] == list(fixtures.PRIMARY_FLOW_SELECTION)

    blocks = [item for item in top8 if item["risk"] == "block"]
    warns = [item for item in top8 if item["risk"] == "warn"]
    assert [item["full_name"] for item in blocks] == [
        "ads.monthly_finance_report_base",
        "dws.store_daily_gmv",
    ]
    assert [item["full_name"] for item in warns] == ["dwd.coupon_use_detail"]
    # block 的判定依据是近 7 天仍有访问
    assert all(item["recent_block_access"] > 0 for item in blocks)
    assert all(item["recent_block_access"] == 0 for item in top8 if item["risk"] != "block")

    remaining = [item for item in top8 if item["risk"] != "block"]
    summary = savings_core.aggregate(remaining)
    assert summary["count"] == 6
    assert summary["save_year"] == 60480.0
    assert summary["migration_cost"] == 9180.0
    assert summary["net_save_year"] == 51300.0
    assert summary["avg_payback"] == 1.8


def test_single_table_economics_match_plan_items(trial_hits: list[dict]) -> None:
    """逐表数字与 CSV 工单口径对齐（交易明细 4800 GB：月省 2400 / 迁移 3870 / 回收期 1.6）。"""
    row = next(item for item in trial_hits if item["full_name"] == "dwd.trade_order_detail")
    assert row["save_month"] == 2400.0
    assert row["migration_cost"] == 3870.0
    assert row["payback_months"] == 1.6
    assert row["net_save_year"] == 24930.0
    assert row["reasons"] == "近 7 天零访问、无报表引用、分区数满足灰度要求"


def test_invariants_over_full_seed(candidate_rows: list[dict]) -> None:
    """不变量：热度 ∈ [0,100]；节省率 ∈ [0,1]；有月省时回收期 > 0 且净年省 < 年省。"""
    for row in candidate_rows:
        assert 0.0 <= row["hot_score"] <= 100.0
        if row["size_gb"] > 0:
            cost_before = row["size_gb"] * PRICES[row["tier"]]
            assert 0.0 <= row["save_month"] / cost_before <= 1.0
        if row["save_month"] > 0:
            assert row["payback_months"] > 0
            assert row["net_save_year"] < row["save_month"] * 12


def test_heat_metrics_are_deterministic(seed_metrics: dict[str, dict]) -> None:
    """确定性：同一 seed 输入再算一次，42 张表热度分逐字相同。"""
    again = {}
    for spec in fixtures.TABLES:
        agg = heat_core.aggregate_access(
            seeded_counts(spec), half_life=HEAT_HALF_LIFE_DAYS, block_recent_days=7, quiet_days=30
        )
        again[spec.full_name] = agg["weighted"]
    first = {name: item["weighted"] for name, item in seed_metrics.items()}
    assert again == first

    rebuilt = build_candidate_rows(build_seed_metrics())
    assert [row["hot_score"] for row in rebuilt] == [
        item["hot_score"] for item in seed_metrics.values()
    ]


def test_risk_gate_uses_cost_core_thresholds() -> None:
    """闸门阈值全部来自策略（7 / 3 / 30），改参数应改变判定，而不是写死在业务里。"""
    strict = cost_core.assess_risk(
        recent_block_access=0, report_refs=0, partition_count=4,
        block_recent_days=7, min_partition=5, quiet_days=30,
    )
    relaxed = cost_core.assess_risk(
        recent_block_access=0, report_refs=0, partition_count=4,
        block_recent_days=7, min_partition=3, quiet_days=30,
    )
    assert strict["risk"] == "warn"      # 4 < 5
    assert relaxed["risk"] == "ok"       # 4 >= 3
