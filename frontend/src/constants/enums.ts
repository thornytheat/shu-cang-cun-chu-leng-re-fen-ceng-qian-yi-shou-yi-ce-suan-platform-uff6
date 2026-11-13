// 共享枚举（前端镜像）——后端真源：backend/src/constants/enums.py
// 出现位置：types/domain.ts、constants/enums.ts（本文件）、components/common/TierBadge.vue、
// components/common/RiskBadge.vue、components/domain/ShelfTable.vue、pages/*.vue
import type { DwLayer, PlanItemStatus, PlanStatus, ReceiptResult, RiskLevel, StorageTier } from '../types/domain'

export const STORAGE_TIERS: StorageTier[] = ['hot', 'warm', 'cold']
export const DW_LAYERS: DwLayer[] = ['ods', 'dwd', 'dws', 'ads']
export const RISK_LEVELS: RiskLevel[] = ['block', 'warn', 'ok']

export const TIER_LABELS: Record<StorageTier, string> = {
  hot: '热区',
  warm: '温区',
  cold: '冷区',
}

export const TIER_CODES: Record<StorageTier, string> = {
  hot: 'H',
  warm: 'W',
  cold: 'C',
}

export const TIER_HINT: Record<StorageTier, string> = {
  hot: '在线高带宽 · 单价最高',
  warm: '低频标准存储',
  cold: '对象存储归档 · 单价最低',
}

export const LAYER_LABELS: Record<DwLayer, string> = {
  ods: '贴源层',
  dwd: '明细层',
  dws: '汇总层',
  ads: '应用层',
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  block: '阻断',
  warn: '需确认',
  ok: '可迁',
}

export const PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  draft: '草稿',
  submitted: '已提交',
  executing: '执行中',
  reconciling: '待对账',
  settled: '已结算',
  approved: '已审批',
  cancelled: '已撤销',
}

export const PLAN_ITEM_STATUS_LABELS: Record<PlanItemStatus, string> = {
  pending: '待提交',
  submitted: '已提交',
  executing: '执行中',
  reconciling: '待对账',
  settled: '已结算',
  failed: '失败',
  removed: '已移除',
}

export const RECEIPT_RESULT_LABELS: Record<ReceiptResult, string> = {
  success: '成功',
  failed: '失败',
}

// 执行回执 / 账单登记的回执原因（后端 settlement_core 的 reason 字段）
export const ACK_REASON_LABELS: Record<string, string> = {
  received: '回执已登记，进入待对账',
  settled: '已结算',
  failed: '失败回执已登记，不计节省',
  duplicate: '重复单号，幂等忽略（未重复计费）',
  already_received: '已有成功回执，迟到回执忽略',
  already_settled: '已结算，不回退',
  not_executable: '计划项不在可执行状态',
  item_failed: '失败表需先重试成功再结账',
  recorded_pending_receipt: '账单先到，等待回执结算',
}

export const COMPRESSION_LABELS: Record<string, string> = {
  zstd: 'ZSTD',
  lz4: 'LZ4',
  snappy: 'SNAPPY',
  none: '未压缩',
}
