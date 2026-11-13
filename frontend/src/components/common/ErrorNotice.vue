<script setup lang="ts">
defineProps<{ message: string; detail?: string; traceId?: string | null }>()
const emit = defineEmits<{ (event: 'retry'): void }>()
</script>

<template>
  <div class="notice" role="alert">
    <div class="bar" aria-hidden="true"></div>
    <div class="body">
      <p class="msg">{{ message }}</p>
      <p v-if="detail" class="detail mono">{{ detail }}</p>
      <p v-if="traceId" class="trace mono">trace {{ traceId }}</p>
    </div>
    <button class="btn btn-sm" type="button" @click="emit('retry')">重试</button>
  </div>
</template>

<style scoped>
.notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--block);
  background: var(--hot-wash);
}
.bar {
  width: 3px;
  align-self: stretch;
  background: var(--block);
}
.body {
  flex: 1;
  min-width: 0;
}
.msg {
  color: var(--slate);
  font-weight: 500;
}
.detail {
  font-size: 11px;
  color: var(--slate-soft);
  margin-top: 2px;
  word-break: break-all;
}
.trace {
  font-size: 10.5px;
  color: var(--slate-faint);
  margin-top: 3px;
  letter-spacing: 0.08em;
}
</style>
