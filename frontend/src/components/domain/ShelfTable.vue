<script setup lang="ts">
import { computed } from 'vue'
import type { TableRow } from '../../types/domain'
import { COMPRESSION_LABELS, LAYER_LABELS } from '../../constants/enums'
import { gb, money, shelfCode, shortDate } from '../../utils/format'
import TierBadge from '../common/TierBadge.vue'
import RiskBadge from '../common/RiskBadge.vue'

const props = withDefaults(
  defineProps<{
    rows: TableRow[]
    showRisk?: boolean
    showSave?: boolean
    clickable?: boolean
    measure?: 'size' | 'score'
  }>(),
  { showRisk: true, showSave: true, clickable: true, measure: 'size' },
)

const emit = defineEmits<{ (event: 'select', id: string): void }>()

const maxSize = computed(() => Math.max(1, ...props.rows.map((row) => row.size_gb)))

function onRow(id: string) {
  if (props.clickable) emit('select', id)
}
</script>

<template>
  <div class="shelf">
    <table>
      <thead>
        <tr>
          <th class="w-code">货架</th>
          <th>库表</th>
          <th class="w-layer">分层</th>
          <th class="w-tier">温区</th>
          <th class="w-size num">体积</th>
          <th class="w-bar">占比</th>
          <th class="w-part num">分区</th>
          <th class="w-score num">热度</th>
          <th v-if="showSave" class="w-save num">降冷月省</th>
          <th v-if="showRisk" class="w-risk">风险</th>
          <th class="w-write num">最近写入</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="row.id"
          :class="{ clickable }"
          @click="onRow(row.id)"
        >
          <td class="code mono">{{ shelfCode(index + 1, row.tier) }}</td>
          <td class="name">
            <span class="mono">{{ row.full_name }}</span>
            <span v-if="row.report_refs" class="refs mono" :title="row.report_names.join('、')">
              报表 ×{{ row.report_refs }}
            </span>
          </td>
          <td class="layer">{{ LAYER_LABELS[row.layer] }}</td>
          <td><TierBadge :tier="row.tier" /></td>
          <td class="num mono">{{ gb(row.size_gb) }}</td>
          <td class="bar-cell">
            <span class="bar" :style="{ width: `${Math.max((row.size_gb / maxSize) * 100, 2)}%` }"></span>
          </td>
          <td class="num mono">{{ row.partition_count }}</td>
          <td class="num mono score" :class="`s-${row.suggested_tier}`">
            {{ row.hot_score.toFixed(1) }}
          </td>
          <td v-if="showSave" class="num mono save">
            {{ row.tier === 'cold' ? '—' : `¥${money(row.cold_save_month)}` }}
          </td>
          <td v-if="showRisk">
            <RiskBadge :risk="row.risk" :reason="row.risk_reason" />
          </td>
          <td class="num mono write">{{ shortDate(row.last_write_at) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="none mono">没有匹配的货架格子</p>
    <p v-else class="foot mono">
      共 {{ rows.length }} 张表 · 压缩方式 {{ COMPRESSION_LABELS[rows[0].compression] || rows[0].compression }} 起
    </p>
  </div>
</template>

<style scoped>
.shelf {
  border: 1px solid var(--line);
  background: var(--frost-1);
  overflow-x: auto;
}
table {
  min-width: 940px;
}
thead th {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--slate-faint);
  text-align: left;
  padding: 8px 8px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
  font-weight: 500;
  white-space: nowrap;
}
tbody td {
  padding: 7px 8px;
  border-bottom: var(--hair);
  font-size: 12.5px;
  vertical-align: middle;
}
tbody tr:last-child td {
  border-bottom: 0;
}
tbody tr.clickable {
  cursor: pointer;
  transition: background 160ms var(--ease);
}
tbody tr.clickable:hover {
  background: var(--frost-0);
}
.code {
  font-size: 10.5px;
  color: var(--slate-faint);
  letter-spacing: 0.06em;
  white-space: nowrap;
}
.name {
  min-width: 210px;
}
.name .mono {
  font-size: 12px;
}
.refs {
  display: inline-block;
  margin-left: 8px;
  padding: 0 5px;
  font-size: 9.5px;
  background: var(--warm-wash);
  color: var(--warm);
  border: 1px solid var(--warm-soft);
  letter-spacing: 0.02em;
}
.layer {
  color: var(--slate-soft);
  white-space: nowrap;
}
.num {
  text-align: right;
  font-size: 11.5px;
}
.bar-cell {
  width: 92px;
  padding-right: 12px;
}
.bar {
  display: block;
  height: 7px;
  background: var(--wood-pale);
  opacity: 0.75;
}
.score {
  font-weight: 500;
}
.s-hot {
  color: var(--hot);
}
.s-warm {
  color: var(--warm);
}
.s-cold {
  color: var(--cold);
}
.save {
  color: var(--ok);
}
.write {
  color: var(--slate-faint);
  font-size: 10.5px;
  white-space: nowrap;
}
.w-code { width: 58px; }
.w-layer { width: 64px; }
.w-tier { width: 86px; }
.w-size { width: 80px; }
.w-bar { width: 96px; }
.w-part { width: 52px; }
.w-score { width: 56px; }
.w-save { width: 92px; }
.w-risk { width: 76px; }
.w-write { width: 84px; }
.none {
  padding: 16px;
  color: var(--slate-faint);
  font-size: 12px;
}
.foot {
  padding: 7px 10px;
  font-size: 10px;
  color: var(--slate-faint);
  border-top: var(--hair);
  letter-spacing: 0.04em;
}
</style>
