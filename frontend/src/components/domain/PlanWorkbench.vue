<script setup lang="ts">
import { computed } from 'vue'
import type { Plan } from '../../types/domain'
import { PLAN_ITEM_STATUS_LABELS, PLAN_STATUS_LABELS } from '../../constants/enums'
import { gb, money, months, shortTime } from '../../utils/format'
import RiskBadge from '../common/RiskBadge.vue'

const props = defineProps<{ plan: Plan; busy: boolean; canEdit: boolean; canExport: boolean }>()
const emit = defineEmits<{
  (event: 'remove', itemId: string): void
  (event: 'recheck'): void
  (event: 'submit'): void
  (event: 'export'): void
}>()

const isDraft = computed(() => props.plan.status === 'draft')
const blockers = computed(() => props.plan.items.filter((item) => item.risk === 'block'))
const warns = computed(() => props.plan.items.filter((item) => item.risk === 'warn'))
</script>

<template>
  <section class="wb">
    <header class="head">
      <div class="title-block">
        <div class="meta">
          <span class="tag">{{ plan.code }}</span>
          <span class="status mono" :class="`st-${plan.status}`">{{ PLAN_STATUS_LABELS[plan.status] }}</span>
          <span class="mono small">策略 v{{ plan.policy_version }} · 阈值 {{ plan.threshold }}</span>
        </div>
        <h2 class="title">{{ plan.title }}</h2>
        <p class="sub mono">
          {{ plan.created_by }}
          <template v-if="plan.rechecked_at"> · 复检 {{ shortTime(plan.rechecked_at) }}</template>
          <template v-if="plan.submitted_at"> · 提交 {{ shortTime(plan.submitted_at) }}（{{ plan.submitted_by }}）</template>
        </p>
      </div>
      <div class="actions">
        <button class="btn btn-sm" type="button" :disabled="busy || !canEdit" @click="emit('recheck')">
          风险复检
        </button>
        <button
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="busy || !canEdit || !isDraft || blockers.length > 0 || !plan.items.length"
          :title="blockers.length ? '先移除被阻断的表' : ''"
          @click="emit('submit')"
        >
          提交计划
        </button>
        <button
          class="btn btn-sm"
          type="button"
          :disabled="busy || !canExport || !plan.items.length"
          @click="emit('export')"
        >
          导出工单 CSV
        </button>
      </div>
    </header>

    <div class="summary">
      <div class="cell">
        <span class="label">计划表数</span>
        <strong class="mono">{{ plan.item_count }}</strong>
      </div>
      <div class="cell">
        <span class="label">总体积</span>
        <strong class="mono">{{ gb(plan.total_size_gb) }}</strong>
      </div>
      <div class="cell">
        <span class="label">月省</span>
        <strong class="mono">¥{{ money(plan.save_month) }}</strong>
      </div>
      <div class="cell">
        <span class="label">年省</span>
        <strong class="mono">¥{{ money(plan.save_year) }}</strong>
      </div>
      <div class="cell">
        <span class="label">迁移成本</span>
        <strong class="mono">¥{{ money(plan.migration_cost) }}</strong>
      </div>
      <div class="cell emph">
        <span class="label">净年省（首年）</span>
        <strong class="mono">¥{{ money(plan.net_save_year) }}</strong>
      </div>
      <div class="cell emph">
        <span class="label">平均回收期</span>
        <strong class="mono">{{ months(plan.avg_payback) }}</strong>
      </div>
      <div class="cell">
        <span class="label">风险</span>
        <strong class="mono">
          <span class="blk">{{ plan.risk_block_count }} 阻断</span> ·
          <span class="wn">{{ plan.risk_warn_count }} 需确认</span>
        </strong>
      </div>
    </div>

    <p v-if="blockers.length" class="banner block mono">
      ■ {{ blockers.length }} 张被阻断：{{ blockers.map((item) => item.table_name).join('、') }} —— 冷存要求近 30
      天零访问，逐张移除后才能提交
    </p>
    <p v-else-if="warns.length" class="banner warn mono">
      ▲ {{ warns.length }} 张需报表 owner 书面确认：{{ warns.map((item) => item.table_name).join('、') }}
    </p>
    <p v-else-if="plan.items.length" class="banner ok mono">○ 风险闸门全部通过，可提交</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="w-i">#</th>
            <th>库表</th>
            <th>温区</th>
            <th class="num">体积</th>
            <th class="num">热度</th>
            <th class="num">月省</th>
            <th class="num">回收期</th>
            <th class="num">净年省</th>
            <th>风险 / 原因</th>
            <th class="w-act"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in plan.items" :key="item.id" :class="{ blocked: item.risk === 'block' }">
            <td class="mono idx">{{ String(index + 1).padStart(2, '0') }}</td>
            <td class="mono name">
              {{ item.table_name }}
              <span class="iname-cost mono">迁移成本 ¥{{ money(item.migration_cost) }}</span>
            </td>
            <td class="mono tiercell">
              {{ item.from_tier === 'hot' ? 'H' : item.from_tier === 'warm' ? 'W' : 'C' }} →
              {{ item.suggested_tier === 'hot' ? 'H' : item.suggested_tier === 'warm' ? 'W' : 'C' }}
            </td>
            <td class="num mono">{{ gb(item.size_gb) }}</td>
            <td class="num mono">{{ item.hot_score.toFixed(1) }}</td>
            <td class="num mono">¥{{ money(item.save_month) }}</td>
            <td class="num mono">{{ months(item.payback_months) }}</td>
            <td class="num mono">¥{{ money(item.net_save_year) }}</td>
            <td class="riskcell">
              <RiskBadge :risk="item.risk" :reason="item.reasons" />
              <span class="reason">{{ item.reasons }}</span>
            </td>
            <td class="w-act">
              <button
                v-if="isDraft && canEdit"
                class="btn btn-danger btn-sm"
                type="button"
                :disabled="busy"
                @click="emit('remove', item.id)"
              >
                移除
              </button>
              <span v-else class="mono item-st" :class="`ist-${item.status}`">
                {{ PLAN_ITEM_STATUS_LABELS[item.status] ?? item.status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!plan.items.length" class="none mono">
        计划里还没有表 —— 回到「策略与试算」勾选候选表后再建一次计划。
      </p>
    </div>
    <p v-if="plan.note" class="note mono">备注：{{ plan.note }}</p>
  </section>
</template>

<style scoped>
.wb {
  border: 1px solid var(--line);
  background: var(--frost-1);
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
.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.status {
  font-size: 10.5px;
  padding: 1px 7px;
  border: 1px solid currentColor;
  letter-spacing: 0.06em;
}
.st-draft {
  color: var(--warm);
}
.st-submitted {
  color: var(--ok);
}
.st-executing {
  color: var(--warm);
}
.st-reconciling {
  color: var(--wood-deep);
}
.st-settled {
  color: var(--ok);
}
.item-st {
  font-size: 10px;
  color: var(--slate-faint);
}
.ist-executing {
  color: var(--warm);
}
.ist-reconciling {
  color: var(--wood-deep);
}
.ist-settled {
  color: var(--ok);
}
.ist-failed {
  color: var(--block);
}
.small {
  font-size: 10px;
  color: var(--slate-faint);
}
.title {
  font-size: var(--step-2);
  font-weight: 700;
  margin-top: 4px;
}
.sub {
  font-size: 10.5px;
  color: var(--slate-faint);
  margin-top: 2px;
}
.actions {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.summary {
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
.cell .label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cell:last-child {
  border-right: 0;
}
.cell strong {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.cell.emph {
  background: var(--frost-0);
}
.cell.emph strong {
  color: var(--wood-deep);
}
.blk {
  color: var(--block);
}
.wn {
  color: var(--warn);
}
.banner {
  margin: 0;
  padding: 8px 14px;
  font-size: 10.8px;
  border-bottom: var(--hair);
  line-height: 1.5;
}
.banner.block {
  background: var(--hot-wash);
  color: var(--block);
}
.banner.warn {
  background: var(--warm-wash);
  color: var(--warm);
}
.banner.ok {
  background: var(--ok-wash);
  color: var(--ok);
}
.table-wrap {
  overflow-x: auto;
}
table {
  min-width: 860px;
}
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
tbody tr.blocked {
  background: var(--hot-wash);
}
.idx {
  color: var(--slate-faint);
  font-size: 10.5px;
}
.name {
  min-width: 216px;
}
.iname-cost {
  display: block;
  font-size: 9.5px;
  color: var(--slate-faint);
  margin-top: 1px;
}
.tiercell {
  font-size: 10.5px;
  color: var(--slate-soft);
  white-space: nowrap;
}
.num {
  text-align: right;
  font-size: 11.5px;
  white-space: nowrap;
}
.riskcell {
  min-width: 210px;
}
.reason {
  display: block;
  font-size: 10px;
  color: var(--slate-soft);
  margin-top: 2px;
  line-height: 1.45;
}
.none {
  padding: 16px;
  font-size: 11.5px;
  color: var(--slate-faint);
}
.note {
  padding: 7px 14px;
  font-size: 10.5px;
  color: var(--slate-faint);
  border-top: var(--hair);
}
.w-i { width: 34px; }
.w-act { width: 74px; }
@media (max-width: 1200px) {
  .summary {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 700px) {
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
