"""pytest 共享夹具：策略组替身 + 从 `scripts/fixtures.py` 复算真实 seed 输入。

约束：
  - **不连 DB、不连网络**：算法纯函数层（heat_core / cost_core / savings_core）只吃数值；
    这里的输入全部由 fixtures.RAW_TABLES 确定性派生（sha256 抖动，与 seed 生成器同一公式）。
  - 策略组 `FakePolicyGroup` 只提供 core 需要的价目与阈值，与 seed 的 version=3 策略一致。
"""
from __future__ import annotations

import hashlib

import pytest

from scripts import fixtures
from src.services import cost_core, heat_core, savings_core

# seed 策略（fixtures.POLICY_TIERS + POLICY_COLD_RULES）的镜像，供纯函数调用
PRICES = {"hot": 1.05, "warm": 0.85, "cold": 0.55}
HEAT_WINDOW_DAYS = 90
HEAT_HALF_LIFE_DAYS = 14.0
REPORT_BONUS_PER_REF = 8
REPORT_BONUS_CAP = 20
QUIET_DAYS = 30
BLOCK_RECENT_DAYS = 7
MIN_PARTITION = 3
MIGRATE_PRICE = 0.75
MIGRATE_FIXED = 270.0


class FakePolicyGroup:
    """TierPolicy 组合的替身：接口与 policy_service.PolicyGroup 对齐，只含 core 用到的字段。"""

    version = fixtures.POLICY_VERSION
    hot_score_min = 60.0
    warm_score_min = 20.0
    quiet_days = QUIET_DAYS
    block_recent_days = BLOCK_RECENT_DAYS
    min_partition = MIN_PARTITION
    migrate_price = MIGRATE_PRICE
    migrate_fixed = MIGRATE_FIXED

    def price(self, tier: str) -> float:
        return PRICES[tier]


def jitter(name: str, offset: int) -> float:
    """与 scripts/seed_demo.py::_jitter 完全相同的确定性抖动（0.82 ~ 1.18）。"""
    digest = hashlib.sha256(f"{name}:{offset}".encode("utf-8")).digest()
    return 0.82 + 0.36 * (int.from_bytes(digest[:2], "big") / 65535.0)


def seeded_counts(spec: fixtures.TableSpec, window_days: int = HEAT_WINDOW_DAYS) -> list[int]:
    """复算 seed 写入 access_stats 的 90 天访问序列（offset 0 = 今天，缺失日期补 0）。"""
    spikes = dict(spec.spikes)
    counts: list[int] = []
    for offset in range(spec.access_days):
        if spec.access_base == 0 or offset < spec.quiet_after:
            access = 0
        else:
            access = round(spec.access_base * jitter(spec.full_name, offset))
        counts.append(access + spikes.get(offset, 0))
    return counts + [0] * (window_days - len(counts))


def build_seed_metrics() -> dict[str, dict]:
    """42 张表的真实热度指标（含归一化后的 hot_score），复算服务端 compute_scores 口径。"""
    metrics: dict[str, dict] = {}
    for spec in fixtures.TABLES:
        agg = heat_core.aggregate_access(
            seeded_counts(spec),
            half_life=HEAT_HALF_LIFE_DAYS,
            block_recent_days=BLOCK_RECENT_DAYS,
            quiet_days=QUIET_DAYS,
        )
        metrics[spec.full_name] = {**agg, "spec": spec}

    decay = heat_core.normalize_decay_scores(
        {name: item["weighted"] for name, item in metrics.items()}
    )
    for name, item in metrics.items():
        bonus = heat_core.report_bonus(
            item["spec"].report_refs, per_ref=REPORT_BONUS_PER_REF, cap=REPORT_BONUS_CAP
        )
        item["decay_score"] = decay[name]
        item["hot_score"] = heat_core.combine_hot_score(decay[name], bonus)
    return metrics


def build_candidate_rows(metrics: dict[str, dict]) -> list[dict]:
    """按 trial_service.build_hits 的口径构造逐表候选行（纯 dict，无 DB id）。"""
    rows: list[dict] = []
    for name, item in metrics.items():
        spec = item["spec"]
        econ = cost_core.economics(
            spec.size_gb,
            PRICES[spec.tier],
            PRICES["cold"],
            migrate_price=MIGRATE_PRICE,
            migrate_fixed=MIGRATE_FIXED,
        )
        verdict = cost_core.assess_risk(
            recent_block_access=item["recent_block"],
            report_refs=spec.report_refs,
            partition_count=spec.partition_count,
            report_names=spec.report_names,
            block_recent_days=BLOCK_RECENT_DAYS,
            min_partition=MIN_PARTITION,
            quiet_days=QUIET_DAYS,
        )
        rows.append(
            {
                "table_name": name,
                "full_name": name,
                "layer": spec.layer,
                "tier": spec.tier,
                "size_gb": float(spec.size_gb),
                "partition_count": spec.partition_count,
                "report_refs": spec.report_refs,
                "hot_score": item["hot_score"],
                "save_month": econ["save_month"],
                "migration_cost": econ["migration_cost"],
                "payback_months": econ["payback_months"],
                "net_save_year": econ["net_save_year"],
                "risk": verdict["risk"],
                "reasons": verdict["reasons"],
                "recent_block_access": item["recent_block"],
                "recent_quiet_access": item["recent_quiet"],
            }
        )
    return rows


@pytest.fixture(scope="session")
def group() -> FakePolicyGroup:
    return FakePolicyGroup()


@pytest.fixture(scope="session")
def seed_metrics() -> dict[str, dict]:
    return build_seed_metrics()


@pytest.fixture(scope="session")
def candidate_rows(seed_metrics: dict[str, dict]) -> list[dict]:
    return build_candidate_rows(seed_metrics)


@pytest.fixture(scope="session")
def trial_hits(candidate_rows: list[dict]) -> list[dict]:
    """阈值 20 的降冷候选（主流程验收里的 12 张）。"""
    return savings_core.select_candidates(candidate_rows, 20.0)
