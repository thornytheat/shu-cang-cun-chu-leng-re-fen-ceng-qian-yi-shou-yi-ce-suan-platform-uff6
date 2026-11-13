<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { PolicyGroup } from '../../types/domain'
import { TIER_LABELS } from '../../constants/enums'
import type { PolicyUpdatePayload } from '../../api/policies'

const props = defineProps<{ policy: PolicyGroup; saving: boolean }>()
const emit = defineEmits<{ (event: 'save', payload: PolicyUpdatePayload): void }>()

interface Draft {
  prices: Record<string, number>
  scoreMins: Record<string, number>
  regions: Record<string, string>
  quiet_days: number
  block_recent_days: number
  min_partition: number
  migrate_price: number
  migrate_fixed: number
}

const draft = reactive<Draft>({
  prices: {},
  scoreMins: {},
  regions: {},
  quiet_days: 30,
  block_recent_days: 7,
  min_partition: 3,
  migrate_price: 0.75,
  migrate_fixed: 270,
})

function hydrate(policy: PolicyGroup | null) {
  if (!policy) return
  for (const tier of policy.tiers) {
    draft.prices[tier.tier] = tier.unit_price
    draft.scoreMins[tier.tier] = tier.score_min
    draft.regions[tier.tier] = tier.target_region
  }
  const cold = policy.tiers.find((row) => row.tier === 'cold')
  if (cold) {
    draft.quiet_days = cold.quiet_days
    draft.block_recent_days = cold.block_recent_days
    draft.min_partition = cold.min_partition
    draft.migrate_price = cold.migrate_price
    draft.migrate_fixed = cold.migrate_fixed
  }
}

watch(() => props.policy, hydrate, { immediate: true })

function submit() {
  emit('save', {
    tiers: (props.policy?.tiers ?? []).map((tier) => ({
      tier: tier.tier,
      score_min: Number(draft.scoreMins[tier.tier] ?? tier.score_min),
      unit_price: Number(draft.prices[tier.tier] ?? tier.unit_price),
      target_region: draft.regions[tier.tier] ?? tier.target_region,
    })),
    quiet_days: Number(draft.quiet_days),
    block_recent_days: Number(draft.block_recent_days),
    min_partition: Number(draft.min_partition),
    migrate_price: Number(draft.migrate_price),
    migrate_fixed: Number(draft.migrate_fixed),
    note: '策略页人工调参',
  })
}
</script>

<template>
  <section class="editor">
    <header class="head">
      <span class="tag">POLICY v{{ policy.version }}</span>
      <h2 class="title">分档条件与单价</h2>
      <button class="btn btn-primary btn-sm" type="button" :disabled="saving" @click="submit">
        {{ saving ? '升版中…' : '保存并升版' }}
      </button>
    </header>

    <div class="grid">
      <div v-for="tier in policy.tiers" :key="tier.tier" class="tier-block">
        <p class="tier-name">
          {{ TIER_LABELS[tier.tier] }}
          <span class="mono">{{ tier.code }}</span>
        </p>
        <label class="field">
          <span>单价 ¥/GB·月</span>
          <input v-model.number="draft.prices[tier.tier]" class="input" type="number" step="0.01" min="0" />
        </label>
        <label class="field">
          <span>下限热度</span>
          <input
            v-model.number="draft.scoreMins[tier.tier]"
            class="input"
            type="number"
            step="1"
            min="0"
            max="100"
          />
        </label>
        <label class="field">
          <span>目标存储池</span>
          <input v-model="draft.regions[tier.tier]" class="input" type="text" />
        </label>
      </div>
    </div>

    <div class="rules">
      <p class="rules-title">冷区前置条件（风险闸门）</p>
      <label class="field">
        <span>静默天数（近 N 天零访问）</span>
        <input v-model.number="draft.quiet_days" class="input" type="number" min="1" max="365" />
      </label>
      <label class="field">
        <span>阻断窗口（近 N 天有访问即阻断）</span>
        <input v-model.number="draft.block_recent_days" class="input" type="number" min="1" max="90" />
      </label>
      <label class="field">
        <span>最少分区数</span>
        <input v-model.number="draft.min_partition" class="input" type="number" min="1" max="365" />
      </label>
      <label class="field">
        <span>迁移单价 ¥/GB</span>
        <input v-model.number="draft.migrate_price" class="input" type="number" min="0" step="0.05" />
      </label>
      <label class="field">
        <span>每表工单成本 ¥</span>
        <input v-model.number="draft.migrate_fixed" class="input" type="number" min="0" step="10" />
      </label>
    </div>
    <p class="foot mono">
      保存会生成 v{{ policy.version + 1 }} 新版本，旧版本行归档保留（可追溯季度口径变化）。
    </p>
  </section>
</template>

<style scoped>
.editor {
  border: 1px solid var(--line);
  background: var(--frost-1);
  padding: 0 0 12px;
}
.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line-strong);
  background: var(--frost-2);
}
.head .btn {
  margin-left: auto;
}
.title {
  font-size: var(--step-1);
  font-weight: 500;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  border-bottom: var(--hair);
}
.tier-block {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-right: var(--hair);
}
.tier-block:last-child {
  border-right: 0;
}
.tier-name {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-weight: 500;
}
.tier-name .mono {
  font-size: 10px;
  color: var(--slate-faint);
  letter-spacing: 0.06em;
}
.rules {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px 14px;
  padding: 12px 14px;
}
.rules-title {
  grid-column: 1 / -1;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--slate-faint);
}
.foot {
  padding: 0 14px;
  font-size: 10.5px;
  color: var(--slate-faint);
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .tier-block {
    border-right: 0;
    border-bottom: var(--hair);
  }
}
</style>
