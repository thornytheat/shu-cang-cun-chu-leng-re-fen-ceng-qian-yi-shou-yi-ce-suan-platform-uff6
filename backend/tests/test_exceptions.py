"""异常输入单测：非法参数必须显式抛错，不许静默返回脏值。

对应 TEST-PLAN §1「异常输入 ≥ 2」：阈值越界、负体积、非正半衰期、非法窗口长度。
"""
from __future__ import annotations

from datetime import date

import pytest

from src.services import cost_core, heat_core, savings_core


@pytest.mark.parametrize(("value", "message"), [(-0.1, "0 到 100"), (100.1, "0 到 100"), (999, "0 到 100")])
def test_threshold_out_of_range_raises(value: float, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        savings_core.validate_threshold(value)


def test_threshold_non_numeric_raises() -> None:
    with pytest.raises(ValueError, match="threshold 必须是数字"):
        savings_core.validate_threshold("not-a-number")


def test_negative_size_raises_instead_of_dirty_saving() -> None:
    with pytest.raises(ValueError, match="size_gb 必须 >= 0"):
        cost_core.economics(-100, 1.05, 0.55)


@pytest.mark.parametrize("half_life", [0.0, -14.0])
def test_non_positive_half_life_raises(half_life: float) -> None:
    with pytest.raises(ValueError, match="half_life 必须 > 0"):
        heat_core.decay_weight(0, half_life)


def test_negative_window_raises() -> None:
    with pytest.raises(ValueError, match="window_days 必须 >= 1"):
        heat_core.window_dates(date(2026, 11, 12), -1)
