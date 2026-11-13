<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTableStore } from '../stores/tableStore'
import { COMPRESSION_LABELS, LAYER_LABELS, TIER_LABELS } from '../constants/enums'
import { bytes, gb, money, months, shortTime } from '../utils/format'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricTile from '../components/common/MetricTile.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import EmptyState from '../components/common/EmptyState.vue'
import TierBadge from '../components/common/TierBadge.vue'
import RiskBadge from '../components/common/RiskBadge.vue'
import TierThermometer from '../components/domain/TierThermometer.vue'
import AccessTrendChart from '../components/domain/AccessTrendChart.vue'

const route = useRoute()
const router = useRouter()
const store = useTableStore()
const halfLife = ref(14)

const detail = computed(() => store.detail)
const id = computed(() => String(route.params.id ?? ''))

async function load() {
  if (!id.value) return
  localStorage.setItem('coldtier_last_table', id.value)
  await store.loadDetail(id.value)
}

onMounted(load)
watch(id, load)

const peak = computed(() => {
  if (!detail.value) return 0
  return Math.max(1, ...detail.value.series.map((point) => point.access_count))
})

const silentDays = computed(() => {
  if (!detail.value) return 0
  let count = 0
  // series 由后端按「今天 → 90 天前」返回，直接正序数即可
  for (const point of detail.value.series) {
    if (point.access_count > 0) break
    count += 1
  }
  return count
})

const checks = computed(() => detail.value?.risk.checks ?? [])
</script>

<template>
  <AppShell>
    <PageHeader
      eyebrow="A-02 / TABLE THERMOMETER"
      title="表热度详情"
      :code="detail ? detail.profile.full_name : '—'"
      :desc="
        detail
          ? `衰减分 ${detail.heat.decay_score} + 引用加成 ${detail.heat.report_bonus} = 热度 ${detail.heat.hot_score}；建议温区 ${TIER_LABELS[detail.heat.suggested_tier]}。`
          : '从存储概览的货架清单点任意一行进来，这里给出 90 天访问序列、衰减权重与收益测算。'
      "
    >
      <template #actions>
        <button class="btn btn-sm" type="button" @click="router.push('/overview')">← 返回货架</button>
        <button class="btn btn-sm" type="button" :disabled="store.detailLoading" @click="load">刷新</button>
        <button class="btn btn-primary btn-sm" type="button" @click="router.push('/policies')">
          去策略页试算
        </button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="store.detailError" :message="store.detailError" @retry="load" />

    <div v-if="store.detailLoading && !detail" class="skeleton mono">正在按 90 天序列算这张表的热度…</div>

    <template v-if="detail">
      <section class="kpis">
        <MetricTile
          label="热度分"
          :value="detail.heat.hot_score.toFixed(1)"
          hint="0-100，越高越该留热区"
          :tone="detail.heat.hot_score >= 60 ? 'hot' : detail.heat.hot_score >= 20 ? 'warm' : 'cold'"
        />
        <MetricTile label="衰减分" :value="detail.heat.decay_score.toFixed(1)" :hint="`半衰期 ${detail.heat.half_life_days} 天`" />
        <MetricTile
          label="引用加成"
          :value="`+${detail.heat.report_bonus.toFixed(0)}`"
          :hint="`${detail.profile.report_refs} 张报表 × 8，上限 20`"
          tone="wood"
        />
        <MetricTile
          label="近 30 天访问"
          :value="String(detail.heat.recent_30_access)"
          unit="次"
          :hint="`近 7 天 ${detail.heat.recent_7_access} 次`"
          :tone="detail.heat.recent_30_access === 0 ? 'cold' : 'default'"
        />
        <MetricTile
          label="已静默"
          :value="String(silentDays)"
          unit="天"
          :hint="`窗口 ${detail.heat.window_days} 天 · 峰值 ${peak}/日`"
        />
      </section>

      <div class="layout">
        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="label">近 90 天访问序列</p>
              <h2 class="panel-title">访问趋势与衰减权重</h2>
            </div>
            <span class="mono small">加权访问 {{ detail.heat.weighted_access.toFixed(1) }} · 总访问 {{ detail.heat.total_90_access }}</span>
          </div>
          <AccessTrendChart :series="detail.series" :quiet-days="30" :half-life="halfLife" />
          <p class="explain">
            柱子是每天的真实访问次数，木色虚线是指数衰减权重（越近权重越高）；左侧冷色区域是近 30 天的静默线 ——
            冷存要求这段区间访问为 0。
          </p>
        </section>

        <aside class="side">
          <section class="panel pad">
            <p class="label">热度温度计</p>
            <div class="thermo-row">
              <TierThermometer :score="detail.heat.hot_score" :height="164" label="当前热度" />
              <div class="facts">
                <div class="fact">
                  <span class="label">当前温区</span>
                  <TierBadge :tier="detail.profile.tier" />
                </div>
                <div class="fact">
                  <span class="label">建议温区</span>
                  <TierBadge :tier="detail.heat.suggested_tier" />
                </div>
                <p class="reason">{{ detail.heat.suggested_reason }}</p>
                <p class="mono tiny">计算于 {{ shortTime(detail.heat.computed_at) }}</p>
              </div>
            </div>
          </section>

          <section class="panel pad">
            <p class="label">风险闸门</p>
            <div class="risk-head">
              <RiskBadge :risk="detail.risk.risk" :reason="detail.risk.reasons" />
              <span class="mono tiny">闸门结论 · 逐项见下</span>
            </div>
            <ul class="checks">
              <li v-for="check in checks" :key="check.name">
                <span class="mono c-name">{{ check.name }}</span>
                <span class="mono c-val">{{ check.value }}</span>
                <RiskBadge :risk="check.level" />
              </li>
            </ul>
            <p class="reason">{{ detail.risk.reasons }}</p>
          </section>

          <section class="panel pad">
            <p class="label">收益测算（迁到冷区）</p>
            <dl class="econ">
              <div>
                <dt>当前月成本</dt>
                <dd class="mono">¥{{ money(detail.profile.monthly_cost, 2) }}</dd>
              </div>
              <div>
                <dt>迁移后月成本</dt>
                <dd class="mono">¥{{ money(detail.economics.cost_after, 2) }}</dd>
              </div>
              <div class="strong">
                <dt>月省 / 年省</dt>
                <dd class="mono">¥{{ money(detail.economics.save_month, 2) }} / ¥{{ money(detail.economics.save_year) }}</dd>
              </div>
              <div>
                <dt>一次性迁移成本</dt>
                <dd class="mono">¥{{ money(detail.economics.migration_cost, 2) }}</dd>
              </div>
              <div>
                <dt>回收期</dt>
                <dd class="mono">{{ months(detail.economics.payback_months) }}</dd>
              </div>
              <div class="strong">
                <dt>首年净省</dt>
                <dd class="mono">¥{{ money(detail.economics.net_save_year) }}</dd>
              </div>
            </dl>
            <p class="mono tiny">
              单价 {{ detail.economics.price_before }} → {{ detail.economics.price_after }} ¥/GB·月；迁移
              {{ detail.economics.migration_cost ? money(detail.economics.migration_cost / detail.economics.size_gb, 2) : '0' }}
              ¥/GB + 工单固定成本
            </p>
          </section>
        </aside>
      </div>

      <div class="layout lower">
        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="label">档案</p>
              <h2 class="panel-title">表元数据</h2>
            </div>
            <span class="mono small">{{ LAYER_LABELS[detail.profile.layer] }} · {{ detail.profile.owner }}</span>
          </div>
          <dl class="meta-grid">
            <div><dt>体积</dt><dd class="mono">{{ gb(detail.profile.size_gb) }}</dd></div>
            <div><dt>行数</dt><dd class="mono">{{ money(detail.economics.row_count) }}</dd></div>
            <div><dt>分区数</dt><dd class="mono">{{ detail.profile.partition_count }}</dd></div>
            <div><dt>压缩</dt><dd class="mono">{{ COMPRESSION_LABELS[detail.profile.compression] || detail.profile.compression }}</dd></div>
            <div><dt>存储池</dt><dd class="mono">{{ detail.profile.storage_region }}</dd></div>
            <div><dt>最近写入</dt><dd class="mono">{{ shortTime(detail.profile.last_write_at) }}</dd></div>
            <div class="wide">
              <dt>报表引用</dt>
              <dd>
                <span v-if="detail.profile.report_refs" class="mono">{{ detail.profile.report_names.join('、') }}</span>
                <span v-else class="mono faint">无</span>
              </dd>
            </div>
            <div class="wide">
              <dt>扫描字节（近 90 天）</dt>
              <dd class="mono">{{ bytes(detail.series.reduce((sum, point) => sum + point.scan_bytes, 0)) }}</dd>
            </div>
          </dl>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="label">同层邻表</p>
              <h2 class="panel-title">货架邻居</h2>
            </div>
            <span class="mono small">点一行切换</span>
          </div>
          <ul class="neighbours">
            <li v-for="item in detail.neighbours" :key="item.id">
              <button type="button" @click="router.push(`/tables/${item.id}`)">
                <span class="mono n-name">{{ item.full_name }}</span>
                <TierBadge :tier="item.tier" :code="false" />
                <span class="mono n-num">{{ gb(item.size_gb) }}</span>
                <span class="mono n-score">{{ item.hot_score.toFixed(1) }}</span>
              </button>
            </li>
          </ul>
          <EmptyState
            v-if="!detail.neighbours.length"
            title="同层只有这一张表"
            hint="换一个分层（ods/dwd/dws/ads）再看。"
          />
        </section>
      </div>
    </template>

    <EmptyState
      v-else-if="!store.detailLoading && !store.detailError"
      title="还没有选表"
      hint="从存储概览的货架清单里点一行，或直接改地址栏里的表 id。"
    >
      <button class="btn btn-sm" type="button" @click="router.push('/overview')">去货架</button>
    </EmptyState>
  </AppShell>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border: 1px solid var(--line);
  background: var(--frost-1);
  margin-bottom: 14px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.9fr);
  gap: 14px;
  margin-bottom: 14px;
}
.layout.lower {
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 1fr);
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
.panel-title {
  font-size: var(--step-2);
  font-weight: 700;
  margin-top: 2px;
}
.small {
  font-size: 10px;
  color: var(--slate-faint);
}
.tiny {
  font-size: 10px;
  color: var(--slate-faint);
  display: block;
  margin-top: 6px;
  line-height: 1.5;
}
.explain {
  padding: 10px 14px 12px;
  font-size: 11.5px;
  color: var(--slate-soft);
  line-height: 1.6;
  border-top: var(--hair);
}
.side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.thermo-row {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.facts {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 150px;
  flex: 1;
}
.fact {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.reason {
  font-size: 11px;
  color: var(--slate-soft);
  line-height: 1.55;
  margin-top: 4px;
}
.risk-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.checks {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}
.checks li {
  display: grid;
  grid-template-columns: 1fr 48px 68px;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  border-bottom: var(--hair);
}
.c-name {
  font-size: 10.5px;
  color: var(--slate-soft);
}
.c-val {
  font-size: 11px;
  text-align: right;
}
.econ {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 8px;
}
.econ > div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 3px 0;
  border-bottom: var(--hair);
}
.econ dt {
  font-size: 11.5px;
  color: var(--slate-soft);
}
.econ dd {
  font-size: 12px;
}
.econ .strong dd {
  font-weight: 700;
  color: var(--wood-deep);
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
}
.meta-grid > div {
  padding: 9px 14px;
  border-bottom: var(--hair);
  border-right: var(--hair);
}
.meta-grid dt {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--slate-faint);
}
.meta-grid dd {
  font-size: 12.5px;
  margin-top: 2px;
}
.meta-grid .wide {
  grid-column: span 3;
  border-right: 0;
}
.faint {
  color: var(--slate-faint);
}
.neighbours {
  display: flex;
  flex-direction: column;
}
.neighbours button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 14px;
  border: 0;
  border-bottom: var(--hair);
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 160ms var(--ease);
}
.neighbours button:hover {
  background: var(--frost-0);
}
.n-name {
  font-size: 11.5px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.n-num {
  font-size: 10.5px;
  color: var(--slate-soft);
}
.n-score {
  font-size: 11px;
  color: var(--wood-deep);
  font-weight: 500;
}
.skeleton {
  padding: 18px;
  font-size: 11.5px;
  color: var(--slate-faint);
  border: 1px dashed var(--line-strong);
}
@media (max-width: 1279px) {
  .kpis {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .layout,
  .layout.lower {
    grid-template-columns: minmax(0, 1fr);
  }
  .meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .meta-grid .wide {
    grid-column: span 2;
  }
}
@media (max-width: 767px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .meta-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .meta-grid .wide {
    grid-column: span 1;
  }
}
</style>
