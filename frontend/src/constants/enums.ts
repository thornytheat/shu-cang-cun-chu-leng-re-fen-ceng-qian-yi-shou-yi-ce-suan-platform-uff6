// 共享枚举（前端镜像）——后端真源：backend/src/constants/enums.py
// 出现位置：types/domain.ts、constants/enums.ts（本文件）、components/common/TierBadge.vue、
// components/common/RiskBadge.vue、components/domain/ShelfTable.vue、pages/*.vue
import type { DwLayer, PlanStatus, RiskLevel, StorageTier } from '../types/domain'

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
  approved: '已审批',
  cancelled: '已撤销',
}

export const COMPRESSION_LABELS: Record<string, string> = {
  zstd: 'ZSTD',
  lz4: 'LZ4',
  snappy: 'SNAPPY',
  none: '未压缩',
}
