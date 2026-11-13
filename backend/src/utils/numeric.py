"""金额与比率口径：统一四舍五入到分/一位小数，避免各处散落 round()。"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ONE_DP = Decimal("0.1")


def money(value: float | Decimal | int | None) -> float:
    """金额保留 2 位（分）。"""
    if value is None:
        return 0.0
    return float(Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP))


def ratio1(value: float | Decimal | None) -> float | None:
    """比率/月份保留 1 位（回收期展示口径 1.8 月）。"""
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(ONE_DP, rounding=ROUND_HALF_UP))


def score1(value: float | Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(Decimal(str(value)).quantize(ONE_DP, rounding=ROUND_HALF_UP))
