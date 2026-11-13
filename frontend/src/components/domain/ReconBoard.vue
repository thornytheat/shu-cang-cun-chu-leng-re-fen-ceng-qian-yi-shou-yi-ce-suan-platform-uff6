<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { Plan, PlanReconciliation, ReconRow } from '../../types/domain'
import { PLAN_ITEM_STATUS_LABELS, PLAN_STATUS_LABELS } from '../../constants/enums'
import { money, shortTime } from '../../utils/format'

const props = defineProps<{
  plan: Plan
  recon: PlanReconciliation
  busy: boolean
  canExecute: boolean
}>()
const emit = defineEmits<{
  (event: 'startBatch', batchNo: string): void
  (event: 'receipt', itemId: string, itemIndex: number, result: 'success' | 'failed', resend: boolean): void
  (event: 'bill', itemId: string, itemIndex: number, amount: number, billMonth: string): void
  (event: 'refresh'): void
}>()

const totals = computed(() => props.recon.totals)
const progress = computed(() => `${totals.value.settled}/${totals.value.item_count}`)

const nextBatchNo = computed(() => `MB-${props.plan.code}-${String(props.recon.batches.length + 1).padStart(2, '0')}`)
const batchNo = ref('')
function fireBatch() {
  emit('startBatch', batchNo.value.trim() || nextBatchNo.value)
}

const billMonth = new Date().toISOString().slice(0, 7)
const billAmounts = reactive<Record<string, number>>({})
watch(
  () => props.recon.rows,
  (rows) => {
    for (const row of rows) {
      if (billAmounts[row.item_id] === undefined) billAmounts[row.item_id] = row.est_save_month
    }
  },
  { immediate: true },
)
function amountFor(row: ReconRow): number {
  return billAmounts[row.item_id] ?? row.est_save_month
}

const canAct = computed(() => props.canExecute && !props.busy && props.plan.status !== 'settled')
const diffClass = (value: number | null) => (value === null ? '' : value < 0 ? 'neg' : value > 0 ? 'pos' : '')
const MISSING_LABELS: Record<string, string> = { receipt: '缺回执', bill: '缺账单', retry: '待重试' }
</script>

<template>
  <section class="recon">
    <header class="head">
      <div class="title-block">
        <p class="label">执行与对账 · RECONCILIATION</p>
        <h2 class="title">
          逐表回执对账
          <span class="status mono" :class="`st-${recon.status}`">{{ PLAN_STATUS_LABELS[recon.status] }}</span>
        </h2>
        <p class="sub mono">
          结算口径：失败表不计节省 · 同一回执 / 整批重跑不重复计费 · 已结算不回退 · 生成于
          {{ shortTime(recon.generated_at) }}
        </p>
      </div>
      <div class="actions">
        <button class="btn btn-sm" type="button" :disabled="busy" @click="emit('refresh')">刷新对账</button>
      </div>
    </header>

    <div class="batchbar">
      <div class="batch-start">
        <input
          v-model="batchNo"
          class="input mono"
          type="text"
          :placeholder="`批次号（默认 ${nextBatchNo}）`"
          :disabled="!canAct"
        />
        <button class="btn btn-primary btn-sm" type="button" :disabled="!canAct" @click="fireBatch">
          启动执行批次
        </button>
        <span class="hint mono">同一批次号重跑幂等：不重复置位、不重复计费</span>
      </div>
      <ul v-if="recon.batches.length" class="batches mono">
        <li v-for="batch in recon.batches" :key="batch.id">
          <span class="b-no">{{ batch.batch_no }}</span>
          <span class="b-meta">{{ batch.receipt_count }} 条回执 · {{ batch.created_by }} · {{ shortTime(batch.created_at) }}</span>
        </li>
      </ul>
    </div>

    <div class="totals">
      <div class="cell">
        <span class="label">预估月省</span>
        <strong class="mono">¥{{ money(totals.est_save_month) }}</strong>
      </div>
      <div class="cell">
        <span class="label">实际月省（已知）</span>
        <strong class="mono">¥{{ money(totals.actual_save_month) }}</strong>
      </div>
      <div class="cell">
        <span class="label">月省差异</span>
        <strong class="mono" :class="diffClass(totals.save_diff)">{{ totals.save_diff >= 0 ? '+' : '' }}¥{{ money(totals.save_diff) }}</strong>
      </div>
      <div class="cell">
        <span class="label">预估迁移成本</span>
        <strong class="mono">¥{{ money(totals.est_migrate_cost) }}</strong>
      </div>
      <div class="cell">
        <span class="label">实际迁移成本</span>
        <strong class="mono">¥{{ money(totals.actual_migrate_cost) }}</strong>
      </div>
      <div class="cell emph">
        <span class="label">结算净年省</span>
        <strong class="mono">¥{{ money(totals.settled_net_save_year) }}</strong>
      </div>
      <div class="cell emph">
        <span class="label">净年省差异</span>
        <strong class="mono" :class="diffClass(totals.net_diff)">{{ totals.net_diff >= 0 ? '+' : '' }}¥{{ money(totals.net_diff) }}</strong>
      </div>
      <div class="cell">
        <span class="label">结算进度</span>
        <strong class="mono">{{ progress }}</strong>
      </div>
    </div>

    <p v-if="recon.missing.no_receipt.length" class="banner warn mono">
      ▲ 未回执 {{ recon.missing.no_receipt.length }} 张：{{ recon.missing.no_receipt.join('、') }}
    </p>
    <p v-if="recon.missing.no_bill.length" class="banner warn mono">
      ▲ 待账单 {{ recon.missing.no_bill.length }} 张：{{ recon.missing.no_bill.join('、') }}
    </p>
    <p v-if="recon.missing.failed.length" class="banner block mono">
      ■ 失败 {{ recon.missing.failed.length }} 张（不计节省，重试成功后再结算）：{{ recon.missing.failed.join('、') }}
    </p>
    <p v-if="recon.status === 'settled'" class="banner ok mono">○ 全部表已结算，预估与实际按表对齐</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="w-i">#</th>
            <th>库表</th>
            <th>状态</th>
            <th class="num">预估月省</th>
            <th class="num">实际月省</th>
            <th class="num">差异</th>
            <th class="num">预估迁移成本</th>
            <th class="num">实际迁移成本</th>
            <th class="num">结算净年省</th>
            <th>回执 / 账单</th>
            <th class="w-act"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in recon.rows" :key="row.item_id" :class="`row-${row.status}`">
            <td class="mono idx">{{ String(index + 1).padStart(2, '0') }}</td>
            <td class="mono name">
              {{ row.table_name }}
              <span v-if="row.message" class="msg mono">{{ row.message }}</span>
            </td>
            <td>
              <span class="chip mono" :class="`chip-${row.status}`">{{ PLAN_ITEM_STATUS_LABELS[row.status] }}</span>
              <span v-for="flag in row.missing" :key="flag" class="miss mono">{{ MISSING_LABELS[flag] ?? flag }}</span>
            </td>
            <td class="num mono">¥{{ money(row.est_save_month) }}</td>
            <td class="num mono">{{ row.actual_save_month === null ? '—' : `¥${money(row.actual_save_month)}` }}</td>
            <td class="num mono" :class="diffClass(row.save_diff)">
              {{ row.save_diff === null ? '—' : `${row.save_diff >= 0 ? '+' : ''}¥${money(row.save_diff)}` }}
            </td>
            <td class="num mono">¥{{ money(row.est_migrate_cost) }}</td>
            <td class="num mono">{{ row.actual_migrate_cost === null ? '—' : `¥${money(row.actual_migrate_cost)}` }}</td>
            <td class="num mono">{{ row.settled_net_save_year === null ? '—' : `¥${money(row.settled_net_save_year)}` }}</td>
            <td class="mono refcell">
              <span v-if="row.receipt_no">{{ row.receipt_no }}</span>
              <span v-if="row.bill_no">{{ row.bill_no }}</span>
              <span v-if="!row.receipt_no && !row.bill_no" class="none-inline">—</span>
            </td>
            <td class="w-act ops">
              <template v-if="canExecute">
                <template v-if="row.status === 'executing' || row.status === 'failed'">
                  <button class="btn btn-primary btn-xs" type="button" :disabled="!canAct" @click="emit('receipt', row.item_id, index, 'success', false)">
                    成功回执
                  </button>
                  <button v-if="row.status === 'executing'" class="btn btn-danger btn-xs" type="button" :disabled="!canAct" @click="emit('receipt', row.item_id, index, 'failed', false)">
                    失败回执
                  </button>
                </template>
                <span v-if="row.status === 'executing' || row.status === 'reconciling'" class="billbox">
                  <input
                    class="input mono bill-input"
                    type="number"
                    min="0"
                    :value="amountFor(row)"
                    :disabled="!canAct"
                    @input="billAmounts[row.item_id] = Number(($event.target as HTMLInputElement).value)"
                  />
                  <button class="btn btn-xs" type="button" :disabled="!canAct" @click="emit('bill', row.item_id, index, amountFor(row), billMonth)">
                    录账单
                  </button>
                </span>
                <button
                  v-if="row.receipt_no"
                  class="btn btn-ghost btn-xs"
                  type="button"
                  :disabled="!canAct"
                  title="用同一回执号重发，验证幂等不重复计费"
                  @click="emit('receipt', row.item_id, index, row.result === 'failed' ? 'failed' : 'success', true)"
                >
                  重发回执
                </button>
              </template>
              <span v-if="row.status === 'settled'" class="mono done">✓ 已结算</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!recon.rows.length" class="none mono">计划提交后，这里按表展示预估 / 实际 / 差异与缺失项。</p>
    </div>
  </section>
</template>

<style scoped>
.recon {
  border: 1px solid var(--line);
  background: var(--frost-1);
  margin-bottom: 14px;
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
  flex-wrap: wrap;
}
.label {
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--slate-faint);
  text-transform: uppercase;
}
.title {
  font-size: var(--step-2);
  font-weight: 700;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.status {
  font-size: 10.5px;
  padding: 1px 7px;
  border: 1px solid currentColor;
  letter-spacing: 0.06em;
}
.st-executing { color: var(--warm); }
.st-reconciling { color: var(--wood-deep); }
.st-settled { color: var(--ok); }
.st-submitted { color: var(--ok); }
.sub {
  font-size: 10.5px;
  color: var(--slate-faint);
  margin-top: 2px;
}
.actions {
  display: flex;
  gap: 6px;
  align-items: flex-start;
}
.batchbar {
  padding: 10px 14px;
  border-bottom: var(--hair);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.batch-start {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.input {
  border: 1px solid var(--line-strong);
  background: var(--frost-0);
  padding: 5px 8px;
  font-size: 11px;
  min-width: 240px;
  color: var(--slate);
}
.hint {
  font-size: 10px;
  color: var(--slate-faint);
}
.batches {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.batches li {
  display: flex;
  gap: 10px;
  font-size: 10.5px;
}
.b-no {
  color: var(--wood-deep);
  font-weight: 600;
}
.b-meta {
  color: var(--slate-faint);
}
.totals {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  border-bottom: var(--hair);
}
.cell {
  padding: 9px 12px;
  border-right: var(--hair);
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.cell:last-child { border-right: 0; }
.cell .label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cell strong {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.cell.emph { background: var(--frost-0); }
.cell.emph strong { color: var(--wood-deep); }
.neg { color: var(--block); }
.pos { color: var(--ok); }
.banner {
  margin: 0;
  padding: 8px 14px;
  font-size: 10.8px;
  border-bottom: var(--hair);
  line-height: 1.5;
}
.banner.block { background: var(--hot-wash); color: var(--block); }
.banner.warn { background: var(--warm-wash); color: var(--warm); }
.banner.ok { background: var(--ok-wash); color: var(--ok); }
.table-wrap { overflow-x: auto; }
table { min-width: 1080px; }
thead th {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--slate-faint);
  text-align: left;
  padding: 7px 9px;
  border-bottom: var(--hair);
  font-weight: 500;
  white-space: nowrap;
}
tbody td {
  padding: 6px 9px;
  border-bottom: var(--hair);
  font-size: 12px;
  vertical-align: top;
}
tr.row-failed { background: var(--hot-wash); }
tr.row-settled { background: var(--ok-wash); }
.idx { color: var(--slate-faint); font-size: 10.5px; }
.name { min-width: 200px; }
.msg {
  display: block;
  font-size: 9.5px;
  color: var(--slate-faint);
  margin-top: 1px;
}
.chip {
  font-size: 10px;
  padding: 1px 6px;
  border: 1px solid currentColor;
  white-space: nowrap;
}
.chip-executing { color: var(--warm); }
.chip-reconciling { color: var(--wood-deep); }
.chip-settled { color: var(--ok); }
.chip-failed { color: var(--block); }
.chip-submitted, .chip-pending { color: var(--slate-faint); }
.miss {
  font-size: 9px;
  color: var(--warn);
  margin-left: 4px;
}
.num { text-align: right; font-size: 11.5px; white-space: nowrap; }
.refcell {
  min-width: 180px;
  font-size: 9.8px;
  color: var(--slate-soft);
}
.refcell span { display: block; }
.none-inline { color: var(--slate-faint); }
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  min-width: 220px;
}
.billbox {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}
.bill-input {
  min-width: 0;
  width: 84px;
  padding: 3px 6px;
  font-size: 10.5px;
}
.btn-xs {
  font-size: 10px;
  padding: 3px 8px;
}
.done { font-size: 10px; color: var(--ok); }
.none {
  padding: 16px;
  font-size: 11.5px;
  color: var(--slate-faint);
}
.w-i { width: 34px; }
.w-act { width: 240px; }
@media (max-width: 1200px) {
  .totals { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .totals { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
