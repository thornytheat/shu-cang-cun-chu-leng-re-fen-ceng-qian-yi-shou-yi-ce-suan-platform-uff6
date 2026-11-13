<script setup lang="ts">
import { computed } from 'vue'
import type { TrialResult } from '../../types/domain'
import { RISK_LABELS, TIER_LABELS } from '../../constants/enums'
import { gb, money, months, shelfCode } from '../../utils/format'
import RiskBadge from '../common/RiskBadge.vue'

const props = defineProps<{ trial: TrialResult; selected: string[]; busy: boolean }>()
const emit = defineEmits<{
  (event: 'toggle', id: string): void
  (event: 'top', count: number): void
  (event: 'create'): void
}>()

const selectedHits = computed(() =>
  props.trial.hits.filter((hit) => props.selected.includes(hit.table_id)),
)
const selectedSize = computed(() => selectedHits.value.reduce((sum, hit) => sum + hit.size_gb, 0))
const selectedSave = computed(() => selectedHits.value.reduce((sum, hit) => sum + hit.save_month, 0))
const selectedBlock = computed(
  () => selectedHits.value.filter((hit) => hit.risk === 'block').length,
)
const canCreate = computed(() => props.selected.length > 0 && !props.busy)
</script>

<template>
  <section class="trial">
    <header class="head">
      <div>
        <p class="label">按阈值粗筛结果 · 逐表收益与闸门</p>
        <h2 class="title mono">
          命中 {{ trial.hit_count }} 张 · 月省 ¥{{ money(trial.save_month) }} · 年省 ¥{{
            money(trial.save_year)
          }}
        </h2>
      </div>
      <div class="head-actions">
        <button class="btn btn-sm" type="button" @click="emit('top', 8)">勾选前 8</button>
        <button class="btn btn-sm" type="button" @click="emit('top', trial.hit_count)">全选</button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="!canCreate" @click="emit('create')">
          以选中 {{ selected.length }} 张建计划
        </button>
      </div>
    </header>

    <p class="scopeline mono">
      候选口径：当前不在冷区 且 热度分 &lt; {{ trial.threshold }} · 评估范围 {{ trial.evaluated_count }} 张 ·
      阻断 {{ trial.risk_block_count }} / 需确认 {{ trial.risk_warn_count }}
    </p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="w-check"></th>
            <th class="w-code">货架</th>
            <th>库表</th>
            <th class="num">体积</th>
            <th class="num">热度</th>
            <th>建议温区</th>
            <th class="num">月省</th>
            <th class="num">回收期</th>
            <th class="num">净年省</th>
            <th>风险</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(hit, index) in trial.hits"
            :key="hit.table_id"
            :class="{ picked: selected.includes(hit.table_id), blocked: hit.risk === 'block' }"
          >
            <td class="w-check">
              <input
                type="checkbox"
                :checked="selected.includes(hit.table_id)"
                :aria-label="`选择 ${hit.full_name}`"
                @change="emit('toggle', hit.table_id)"
              />
            </td>
            <td class="mono code">{{ shelfCode(index + 1, hit.tier) }}</td>
            <td class="name">
              <span class="mono">{{ hit.full_name }}</span>
              <span class="meta mono">{{ TIER_LABELS[hit.tier] }} · {{ hit.partition_count }} 分区</span>
            </td>
            <td class="num mono">{{ gb(hit.size_gb) }}</td>
            <td class="num mono">{{ hit.hot_score.toFixed(1) }}</td>
            <td class="mono sugg">{{ TIER_LABELS[hit.suggested_tier] }}</td>
            <td class="num mono">¥{{ money(hit.save_month) }}</td>
            <td class="num mono">{{ months(hit.payback_months) }}</td>
            <td class="num mono">¥{{ money(hit.net_save_year) }}</td>
            <td class="risk-cell">
              <RiskBadge :risk="hit.risk" :reason="hit.reasons" />
              <span class="reason">{{ hit.reasons }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="foot mono">
      已选 {{ selected.length }} 张 · {{ gb(selectedSize) }} · 预估月省 ¥{{ money(selectedSave) }}
      <span v-if="selectedBlock" class="warn">其中 {{ selectedBlock }} 张会被风险闸门阻断</span>
      <span v-else class="ok">风险预检全部通过</span>
    </footer>
  </section>
</template>

<style scoped>
.trial {
  border: 1px solid var(--line);
  background: var(--frost-1);
}
.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
  flex-wrap: wrap;
}
.title {
  font-size: var(--step-2);
  font-weight: 700;
  margin-top: 3px;
  letter-spacing: -0.01em;
}
.head-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.scopeline {
  padding: 7px 14px;
  font-size: 10.5px;
  color: var(--slate-faint);
  border-bottom: var(--hair);
}
.table-wrap {
  overflow-x: auto;
}
table {
  min-width: 980px;
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
tbody tr.picked {
  background: var(--warm-wash);
}
tbody tr.blocked {
  background: var(--hot-wash);
}
.name .mono {
  font-size: 12px;
}
.name .meta {
  display: block;
  font-size: 10px;
  color: var(--slate-faint);
}
.code {
  font-size: 10.5px;
  color: var(--slate-faint);
}
.sugg {
  font-size: 11px;
  color: var(--slate-soft);
}
.num {
  text-align: right;
  font-size: 11.5px;
  white-space: nowrap;
}
.risk-cell {
  min-width: 200px;
}
.reason {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  line-height: 1.45;
  color: var(--slate-soft);
}
.foot {
  padding: 8px 14px;
  font-size: 10.5px;
  color: var(--slate-soft);
  border-top: var(--hair);
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.warn {
  color: var(--block);
}
.ok {
  color: var(--ok);
}
.w-check { width: 34px; }
.w-code { width: 56px; }
</style>
