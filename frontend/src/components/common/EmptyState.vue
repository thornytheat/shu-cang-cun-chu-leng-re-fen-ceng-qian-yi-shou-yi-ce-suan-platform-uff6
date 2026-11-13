<script setup lang="ts">
defineProps<{ title: string; hint?: string; code?: string }>()
</script>

<template>
  <div class="empty">
    <div class="glyph mono" aria-hidden="true">
      <span class="shelf"></span>
      <span class="shelf"></span>
      <span class="shelf"></span>
    </div>
    <div>
      <p class="title">{{ title }}</p>
      <p v-if="hint" class="hint">{{ hint }}</p>
      <p v-if="code" class="code mono">{{ code }}</p>
    </div>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 26px 22px;
  border: 1px dashed var(--line-strong);
  background: var(--frost-1);
  color: var(--slate-soft);
}
.glyph {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-top: 4px;
}
.shelf {
  display: block;
  width: 34px;
  height: 3px;
  background: var(--wood-pale);
}
.shelf:nth-child(2) {
  width: 26px;
}
.shelf:nth-child(3) {
  width: 30px;
}
.title {
  font-weight: 500;
  color: var(--slate);
}
.hint {
  font-size: 12.5px;
  margin-top: 3px;
}
.code {
  font-size: 10.5px;
  color: var(--slate-faint);
  margin-top: 6px;
  letter-spacing: 0.12em;
}
</style>
