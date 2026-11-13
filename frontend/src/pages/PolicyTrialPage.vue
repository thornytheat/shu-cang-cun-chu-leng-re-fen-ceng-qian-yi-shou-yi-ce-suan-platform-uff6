<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { usePolicyStore } from '../stores/policyStore'
import { usePlanStore } from '../stores/planStore'
import { TIER_HINT, TIER_LABELS } from '../constants/enums'
import { EMPTY_HINTS } from '../constants/messages'
import { money, months } from '../utils/format'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import MetricTile from '../components/common/MetricTile.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import TierThermometer from '../components/domain/TierThermometer.vue'
import PolicyEditor from '../components/domain/PolicyEditor.vue'
import TrialBoard from '../components/domain/TrialBoard.vue'

const auth = useAuthStore()
const policy = usePolicyStore()
const plans = usePlanStore()
const router = useRouter()

const localError = ref('')
const creating = ref(false)

const canTrial = computed(() => auth.can('trial:run'))
const canWritePolicy = computed(() => auth.can('policies:write'))
const canPlan = computed(() => auth.can('plans:write'))

const priceRows = computed(() => policy.policy?.tiers ?? [])

async function load() {
  await policy.load()
}

async function runTrial() {
  localError.value = ''
  await policy.trialRun(Number(policy.threshold))
}

async function createPlanFromSelection() {
  localError.value = ''
  if (!policy.selected.length) {
    localError.value = '先勾选至少一张表'
    return
  }
  creating.value = true
  const title = `2026-Q4 降冷计划（试算 ${policy.threshold} 分 · ${policy.selected.length} 张）`
  const plan = await plans.create(title, policy.threshold, policy.selected)
  creating.value = false
  if (plan) {
    await router.push('/plans')
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <PageHeader
      eyebrow="B-01 / POLICY & WHAT-IF"
      title="策略与试算"
      code="TIER POLICY · VERSIONED"
      desc="左栏是本季生效的三档单价与冷区前置条件；右栏用阈值粗筛候选表，逐表给出月省、回收期与风险闸门结论。计算全部在后端完成。"
    >
      <template #actions>
        <button class="btn btn-sm" type="button" :disabled="policy.loading" @click="load">刷新策略</button>
        <button
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="!canTrial || policy.trialLoading"
          :title="canTrial ? '' : '当前角色无 trial:run 权限'"
          @click="runTrial"
        >
          {{ policy.trialLoading ? '试算中…' : `按阈值 ${policy.threshold} 试算` }}
        </button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="policy.error" :message="policy.error" @retry="load" />
    <p v-if="policy.notice" class="notice mono">{{ policy.notice }}</p>
    <p v-if="localError" class="notice notice-bad mono">{{ localError }}</p>

    <div class="top-row">
      <section class="panel threshold-panel">
        <div class="rail-wood" aria-hidden="true"></div>
        <div class="panel-head">
          <div>
            <p class="label">试算阈值</p>
            <h2 class="panel-title">热度分 &lt; 阈值 → 降冷候选</h2>
          </div>
          <span class="mono big-threshold">{{ policy.threshold }}</span>
        </div>
        <div class="slider-box">
          <input
            v-model.number="policy.threshold"
            type="range"
            min="0"
            max="60"
            step="1"
            aria-label="试算阈值"
            @change="runTrial"
          />
          <div class="scale mono">
            <span v-for="tick in [0, 20, 40, 60]" :key="tick">{{ tick }}</span>
          </div>
        </div>
        <div class="thermo-box">
          <TierThermometer
            :score="policy.trial?.hits[0]?.hot_score ?? 0"
            :threshold="policy.threshold"
            :height="168"
            label="候选中最高热度"
          />
          <div class="thermo-side">
            <div v-for="tier in priceRows" :key="tier.tier" class="price-row">
              <span class="mono p-tier">{{ TIER_LABELS[tier.tier] }}</span>
              <span class="mono p-price">¥{{ tier.unit_price.toFixed(2) }}<span class="unit">/GB·月</span></span>
              <span class="mono p-hint" :title="TIER_HINT[tier.tier]">{{ TIER_HINT[tier.tier] }}</span>
            </div>
            <p class="mono tiny">
              热度口径：90 天指数衰减（半衰期 {{ policy.policy?.heat_half_life_days ?? 14 }} 天）+
              报表引用 +8/条（上限 20）
            </p>
          </div>
        </div>
      </section>

      <section class="panel summary-panel">
        <div class="panel-head">
          <div>
            <p class="label">试算汇总</p>
            <h2 class="panel-title">把候选表迁到冷区的一年账</h2>
          </div>
          <span v-if="policy.trial" class="mono small">
            POLICY v{{ policy.trial.policy_version }} · 评估 {{ policy.trial.evaluated_count }} 张
          </span>
        </div>
        <div v-if="policy.trial" class="kpis">
          <MetricTile
            label="命中"
            :value="String(policy.trial.hit_count)"
            unit="张"
            :hint="`阈值 ${policy.trial.threshold}`"
            tone="cold"
          />
          <MetricTile
            label="候选总体积"
            :value="money(policy.trial.size_total_gb)"
            unit="GB"
            :hint="`${(policy.trial.size_total_gb / 1024).toFixed(2)} TB`"
          />
          <MetricTile
            label="预估月省"
            :value="`¥${money(policy.trial.save_month)}`"
            :hint="`年省 ¥${money(policy.trial.save_year)}`"
            tone="wood"
          />
          <MetricTile
            label="迁移成本合计"
            :value="`¥${money(policy.trial.migration_cost)}`"
            :hint="`回收期 ${months(policy.trial.avg_payback)}`"
          />
          <MetricTile
            label="首年净省"
            :value="`¥${money(policy.trial.net_save_year)}`"
            :hint="`阻断 ${policy.trial.risk_block_count} · 需确认 ${policy.trial.risk_warn_count}`"
            tone="warm"
          />
        </div>
        <div v-else class="summary-empty">
          <p class="mono tiny">
            还没有试算结果：把阈值定下来（默认取温区下限 20），点右上角「试算」即可得到命中数、月省/年省、
            迁移成本与整体回收期。
          </p>
        </div>
      </section>
    </div>

    <TrialBoard
      v-if="policy.trial"
      :trial="policy.trial"
      :selected="policy.selected"
      :busy="creating || !canPlan"
      @toggle="policy.toggle"
      @top="policy.selectTop"
      @create="createPlanFromSelection"
    />
    <EmptyState v-else title="还没有试算结果" :hint="EMPTY_HINTS.trial" code="IDLE / TRIAL">
      <button class="btn btn-primary btn-sm" type="button" :disabled="!canTrial" @click="runTrial">
        立即试算
      </button>
    </EmptyState>

    <p v-if="!canPlan" class="hint-bar mono">
      当前角色（{{ auth.user?.role }}）无 <code>plans:write</code> 权限：可以试算与看收益，但建计划/提交会返回 403。
    </p>

    <div v-if="canWritePolicy && policy.policy" class="panel editor-wrap">
      <PolicyEditor :policy="policy.policy" :saving="policy.saving" @save="policy.save" />
    </div>
    <div v-else-if="policy.policy" class="panel read-only">
      <p class="label">策略只读</p>
      <p class="ro-note">
        当前角色（{{ auth.user?.role }}）没有 <code class="mono">policies:write</code> 权限，只能查看单价与条件；
        保存会由后端返回 403。需要调参请用 admin 账号。
      </p>
      <dl class="ro-grid">
        <div v-for="tier in priceRows" :key="tier.tier">
          <dt>{{ TIER_LABELS[tier.tier] }} · {{ tier.code }} v{{ tier.version }}</dt>
          <dd class="mono">
            ¥{{ tier.unit_price.toFixed(2) }}/GB·月 · 下限 {{ tier.score_min }} · {{ tier.target_region }}
          </dd>
        </div>
      </dl>
    </div>
  </AppShell>
</template>

<style scoped>
.notice {
  margin-bottom: 12px;
  padding: 7px 10px;
  background: var(--ok-wash);
  border: 1px solid var(--ok);
  color: var(--ok);
  font-size: 10.8px;
}
.notice-bad {
  background: var(--hot-wash);
  border-color: var(--block);
  color: var(--block);
}
.top-row {
  display: grid;
  grid-template-columns: minmax(320px, 0.78fr) minmax(0, 1.22fr);
  gap: 14px;
  align-items: start;
  margin-bottom: 14px;
}
.trial,
.editor-wrap,
.read-only,
.hint-bar {
  margin-bottom: 14px;
}
.editor-wrap {
  border: 0;
}
.summary-panel {
  display: flex;
  flex-direction: column;
}
.summary-empty {
  padding: 14px;
  display: flex;
  align-items: center;
}
.panel {
  border: 1px solid var(--line);
  background: var(--frost-1);
}
.summary-panel .kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(126px, 1fr));
  align-content: stretch;
  flex: 1;
}
.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
  flex-wrap: wrap;
}
.panel-title {
  font-size: var(--step-1);
  font-weight: 700;
  margin-top: 2px;
}
.small {
  font-size: 10px;
  color: var(--slate-faint);
}
.big-threshold {
  font-size: 26px;
  font-weight: 700;
  color: var(--wood-deep);
  letter-spacing: -0.02em;
}
.slider-box {
  padding: 12px 14px 4px;
}
.scale {
  display: flex;
  justify-content: space-between;
  font-size: 9.5px;
  color: var(--slate-faint);
  padding: 2px 2px 0;
}
.thermo-box {
  display: flex;
  gap: 18px;
  padding: 10px 14px 14px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.thermo-side {
  flex: 1;
  min-width: 160px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.price-row {
  display: grid;
  grid-template-columns: 36px auto;
  gap: 1px 8px;
  align-items: baseline;
  border-bottom: var(--hair);
  padding-bottom: 4px;
}
.p-tier {
  font-size: 11px;
  color: var(--slate);
}
.p-price {
  font-size: 12px;
  font-weight: 700;
  color: var(--wood-deep);
}
.p-price .unit {
  font-size: 9px;
  font-weight: 400;
  color: var(--slate-faint);
  margin-left: 1px;
}
.p-hint {
  grid-column: 1 / -1;
  font-size: 9.8px;
  color: var(--slate-faint);
  line-height: 1.4;
}
.tiny {
  font-size: 10px;
  color: var(--slate-faint);
  line-height: 1.5;
  margin-top: 4px;
}
.read-only {
  padding: 12px 14px 14px;
}
.ro-note {
  font-size: 11.5px;
  color: var(--slate-soft);
  line-height: 1.6;
  margin-top: 6px;
}
.ro-grid {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 10px;
}
.ro-grid > div {
  border-bottom: var(--hair);
  padding-bottom: 4px;
}
.ro-grid dt {
  font-size: 11px;
  color: var(--slate);
}
.ro-grid dd {
  font-size: 10.5px;
  color: var(--slate-faint);
}
.hint-bar {
  padding: 8px 10px;
  border: 1px dashed var(--line-strong);
  font-size: 10.5px;
  color: var(--slate-soft);
}
.hint-bar code {
  background: var(--frost-2);
  padding: 0 4px;
}
@media (max-width: 1100px) {
  .top-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
