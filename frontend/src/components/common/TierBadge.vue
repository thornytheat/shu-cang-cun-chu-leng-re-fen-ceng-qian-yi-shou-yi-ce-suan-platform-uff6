<script setup lang="ts">
import { computed } from 'vue'
import type { StorageTier } from '../../types/domain'
import { TIER_CODES, TIER_LABELS } from '../../constants/enums'

const props = withDefaults(
  defineProps<{ tier: StorageTier; muted?: boolean; code?: boolean }>(),
  { muted: false, code: true },
)

const label = computed(() => TIER_LABELS[props.tier] ?? props.tier)
const code = computed(() => TIER_CODES[props.tier] ?? '?')
</script>

<template>
  <span class="tier" :class="[`tier-${tier}`, { muted }]" :title="`当前温区：${label}`">
    <span v-if="code" class="tier-code mono">{{ code }}</span>
    <span class="tier-label">{{ label }}</span>
  </span>
</template>

<style scoped>
.tier {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 1px 7px 1px 1px;
  border: 1px solid currentColor;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.7;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.tier-code {
  padding: 0 5px;
  background: currentColor;
  color: var(--frost-0);
  font-weight: 700;
}
.tier-label {
  color: var(--slate);
  font-family: var(--font-sans);
  font-size: 11.5px;
  padding-right: 5px;
}
.tier-hot {
  color: var(--hot);
  background: var(--hot-wash);
}
.tier-warm {
  color: var(--warm);
  background: var(--warm-wash);
}
.tier-cold {
  color: var(--cold);
  background: var(--cold-wash);
}
.muted {
  opacity: 0.72;
}
</style>
