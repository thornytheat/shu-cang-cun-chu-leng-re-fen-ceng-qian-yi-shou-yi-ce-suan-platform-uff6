export type StorageTier = 'hot' | 'warm' | 'cold'
export type DwLayer = 'ods' | 'dwd' | 'dws' | 'ads'
export type RiskLevel = 'block' | 'warn' | 'ok'
export type PlanStatus =
  | 'draft'
  | 'submitted'
  | 'executing'
  | 'reconciling'
  | 'settled'
  | 'approved'
  | 'cancelled'
export type PlanItemStatus =
  | 'pending'
  | 'submitted'
  | 'executing'
  | 'reconciling'
  | 'settled'
  | 'failed'
  | 'removed'
export type ReceiptResult = 'success' | 'failed'

export interface TableRow {
  id: string
  full_name: string
  layer: DwLayer
  tier: StorageTier
  size_gb: number
  partition_count: number
  compression: string
  report_refs: number
  report_names: string[]
  owner: string
  storage_region: string
  last_write_at: string | null
  hot_score: number
  suggested_tier: StorageTier
  monthly_cost: number
  cold_save_month: number
  risk: RiskLevel
  risk_reason: string
}

export interface AccessPoint {
  stat_date: string
  access_count: number
  query_count: number
  scan_bytes: number
  decay_weight: number
  weighted_access: number
}

export interface HotScore {
  table_id: string
  full_name: string
  hot_score: number
  decay_score: number
  report_bonus: number
  weighted_access: number
  recent_7_access: number
  recent_30_access: number
  total_90_access: number
  suggested_tier: StorageTier
  suggested_reason: string
  computed_at: string
  window_days: number
  half_life_days: number
}

export interface Economics {
  price_before: number
  price_after: number
  cost_before: number
  cost_after: number
  save_month: number
  save_year: number
  migration_cost: number
  payback_months: number | null
  net_save_year: number
}

export interface RiskCheck {
  name: string
  level: RiskLevel
  value: number
}

export interface TableDetail {
  profile: TableRow
  heat: HotScore
  series: AccessPoint[]
  economics: Economics & {
    current_tier: StorageTier
    monthly_cost: number
    size_gb: number
    row_count: number
    compression: string
    partition_count: number
  }
  risk: { risk: RiskLevel; reasons: string; checks: RiskCheck[] }
  neighbours: Array<{
    id: string
    full_name: string
    size_gb: number
    tier: StorageTier
    hot_score: number
  }>
}

export interface TierBucket {
  tier: StorageTier
  table_count: number
  size_gb: number
  monthly_cost: number
  unit_price: number
  share_pct: number
}

export interface LayerCell {
  layer: DwLayer
  tier: StorageTier
  table_count: number
  size_gb: number
  monthly_cost: number
}

export interface AuditEntry {
  id: string
  action: string
  actor_email: string
  actor_role: string
  entity_type: string
  entity_id: string
  detail: Record<string, unknown>
  trace_id: string
  created_at: string
}

export interface Overview {
  brand: string
  org_name: string
  generated_at: string
  table_count: number
  total_size_gb: number
  total_size_tb: number
  monthly_cost: number
  year_cost: number
  tier_buckets: TierBucket[]
  layer_cells: LayerCell[]
  cold_saving_month: number
  cold_saving_year: number
  candidate_count: number
  block_count: number
  warn_count: number
  hot_table: { full_name: string; hot_score: number; size_gb: number; tier: StorageTier; report_refs: number } | null
  coldest_candidate: {
    full_name: string
    size_gb: number
    save_month: number
    payback_months: number | null
    hot_score: number
    table_id: string
    economics: Economics
  } | null
  policy_version: number
  last_heat_at: string | null
  audit_tail: AuditEntry[]
}

export interface PolicyTier {
  code: string
  tier: StorageTier
  title: string
  version: number
  score_min: number
  unit_price: number
  target_region: string
  quiet_days: number
  block_recent_days: number
  min_partition: number
  migrate_price: number
  migrate_fixed: number
  updated_by: string
  updated_at: string
  is_current: boolean
}

export interface PolicyGroup {
  version: number
  is_current: boolean
  tiers: PolicyTier[]
  heat_window_days: number
  heat_half_life_days: number
  report_bonus_per_ref: number
  report_bonus_cap: number
}

export interface TrialHit {
  table_id: string
  full_name: string
  layer: DwLayer
  tier: StorageTier
  size_gb: number
  partition_count: number
  report_refs: number
  hot_score: number
  suggested_tier: StorageTier
  save_month: number
  migration_cost: number
  payback_months: number | null
  net_save_year: number
  risk: RiskLevel
  reasons: string
  recent_7_access: number
  recent_30_access: number
}

export interface TrialResult {
  policy_version: number
  threshold: number
  hit_count: number
  evaluated_count: number
  size_total_gb: number
  save_month: number
  save_year: number
  migration_cost: number
  net_save_year: number
  avg_payback: number | null
  risk_block_count: number
  risk_warn_count: number
  hits: TrialHit[]
  computed_at: string
}

export interface PlanItem {
  id: string
  table_id: string
  table_name: string
  from_tier: StorageTier
  suggested_tier: StorageTier
  size_gb: number
  hot_score: number
  save_month: number
  migration_cost: number
  payback_months: number | null
  net_save_year: number
  risk: RiskLevel
  reasons: string
  status: PlanItemStatus
  status_label: string
  actual_save_month: number | null
  actual_migrate_cost: number | null
  last_receipt_no: string
  settled_at: string | null
}

export interface Plan {
  id: string
  code: string
  title: string
  status: PlanStatus
  status_label: string
  policy_version: number
  threshold: number
  total_size_gb: number
  save_month: number
  save_year: number
  migration_cost: number
  net_save_year: number
  avg_payback: number | null
  risk_block_count: number
  risk_warn_count: number
  created_by: string
  submitted_by: string
  submitted_at: string | null
  rechecked_at: string | null
  note: string
  item_count: number
  items: PlanItem[]
}

// ---------------------------------------------------------------- 执行与对账 ----
export interface ExecutionBatch {
  id: string
  batch_no: string
  note: string
  created_by: string
  receipt_count: number
  created_at: string | null
}

export interface ReconRow {
  item_id: string
  table_name: string
  status: PlanItemStatus
  result: string
  est_save_month: number
  est_migrate_cost: number
  est_net_save_year: number
  actual_save_month: number | null
  actual_migrate_cost: number | null
  save_diff: number | null
  migrate_diff: number | null
  settled_net_save_year: number | null
  missing: string[]
  receipt_no: string
  bill_no: string
  batch_no: string
  message: string
}

export interface ReconTotals {
  item_count: number
  est_save_month: number
  est_migrate_cost: number
  est_net_save_year: number
  actual_save_month: number
  actual_migrate_cost: number
  settled_net_save_year: number
  save_diff: number
  migrate_diff: number
  net_diff: number
  executing: number
  reconciling: number
  settled: number
  failed: number
  missing_receipt: number
  missing_bill: number
}

export interface PlanReconciliation {
  plan_id: string
  code: string
  status: PlanStatus
  status_label: string
  totals: ReconTotals
  missing: { no_receipt: string[]; no_bill: string[]; failed: string[] }
  batches: ExecutionBatch[]
  rows: ReconRow[]
  generated_at: string
}

export interface ExecutionAck {
  created: boolean
  touched: number
  batch: ExecutionBatch
  reconciliation: PlanReconciliation
}

export interface ReceiptAck {
  receipt_no: string
  table_name: string
  applied: boolean
  reason: string
  status: PlanItemStatus
  status_label: string
}

export interface BillAck {
  bill_no: string
  table_name: string
  applied: boolean
  reason: string
  status: PlanItemStatus
  status_label: string
}

export interface ReceiptsAck {
  results: ReceiptAck[]
  reconciliation: PlanReconciliation
}

export interface BillsAck {
  results: BillAck[]
  reconciliation: PlanReconciliation
}
