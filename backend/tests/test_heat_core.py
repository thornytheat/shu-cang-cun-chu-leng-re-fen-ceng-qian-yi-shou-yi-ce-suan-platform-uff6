"""算法 1（指数衰减热度评分）纯函数单测。

期望值来源：闭式公式 0.5^(d/14) 手算 + seed（scripts/fixtures.py）真实 90 天访问序列复算。
"""
from __future__ import annotations

from datetime import date

import pytest

from scripts import fixtures
from src.services import heat_core
from tests.conftest import seeded_counts


# --------------------------------------------------------------- 正常路径 ----
@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (0, 1.0),
        (7, 0.7071067811865476),   # 0.5 ** 0.5
        (14, 0.5),                 # 恰好一个半衰期
        (28, 0.25),
        (42, 0.125),
        (89, 0.012198580971183),   # 窗口最后一天
    ],
)
def test_decay_weight_reference_points(offset: int, expected: float) -> None:
    assert heat_core.decay_weight(offset) == pytest.approx(expected, rel=1e-12)


def test_weighted_access_flat_series_hand_computed() -> None:
    """100 次/天 × 90 天：W = 100 × Σ_{d=0..89} 0.5^(d/14) = 2046.1521590854。"""
    assert heat_core.weighted_access([100] * 90) == pytest.approx(2046.1521590854, rel=1e-9)


def test_weighted_access_decays_by_half_per_half_life() -> None:
    """同一笔访问挪后 14 天，权重恰好减半：ratio = 0.5。"""
    near = heat_core.weighted_access([1000] + [0] * 13)
    far = heat_core.weighted_access([0] * 14 + [1000])
    assert near == pytest.approx(1000.0)
    assert far / near == pytest.approx(0.5, rel=1e-12)


def test_aggregate_access_real_seed_slice() -> None:
    """真实 seed 表 dwd.trade_order_detail（base=68、近 30 天静默）。"""
    spec = next(item for item in fixtures.TABLES if item.full_name == "dwd.trade_order_detail")
    agg = heat_core.aggregate_access(
        seeded_counts(spec), half_life=14.0, block_recent_days=7, quiet_days=30
    )
    assert agg["total"] == 4088
    assert agg["weighted"] == pytest.approx(303.7703705737, rel=1e-9)
    assert agg["recent_block"] == 0
    assert agg["recent_quiet"] == 0


def test_aggregate_access_separates_block_and_quiet_windows() -> None:
    """ads.monthly_finance_report_base：近 7 天 103 次（block），近 30 天 369 次。"""
    spec = next(
        item for item in fixtures.TABLES if item.full_name == "ads.monthly_finance_report_base"
    )
    agg = heat_core.aggregate_access(
        seeded_counts(spec), half_life=14.0, block_recent_days=7, quiet_days=30
    )
    assert (agg["recent_block"], agg["recent_quiet"], agg["total"]) == (103, 369, 1090)
    assert agg["weighted"] == pytest.approx(255.8462231514, rel=1e-9)


def test_normalize_decay_scores_max_is_100() -> None:
    scores = heat_core.normalize_decay_scores({"a": 100.0, "b": 50.0, "c": 0.0})
    assert scores == {"a": 100.0, "b": 50.0, "c": 0.0}


@pytest.mark.parametrize(
    ("refs", "expected"),
    [(0, 0.0), (1, 8.0), (2, 16.0), (3, 20.0), (10, 20.0), (None, 0.0)],
)
def test_report_bonus_caps_at_20(refs, expected: float) -> None:
    assert heat_core.report_bonus(refs, per_ref=8, cap=20) == expected


@pytest.mark.parametrize(
    ("decay", "bonus", "expected"),
    [
        (3.4, 16.0, 19.4),      # 3.4 + 16
        (19.94, 0.0, 19.9),     # score1 四舍五入
        (95.55, 16.0, 100.0),   # min(100, ...) 封顶
        (100.0, 20.0, 100.0),
        (0.0, 0.0, 0.0),
    ],
)
def test_combine_hot_score_caps_at_100(decay: float, bonus: float, expected: float) -> None:
    assert heat_core.combine_hot_score(decay, bonus) == pytest.approx(expected, abs=1e-9)


# ------------------------------------------------------------------ 边界 ----
def test_empty_series_is_zero() -> None:
    assert heat_core.weighted_access([]) == 0.0
    assert heat_core.aggregate_access([]) == {
        "weighted": 0.0,
        "recent_block": 0,
        "recent_quiet": 0,
        "total": 0,
    }


def test_single_day_series() -> None:
    counts = [10]
    agg = heat_core.aggregate_access(counts)
    assert agg["total"] == 10
    assert agg["recent_block"] == 10      # 只有今天，落在近 7 天窗口内
    assert agg["recent_quiet"] == 10
    assert agg["weighted"] == pytest.approx(10.0)


def test_all_zero_series_has_zero_variance() -> None:
    """全部表都是零访问（零方差）：归一化不能除零，应返回全 0。"""
    assert heat_core.normalize_decay_scores({"a": 0.0, "b": 0.0}) == {"a": 0.0, "b": 0.0}
    assert heat_core.normalize_decay_scores({}) == {}


def test_truncated_window_degrades_to_zero_tail() -> None:
    """样本不足（只采到 10 天）：缺口按 0 次访问降级，不报错。"""
    agg = heat_core.aggregate_access([7] * 10, half_life=14.0, block_recent_days=7, quiet_days=30)
    assert agg["total"] == 70
    assert agg["recent_block"] == 49
    assert agg["recent_quiet"] == 70
    assert agg["weighted"] == pytest.approx(7 * sum(0.5 ** (d / 14) for d in range(10)), rel=1e-12)


def test_window_dates_is_contiguous_and_descending() -> None:
    days = heat_core.window_dates(date(2026, 11, 12), 3)
    assert days == [date(2026, 11, 12), date(2026, 11, 11), date(2026, 11, 10)]
    assert len(heat_core.window_dates(date(2026, 11, 12))) == 90


# ---------------------------------------------------------- 分层建议（闸门） ----
@pytest.mark.parametrize(
    ("score", "recent_quiet", "expected_tier"),
    [
        (100.0, 0, "hot"),
        (60.0, 0, "hot"),
        (59.9, 0, "warm"),
        (20.0, 0, "warm"),
        (19.9, 0, "cold"),      # 低分 + 近 30 天零访问 -> 可降冷
        (19.9, 5, "warm"),      # 低分但仍有访问 -> 冷存前置条件不满足
        (0.0, 0, "cold"),
    ],
)
def test_suggest_tier_thresholds(score: float, recent_quiet: int, expected_tier: str) -> None:
    tier, _ = heat_core.suggest_tier(score, recent_quiet)
    assert tier == expected_tier


def test_suggest_tier_reason_text() -> None:
    hot_tier, hot_reason = heat_core.suggest_tier(60.0, 0)
    assert hot_tier == "hot"
    assert hot_reason == "热度 60.0 ≥ 60，应留在热区"

    cold_tier, cold_reason = heat_core.suggest_tier(3.5, 0)
    assert cold_tier == "cold"
    assert cold_reason == "热度 3.5 < 20 且近 30 天零访问，可降冷"

    warm_tier, warm_reason = heat_core.suggest_tier(12.0, 9)
    assert warm_tier == "warm"
    assert warm_reason == "热度 12.0 < 20 但近 30 天仍有 9 次访问，冷存前置条件不满足，保守留温区"


# ------------------------------------------------------------ 异常输入 ----
@pytest.mark.parametrize("offset", [-1, -14])
def test_decay_weight_rejects_negative_offset(offset: int) -> None:
    with pytest.raises(ValueError, match="offset 必须 >= 0"):
        heat_core.decay_weight(offset)


@pytest.mark.parametrize("half_life", [0, -1.0])
def test_decay_weight_rejects_non_positive_half_life(half_life: float) -> None:
    with pytest.raises(ValueError, match="half_life 必须 > 0"):
        heat_core.decay_weight(1, half_life)


def test_window_dates_rejects_zero_window() -> None:
    with pytest.raises(ValueError, match="window_days 必须 >= 1"):
        heat_core.window_dates(date(2026, 11, 12), 0)
