<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchAuditLogs } from '../api/overview'
import { useAuthStore } from '../stores/authStore'
import { usePlanStore } from '../stores/planStore'
import type { AuditEntry } from '../types/domain'
import { PLAN_STATUS_LABELS } from '../constants/enums'
import { EMPTY_HINTS } from '../constants/messages'
import { money, months, shortTime } from '../utils/format'
import { saveBlob } from '../utils/download'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import PlanWorkbench from '../components/domain/PlanWorkbench.vue'

const auth = useAuthStore()
const plans = usePlanStore()
const router = useRouter()

const audit = ref<AuditEntry[]>([])
const auditError = ref('')

const canEdit = computed(() => auth.can('plans:write'))
const canExport = computed(() => auth.can('plans:export'))
const canAudit = computed(() => auth.can('audit:read'))

async function loadAll() {
  await plans.loadList()
  if (canAudit.value) await loadAudit()
}

async function loadAudit() {
  auditError.value = ''
  try {
    const result = await fetchAuditLogs(30)
    audit.value = result.items
  } catch (error) {
    auditError.value = (error as { message?: string }).message ?? '台账加载失败'
  }
}

async function handleExport() {
  const result = await plans.exportCsv()
  if (result) {
    saveBlob(result.blob, result.filename)
    if (canAudit.value) await loadAudit()
  }
}

async function handleRecheck() {
  await plans.recheck()
}

async function handleSubmit() {
  await plans.submit()
}

async function handleRemove(itemId: string) {
  await plans.remove(itemId)
}

onMounted(loadAll)
</script>

<template>
  <AppShell>
    <PageHeader
      eyebrow="C-01 / MIGRATION PLAN"
      title="迁移计划"
      code="WORK ORDER · CSV EXPORT"
      desc="左侧是季度计划台账，右侧是计划工位：风险复检 → 移除阻断项 → 提交 → 导出工单 CSV。汇总口径与试算一致（净年省 = 年省 − 一次性迁移成本）。"
    >
      <template #actions>
        <button class="btn btn-sm" type="button" :disabled="plans.loading" @click="loadAll">刷新</button>
        <button class="btn btn-primary btn-sm" type="button" @click="router.push('/policies')">
          去试算选表
        </button>
      </template>
    </PageHeader>

    <ErrorNotice v-if="plans.error" :message="plans.error" @retry="loadAll" />
    <p v-if="plans.notice" class="notice mono">{{ plans.notice }}</p>

    <section class="panel ledger">
      <div class="rail-wood" aria-hidden="true"></div>
      <div class="panel-head">
        <p class="label">计划台账</p>
        <span class="mono small">{{ plans.list.length }} 份 · 点卡片切换工位</span>
      </div>
      <div class="cards">
        <button
          v-for="plan in plans.list"
          :key="plan.id"
          class="card"
          :class="[{ on: plans.current?.id === plan.id }, `st-card-${plan.status}`]"
          type="button"
          @click="plans.open(plan.id)"
        >
          <span class="c-top">
            <span class="mono c-code">{{ plan.code }}</span>
            <span class="mono c-status" :class="`st-${plan.status}`">{{ PLAN_STATUS_LABELS[plan.status] }}</span>
          </span>
          <span class="c-title">{{ plan.title }}</span>
          <span class="mono c-facts">
            {{ plan.item_count }} 张 · 净年省 ¥{{ money(plan.net_save_year) }} · 回收期
            {{ months(plan.avg_payback) }}
          </span>
          <span class="mono c-risk">
            阻断 {{ plan.risk_block_count }} · 需确认 {{ plan.risk_warn_count }} · 阈值 {{ plan.threshold }}
          </span>
        </button>
        <EmptyState
          v-if="!plans.list.length && !plans.loading"
          class="card-empty"
          title="还没有任何迁移计划"
          :hint="EMPTY_HINTS.plans"
        >
          <button class="btn btn-sm" type="button" @click="router.push('/policies')">去试算</button>
        </EmptyState>
      </div>
    </section>

    <PlanWorkbench
      v-if="plans.current"
      :plan="plans.current"
      :busy="plans.busy"
      :can-edit="canEdit"
      :can-export="canExport"
      @remove="handleRemove"
      @recheck="handleRecheck"
      @submit="handleSubmit"
      @export="handleExport"
    />
    <EmptyState
      v-else
      title="选一份计划"
      hint="上方点任意一份计划卡片查看工位；没有计划就从「策略与试算」勾选候选表建一份。"
      code="NO PLAN SELECTED"
    />

    <section v-if="canAudit" class="panel audit-panel">
      <div class="panel-head">
        <p class="label">操作台账（审计）</p>
        <span class="mono small">admin 可见 · 最近 {{ audit.length }} 条</span>
      </div>
      <ErrorNotice v-if="auditError" :message="auditError" @retry="loadAudit" />
      <ul class="audit">
        <li v-for="entry in audit" :key="entry.id">
          <span class="mono a-time">{{ shortTime(entry.created_at) }}</span>
          <span class="mono a-action">{{ entry.action }}</span>
          <span class="mono a-mail">{{ entry.actor_email || 'system' }} · {{ entry.actor_role || '—' }}</span>
        </li>
      </ul>
      <p v-if="!audit.length" class="none mono">运行一次试算或提交后会写台账。</p>
    </section>
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
.panel {
  border: 1px solid var(--line);
  background: var(--frost-1);
  margin-bottom: 14px;
}
.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
}
.small {
  font-size: 10px;
  color: var(--slate-faint);
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(268px, 1fr));
  gap: 10px;
  padding: 12px 14px;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-top: 3px solid var(--line-strong);
  background: var(--frost-0);
  text-align: left;
  cursor: pointer;
  transition: transform 160ms var(--ease), border-color 180ms var(--ease), background 180ms var(--ease);
}
.card:hover {
  transform: translateY(-2px);
  border-color: var(--wood-pale);
}
.card.on {
  border-top-color: var(--wood);
  background: var(--frost-1);
  box-shadow: inset 0 0 0 1px var(--wood-pale);
}
.st-card-submitted {
  border-top-color: var(--ok);
}
.c-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.c-code {
  font-size: 10.5px;
  color: var(--slate-faint);
  letter-spacing: 0.04em;
}
.c-status {
  font-size: 9.5px;
  letter-spacing: 0.06em;
}
.st-draft {
  color: var(--warm);
}
.st-submitted {
  color: var(--ok);
}
.c-title {
  font-size: 12.8px;
  font-weight: 500;
  color: var(--slate);
  line-height: 1.45;
}
.c-facts,
.c-risk {
  font-size: 10px;
  color: var(--slate-soft);
}
.c-risk {
  color: var(--slate-faint);
}
.card-empty {
  grid-column: 1 / -1;
}
.audit {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 0 18px;
  padding: 6px 14px 10px;
}
.audit li {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 0 8px;
  padding: 6px 0;
  border-bottom: var(--hair);
}
.a-time {
  font-size: 9.8px;
  color: var(--slate-faint);
}
.a-action {
  font-size: 10.5px;
  color: var(--slate);
}
.a-mail {
  grid-column: 2;
  font-size: 9.5px;
  color: var(--slate-faint);
}
.none {
  padding: 12px 14px;
  font-size: 10.5px;
  color: var(--slate-faint);
}
</style>
