<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchOverview } from '../api/overview'
import { recomputeHeat } from '../api/tables'
import { useAuthStore } from '../stores/authStore'
import { useTableStore } from '../stores/tableStore'
import { useTableFilter } from '../hooks/useTableFilter'
import type { Overview } from '../types/domain'
import { LAYER_LABELS, TIER_LABELS } from '../constants/enums'
import { EMPTY_HINTS } from '../constants/messages'
import { gb, money, pct, shortTime } from '../utils/format'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricTile from '../components/common/MetricTile.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import TierThermometer from '../components/domain/TierThermometer.vue'
import CostLadder from '../components/domain/CostLadder.vue'
import TreemapBoard from '../components/domain/TreemapBoard.vue'
import ShelfTable from '../components/domain/ShelfTable.vue'

const auth = useAuthStore()
const tables = useTableStore()
const router = useRouter()

const overview = ref<Overview | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const recomputing = ref(false)

const { tier, layer, keyword, sort, filtered, layerOptions, tierOptions } = useTableFilter(
  () => tables.rows,
)

const candidateShare = computed(() => {
  if (!overview.value || !overview.value.table_count) return 0
  return (overview.value.candidate_count / overview.value.table_count) * 100
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    overview.value = await fetchOverview()
    await tables.load({ sort: 'size' })
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '概览加载失败'
  } finally {
    loading.value = false
  }
}

async function runRecompute() {
  recomputing.value = true
  notice.value = ''
  try {
    const result = await recomputeHeat()
    notice.value = `已投递热度重算任务 ${result.task_id.slice(0, 8)}…（${result.tables} 张表，worker 异步执行）`
  } catch (err) {
    notice.value = (err as { message?: string }).message ?? '投递失败'
  } finally {
    recomputing.value = false
  }
}

function openTable(id: string) {
  localStorage.setItem('coldtier_last_table', id)
  router.push(`/tables/${id}`)
}

onMounted(load)
</script>

<template>
  <AppShell>
    <PageHeader
      eyebrow="A-01 / STORAGE OVERVIEW"
      title="存储概览"
      code="WAREHOUSE · QINGHE RETAIL"
      desc="42 张表按当前温区摆放：木梁是货架，刻度是单价，右侧温度计标出降冷候选的热度分布。所有数字由后端按 90 天访问序列现算。"
    >
      <template #actions>
        <button class="btn btn-sm" type="button" :disabled="loading" @click="load">刷新</button>
        <button
          v-if="auth.can('tables:recompute')"
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="recomputing"
          @click="runRecompute"
        >
          {{ recomputing ? '投递中…' : '重算热度（Celery）' }}
        </button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="error" :message="error" @retry="load" />
    <p v-if="notice" class="notice mono">{{ notice }}</p>

    <template v-if="overview">
      <section class="kpis">
        <MetricTile label="表数量" :value="String(overview.table_count)" unit="张" hint="ods / dwd / dws / ads" />
        <MetricTile
          label="总体积"
          :value="overview.total_size_tb.toFixed(1)"
          unit="TB"
          :hint="`${money(overview.total_size_gb)} GB`"
          tone="cold"
        />
        <MetricTile
          label="月度存储费"
          :value="`¥${money(overview.monthly_cost)}`"
          :hint="`年化 ¥${money(overview.year_cost)}`"
          tone="wood"
        />
        <MetricTile
          label="降冷可省（月）"
          :value="`¥${money(overview.cold_saving_month)}`"
          :hint="`年省 ¥${money(overview.cold_saving_year)}`"
          tone="warm"
        />
        <MetricTile
          label="降冷候选"
          :value="String(overview.candidate_count)"
          unit="张"
          :hint="`占全仓 ${pct(candidateShare)}`"
          tone="hot"
        />
      </section>

      <div class="layout">
        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="label">温区体积与单价</p>
              <h2 class="panel-title">三档货架</h2>
            </div>
            <span class="mono small">POLICY v{{ overview.policy_version }} · 单价随策略版本</span>
          </div>
          <CostLadder :buckets="overview.tier_buckets" />
          <div class="divider"></div>
          <div class="panel-head tight">
            <div>
              <p class="label">分层 × 温区</p>
              <h2 class="panel-title">体积树图</h2>
            </div>
            <span class="mono small">squarified treemap · 自绘 SVG</span>
          </div>
          <TreemapBoard :cells="overview.layer_cells" />
        </section>

        <aside class="side">
          <section class="panel pad">
            <p class="label">候选热度分布</p>
            <div class="thermo-row">
              <TierThermometer
                :score="overview.coldest_candidate?.hot_score ?? 0"
                :height="150"
                label="最冷候选项热度"
              />
              <div class="thermo-facts">
                <div class="fact">
                  <span class="label">候选项</span>
                  <strong class="mono">{{ overview.candidate_count }} 张</strong>
                </div>
                <div class="fact">
                  <span class="label">阻断 / 需确认</span>
                  <strong class="mono">
                    <span class="blk">{{ overview.block_count }}</span> /
                    <span class="wn">{{ overview.warn_count }}</span>
                  </strong>
                </div>
                <div class="fact">
                  <span class="label">上次热度重算</span>
                  <strong class="mono small2">{{ shortTime(overview.last_heat_at) }}</strong>
                </div>
              </div>
            </div>
          </section>

          <section v-if="overview.hot_table" class="panel pad">
            <p class="label">最热表（全仓基准）</p>
            <p class="spot-name mono">{{ overview.hot_table.full_name }}</p>
            <p class="spot-facts mono">
              热度 {{ overview.hot_table.hot_score.toFixed(1) }} · {{ gb(overview.hot_table.size_gb) }} ·
              {{ TIER_LABELS[overview.hot_table.tier] }} · 引用报表 {{ overview.hot_table.report_refs }}
            </p>
            <p class="spot-note">
              它是归一化分母：其他表的热度按它的加权访问量折算成 0-100。
            </p>
          </section>

          <section v-if="overview.coldest_candidate" class="panel pad">
            <p class="label">最大降冷机会</p>
            <button class="spot-name mono linkish" type="button" @click="openTable(overview.coldest_candidate.table_id)">
              {{ overview.coldest_candidate.full_name }}
            </button>
            <p class="spot-facts mono">
              {{ gb(overview.coldest_candidate.size_gb) }} · 月省 ¥{{ money(overview.coldest_candidate.save_month) }} ·
              回收期 {{ overview.coldest_candidate.payback_months ?? '—' }} 月
            </p>
            <p class="spot-note">
              按 {{ overview.coldest_candidate.economics.price_before }} → {{ overview.coldest_candidate.economics.price_after }}
              ¥/GB·月 计算，含一次性迁移成本 ¥{{ money(overview.coldest_candidate.economics.migration_cost) }}。
            </p>
          </section>

          <section class="panel pad">
            <p class="label">最近操作台账</p>
            <ul v-if="overview.audit_tail.length" class="audit">
              <li v-for="entry in overview.audit_tail" :key="entry.id">
                <span class="mono a-time">{{ shortTime(entry.created_at) }}</span>
                <span class="mono a-action">{{ entry.action }}</span>
                <span class="mono a-mail">{{ entry.actor_email || 'system' }}</span>
              </li>
            </ul>
            <p v-else class="spot-note">还没有审计记录。登录、试算、复检、提交都会写一条。</p>
          </section>
        </aside>
      </div>

      <section class="list-block">
        <div class="panel-head list-head">
          <div>
            <p class="label">货架清单</p>
            <h2 class="panel-title">
              {{ filtered.length }} 张表
              <span class="mono small">共 {{ tables.total }} 张</span>
            </h2>
          </div>
          <div class="filters">
            <div class="chips">
              <button
                class="chip mono"
                :class="{ on: tier === 'all' }"
                type="button"
                @click="tier = 'all'"
              >
                全部 {{ tables.rows.length }}
              </button>
              <button
                v-for="option in tierOptions"
                :key="option.value"
                class="chip mono"
                :class="[{ on: tier === option.value }, `chip-${option.value}`]"
                type="button"
                @click="tier = option.value"
              >
                {{ TIER_LABELS[option.value] }} {{ option.count }}
              </button>
            </div>
            <div class="chips">
              <button class="chip mono" :class="{ on: layer === 'all' }" type="button" @click="layer = 'all'">
                全部分层
              </button>
              <button
                v-for="option in layerOptions"
                :key="option.value"
                class="chip mono"
                :class="{ on: layer === option.value }"
                type="button"
                @click="layer = option.value"
              >
                {{ LAYER_LABELS[option.value] }}
              </button>
            </div>
            <input v-model="keyword" class="input search" type="search" placeholder="搜索库表名，如 dwd.trade" />
            <select v-model="sort" class="input sort">
              <option value="size">按体积</option>
              <option value="score">按热度</option>
              <option value="save">按可省金额</option>
              <option value="name">按表名</option>
            </select>
          </div>
        </div>

        <ErrorNotice v-if="tables.error" :message="tables.error" @retry="tables.load({})" />
        <div v-else-if="tables.loading && !tables.rows.length" class="skeleton mono">正在读取 42 个货架格子…</div>
        <EmptyState
          v-else-if="!filtered.length"
          title="这个筛选组合下没有表"
          :hint="EMPTY_HINTS.tables"
          code="EMPTY / FILTER"
        >
          <button class="btn btn-sm" type="button" @click="(tier = 'all'), (layer = 'all'), (keyword = '')">
            清空筛选
          </button>
        </EmptyState>
        <ShelfTable v-else :rows="filtered" @select="openTable" />
      </section>
    </template>

    <div v-else-if="loading" class="skeleton mono">正在汇总 42 张表的体积与成本…</div>
  </AppShell>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border: 1px solid var(--line);
  background: var(--frost-1);
  margin-bottom: 16px;
}
.notice {
  margin-bottom: 12px;
  padding: 7px 10px;
  background: var(--ok-wash);
  border: 1px solid var(--ok);
  color: var(--ok);
  font-size: 10.8px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.85fr);
  gap: 14px;
  margin-bottom: 14px;
}
.panel {
  border: 1px solid var(--line);
  background: var(--frost-1);
}
.panel.pad {
  padding: 12px 14px 14px;
}
.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
  flex-wrap: wrap;
}
.panel-head.tight {
  border-top: var(--hair);
  border-bottom: 0;
  margin-top: 4px;
}
.panel-title {
  font-size: var(--step-2);
  font-weight: 700;
  margin-top: 2px;
}
.small {
  font-size: 10px;
  color: var(--slate-faint);
  letter-spacing: 0.04em;
}
.panel > .ladder-wrap {
  padding: 12px 14px 14px;
}
.divider {
  height: 8px;
}
.panel :deep(.ladder) {
  padding: 12px 14px;
}
.panel :deep(.board) {
  border: 0;
  border-top: var(--hair);
}
.side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.thermo-row {
  display: flex;
  gap: 14px;
  margin-top: 10px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.thermo-facts {
  display: flex;
  flex-direction: column;
  gap: 9px;
  min-width: 120px;
}
.fact {
  display: flex;
  flex-direction: column;
}
.fact strong {
  font-size: 15px;
  font-weight: 700;
}
.small2 {
  font-size: 11px;
  font-weight: 400;
  color: var(--slate-soft);
}
.blk {
  color: var(--block);
}
.wn {
  color: var(--warn);
}
.spot-name {
  font-size: 13px;
  font-weight: 500;
  margin-top: 5px;
  word-break: break-all;
}
.linkish {
  border: 0;
  background: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  color: var(--cold);
  font-family: var(--font-mono);
}
.linkish:hover {
  color: var(--slate);
  text-decoration: underline;
}
.spot-facts {
  font-size: 10.8px;
  color: var(--slate-soft);
  margin-top: 3px;
  line-height: 1.5;
}
.spot-note {
  font-size: 11px;
  color: var(--slate-faint);
  margin-top: 5px;
  line-height: 1.5;
}
.audit {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}
.audit li {
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 0 8px;
  font-size: 10.2px;
  color: var(--slate-soft);
  border-bottom: var(--hair);
  padding-bottom: 3px;
}
.a-time {
  color: var(--slate-faint);
}
.a-action {
  color: var(--slate);
}
.a-mail {
  grid-column: 2;
  color: var(--slate-faint);
}
.list-block {
  border: 1px solid var(--line);
  background: var(--frost-1);
}
.list-head {
  border-bottom: 0;
}
.filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.chips {
  display: flex;
  gap: 3px;
}
.chip {
  padding: 3px 8px;
  border: 1px solid var(--line);
  background: var(--frost-1);
  color: var(--slate-soft);
  font-size: 10.5px;
  cursor: pointer;
  transition: background 160ms var(--ease), color 160ms var(--ease);
}
.chip:hover {
  background: var(--frost-2);
}
.chip.on {
  background: var(--slate);
  color: var(--frost-0);
  border-color: var(--slate);
}
.chip-hot.on {
  background: var(--hot);
  border-color: var(--hot);
}
.chip-warm.on {
  background: var(--warm);
  border-color: var(--warm);
}
.chip-cold.on {
  background: var(--cold);
  border-color: var(--cold);
}
.search {
  width: 200px;
}
.sort {
  width: 128px;
}
.skeleton {
  padding: 18px;
  font-size: 11.5px;
  color: var(--slate-faint);
  border: 1px dashed var(--line-strong);
  background: var(--frost-1);
}
.list-block > .skeleton {
  border: 0;
}
@media (max-width: 1279px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .kpis {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 767px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .search,
  .sort {
    width: 100%;
  }
}
</style>
