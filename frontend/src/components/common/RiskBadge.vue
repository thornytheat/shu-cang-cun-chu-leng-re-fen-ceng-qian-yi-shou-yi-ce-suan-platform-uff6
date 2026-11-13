<script setup lang="ts">
import { computed } from 'vue'
import type { RiskLevel } from '../../types/domain'
import { RISK_LABELS } from '../../constants/enums'

const props = withDefaults(defineProps<{ risk: RiskLevel; reason?: string }>(), { reason: '' })

const label = computed(() => RISK_LABELS[props.risk] ?? props.risk)
const mark = computed(() => (props.risk === 'block' ? '■' : props.risk === 'warn' ? '▲' : '○'))
</script>

<template>
  <span class="risk" :class="`risk-${risk}`" :title="reason || label">
    <span class="mark mono">{{ mark }}</span>
    <span>{{ label }}</span>
  </span>
</template>

<style scoped>
.risk {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.mark {
  font-size: 9px;
  transform: translateY(-0.5px);
}
.risk-ok {
  color: var(--ok);
}
.risk-warn {
  color: var(--warn);
}
.risk-block {
  color: var(--block);
  font-weight: 500;
}
</style>
