"""解析 / 归一化工具单测：金额与比率取整口径、衰减权重形态、窗口日期。

这几个函数是「口径唯一真源」：所有金额四舍五入到分、比率/回收期保留 1 位小数，
前后端与验收数字（6,840 / 51,300 / 1.8 月）都依赖它们，所以单独锁死。
"""
from __future__ import annotations

from datetime import date

import pytest

from src.services import heat_core
from src.utils.numeric import money, ratio1, score1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0.0),
        (None, 0.0),
        (5040.0, 5040.0),
        (1.005, 1.01),      # ROUND_HALF_UP：float 陷阱用 Decimal(str(...)) 规避
        (2.675, 2.68),
        (-0.005, -0.01),    # 负数也远离零方向进位
        (6840.004, 6840.0),
    ],
)
def test_money_rounds_to_cent_half_up(value, expected: float) -> None:
    assert money(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (0, 0.0),
        (1.8214285714, 1.8),    # 计划平均回收期 9180/5040
        (1.9736842105, 2.0),    # 试算平均回收期 13500/6840
        (1.85, 1.9),            # HALF_UP
        (1.84, 1.8),
        (3.75, 3.8),            # 单表回收期 450/120
    ],
)
def test_ratio1_rounds_to_one_decimal(value, expected) -> None:
    assert ratio1(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, 0.0), (16.44, 16.4), (16.45, 16.5), (100, 100.0), (3.5, 3.5)],
)
def test_score1_rounds_half_up(value, expected: float) -> None:
    assert score1(value) == expected


def test_decay_weight_is_strictly_decreasing() -> None:
    weights = [heat_core.decay_weight(offset) for offset in range(90)]
    assert all(later < earlier for earlier, later in zip(weights, weights[1:]))


def test_decay_weight_within_unit_interval() -> None:
    """权重必须落在 (0, 1]：0 天 = 1，之后严格小于 1 且恒为正。"""
    weights = [heat_core.decay_weight(offset) for offset in range(90)]
    assert weights[0] == 1.0
    assert all(0.0 < weight < 1.0 for weight in weights[1:])


def test_window_dates_descending_contiguous_and_unique() -> None:
    days = heat_core.window_dates(date(2026, 11, 12), 90)
    assert len(days) == 90
    assert days[0] == date(2026, 11, 12)
    assert days[-1] == date(2026, 8, 15)          # 90 天窗口 = 今天 + 前 89 天
    assert all((earlier - later).days == 1 for earlier, later in zip(days, days[1:]))
    assert len(set(days)) == 90
