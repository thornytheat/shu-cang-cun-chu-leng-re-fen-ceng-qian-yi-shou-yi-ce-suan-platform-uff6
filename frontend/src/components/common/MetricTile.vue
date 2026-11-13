<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string
    unit?: string
    hint?: string
    tone?: 'default' | 'hot' | 'warm' | 'cold' | 'wood'
    mono?: boolean
  }>(),
  { unit: '', hint: '', tone: 'default', mono: true },
)
</script>

<template>
  <div class="metric" :class="`tone-${tone}`">
    <div class="label">{{ label }}</div>
    <div class="value" :class="{ mono }">
      {{ value }}<span v-if="unit" class="unit">{{ unit }}</span>
    </div>
    <div v-if="hint" class="hint mono">{{ hint }}</div>
  </div>
</template>

<style scoped>
.metric {
  padding: 10px 14px 11px;
  border-left: 2px solid var(--line-strong);
  background: transparent;
  min-width: 0;
}
.value {
  font-size: clamp(19px, 1.65vw, 26px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
  margin-top: 2px;
}
.unit {
  font-size: 11.5px;
  font-weight: 400;
  color: var(--slate-faint);
  margin-left: 4px;
  letter-spacing: 0.02em;
}
.hint {
  font-size: 10.5px;
  color: var(--slate-faint);
  margin-top: 2px;
  letter-spacing: 0.02em;
}
.tone-hot {
  border-left-color: var(--hot);
}
.tone-warm {
  border-left-color: var(--warm);
}
.tone-cold {
  border-left-color: var(--cold);
}
.tone-wood {
  border-left-color: var(--wood);
}
</style>
