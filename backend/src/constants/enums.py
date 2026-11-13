"""共享枚举（后端唯一真源）。

前端镜像：frontend/src/constants/enums.ts
出现位置（README 有完整清单）：
  storage_tier  -> TableProfile.tier / TierPolicy.tier / MigrationPlanItem.suggested_tier
  dw_layer      -> TableProfile.layer
  risk_level    -> MigrationPlanItem.risk / 风险复检响应
  plan_status   -> MigrationPlan.status / 页面筛选
  plan_item_status -> MigrationPlanItem.status
  receipt_result -> MigrationReceipt.result（逐表回执成功/失败）
  compression   -> TableProfile.compression
"""
from __future__ import annotations


class StorageTier(str):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"

    ALL = (HOT, WARM, COLD)


class DwLayer(str):
    ODS = "ods"
    DWD = "dwd"
    DWS = "dws"
    ADS = "ads"

    ALL = (ODS, DWD, DWS, ADS)


class RiskLevel(str):
    BLOCK = "block"
    WARN = "warn"
    OK = "ok"

    ALL = (BLOCK, WARN, OK)


class PlanStatus(str):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    EXECUTING = "executing"
    RECONCILING = "reconciling"
    SETTLED = "settled"
    APPROVED = "approved"
    CANCELLED = "cancelled"

    ALL = (DRAFT, SUBMITTED, EXECUTING, RECONCILING, SETTLED, APPROVED, CANCELLED)


class PlanItemStatus(str):
    PENDING = "pending"
    REMOVED = "removed"
    SUBMITTED = "submitted"
    EXECUTING = "executing"
    RECONCILING = "reconciling"
    SETTLED = "settled"
    FAILED = "failed"

    ALL = (PENDING, REMOVED, SUBMITTED, EXECUTING, RECONCILING, SETTLED, FAILED)


class ReceiptResult(str):
    SUCCESS = "success"
    FAILED = "failed"

    ALL = (SUCCESS, FAILED)


class Compression(str):
    ZSTD = "zstd"
    LZ4 = "lz4"
    SNAPPY = "snappy"
    NONE = "none"

    ALL = (ZSTD, LZ4, SNAPPY, NONE)


TIER_LABELS = {
    StorageTier.HOT: "热区",
    StorageTier.WARM: "温区",
    StorageTier.COLD: "冷区",
}

LAYER_LABELS = {
    DwLayer.ODS: "贴源层",
    DwLayer.DWD: "明细层",
    DwLayer.DWS: "汇总层",
    DwLayer.ADS: "应用层",
}

RISK_LABELS = {
    RiskLevel.BLOCK: "阻断",
    RiskLevel.WARN: "需确认",
    RiskLevel.OK: "可迁",
}

PLAN_STATUS_LABELS = {
    PlanStatus.DRAFT: "草稿",
    PlanStatus.SUBMITTED: "已提交",
    PlanStatus.EXECUTING: "执行中",
    PlanStatus.RECONCILING: "待对账",
    PlanStatus.SETTLED: "已结算",
    PlanStatus.APPROVED: "已审批",
    PlanStatus.CANCELLED: "已撤销",
}

PLAN_ITEM_STATUS_LABELS = {
    PlanItemStatus.PENDING: "待提交",
    PlanItemStatus.SUBMITTED: "已提交",
    PlanItemStatus.EXECUTING: "执行中",
    PlanItemStatus.RECONCILING: "待对账",
    PlanItemStatus.SETTLED: "已结算",
    PlanItemStatus.FAILED: "失败",
    PlanItemStatus.REMOVED: "已移除",
}

RECEIPT_RESULT_LABELS = {
    ReceiptResult.SUCCESS: "成功",
    ReceiptResult.FAILED: "失败",
}
