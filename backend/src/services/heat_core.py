"""算法 1（指数衰减热度评分）纯函数层。

本模块只吃 `int/float/date/dict/list`，**不 import Session / 不查库**，因此可以被 pytest 直接单测；
`heat_service.py` 负责取数并调用这里的函数，口径（半衰期 14 天 / 90 天窗口 / 引用加成）保持不变：

  权重      w(d) = 0.5 ^ (d / half_life)，d = 距今天的天数（0 = 今天）
  加权访问  W = Σ_d access_count(d) × w(d)
  衰减分    S_decay = 100 × W / max(全部表的 W)
  引用加成  B = min(cap, per_ref × report_refs)
  热度分    S = min(100, S_decay + B)
  分层建议  S ≥ hot_min -> hot；warm_min ≤ S < hot_min -> warm；
            S < warm_min 且 quiet_days 天零访问 -> cold；否则保守留 warm。
"""
from __future__ import annotations

from datetime import date, timedelta

from src.constants.enums import StorageTier
from src.utils.numeric import score1

DEFAULT_WINDOW_DAYS = 90
DEFAULT_HALF_LIFE_DAYS = 14.0
DEFAULT_REPORT_BONUS_PER_REF = 8
DEFAULT_REPORT_BONUS_CAP = 20
DEFAULT_HOT_SCORE_MIN = 60.0
DEFAULT_WARM_SCORE_MIN = 20.0
DEFAULT_QUIET_DAYS = 30
DEFAULT_BLOCK_RECENT_DAYS = 7


def decay_weight(offset: int, half_life: float = DEFAULT_HALF_LIFE_DAYS) -> float:
    """单日权重：0.5 ** (offset / half_life)。offset 0 = 今天。

    负 offset / 非正半衰期没有业务含义（会得到 >1 或除零），显式报错而不是静默返回脏权重。
    """
    if offset < 0:
        raise ValueError(f"offset 必须 >= 0（0 = 今天），收到 {offset}")
    if half_life <= 0:
        raise ValueError(f"half_life 必须 > 0，收到 {half_life}")
    return float(0.5 ** (offset / half_life))


def window_dates(as_of: date, window_days: int = DEFAULT_WINDOW_DAYS) -> list[date]:
    """[as_of, as_of-1, ..., as_of-(window_days-1)]，下标即 offset。"""
    if window_days < 1:
        raise ValueError(f"window_days 必须 >= 1，收到 {window_days}")
    return [as_of - timedelta(days=offset) for offset in range(window_days)]


def weighted_access(counts: list[int], half_life: float = DEFAULT_HALF_LIFE_DAYS) -> float:
    """指数衰减加权访问数 W = Σ counts[offset] × w(offset)。空输入 -> 0.0。"""
    if not counts:
        return 0.0
    total = 0.0
    for offset, count in enumerate(counts):
        total += int(count) * decay_weight(offset, half_life)
    return float(total)


def aggregate_access(
    counts: list[int],
    *,
    half_life: float = DEFAULT_HALF_LIFE_DAYS,
    block_recent_days: int = DEFAULT_BLOCK_RECENT_DAYS,
    quiet_days: int = DEFAULT_QUIET_DAYS,
) -> dict:
    """一次遍历得到加权访问、近 N 天访问、窗口总访问。

    counts 长度不足窗口时视为「后续日期缺探测」= 0 次访问（降级，不报错）；
    这正是 seed 里 40 天 / 10 天窗口表的真实形态。
    """
    weighted = 0.0
    recent_block = 0
    recent_quiet = 0
    total = 0
    for offset, count in enumerate(counts):
        access = int(count)
        total += access
        weighted += access * decay_weight(offset, half_life)
        if offset < block_recent_days:
            recent_block += access
        if offset < quiet_days:
            recent_quiet += access
    return {
        "weighted": float(weighted),
        "recent_block": recent_block,
        "recent_quiet": recent_quiet,
        "total": total,
    }


def normalize_decay_scores(weighted: dict[str, float]) -> dict[str, float]:
    """S_decay = 100 × W / max(W)，max 为 0 或空输入时全部为 0.0（零方差降级）。"""
    if not weighted:
        return {}
    peak = max(float(value) for value in weighted.values())
    if peak <= 0:
        return {key: 0.0 for key in weighted}
    return {key: float(value) / peak * 100.0 for key, value in weighted.items()}


def report_bonus(
    report_refs: int | None,
    per_ref: int = DEFAULT_REPORT_BONUS_PER_REF,
    cap: int = DEFAULT_REPORT_BONUS_CAP,
) -> float:
    """报表引用加成 B = min(cap, per_ref × refs)；refs 缺失（None）视为 0。"""
    refs = int(report_refs or 0)
    if refs <= 0:
        return 0.0
    return float(min(float(cap), float(per_ref) * refs))


def combine_hot_score(decay_score: float, bonus: float) -> float:
    """S = min(100, S_decay + B)，保留 1 位小数。"""
    return score1(min(100.0, float(decay_score) + float(bonus)))


def suggest_tier(
    score: float,
    recent_quiet_access: int,
    *,
    hot_score_min: float = DEFAULT_HOT_SCORE_MIN,
    warm_score_min: float = DEFAULT_WARM_SCORE_MIN,
    quiet_days: int = DEFAULT_QUIET_DAYS,
) -> tuple[str, str]:
    """分层建议 + 人话理由（与 heat_service 原实现逐字一致）。"""
    if score >= hot_score_min:
        return StorageTier.HOT, f"热度 {score} ≥ {hot_score_min:g}，应留在热区"
    if score >= warm_score_min:
        return StorageTier.WARM, f"热度 {score} 落在 [{warm_score_min:g}, {hot_score_min:g})，温区合适"
    if recent_quiet_access == 0:
        return (
            StorageTier.COLD,
            f"热度 {score} < {warm_score_min:g} 且近 {quiet_days} 天零访问，可降冷",
        )
    return (
        StorageTier.WARM,
        f"热度 {score} < {warm_score_min:g} 但近 {quiet_days} 天仍有 {recent_quiet_access} 次访问，"
        "冷存前置条件不满足，保守留温区",
    )
