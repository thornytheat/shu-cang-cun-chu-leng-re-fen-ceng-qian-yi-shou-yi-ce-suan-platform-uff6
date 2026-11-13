<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; desc?: string; code?: string }>()
</script>

<template>
  <header class="page-head">
    <div class="rail-wood" aria-hidden="true"></div>
    <div class="row">
      <div class="title-block">
        <div class="meta">
          <span class="eyebrow">{{ eyebrow }}</span>
          <span v-if="code" class="tag">{{ code }}</span>
        </div>
        <h1 class="display">{{ title }}</h1>
        <p v-if="desc" class="lede">{{ desc }}</p>
      </div>
      <div class="actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.page-head {
  margin-bottom: 18px;
}
.row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding-top: 12px;
  flex-wrap: wrap;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.title-block {
  min-width: 0;
}
.lede {
  margin-top: 6px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 4px;
}
@media (max-width: 767px) {
  .row {
    gap: 10px;
  }
  .actions {
    width: 100%;
  }
}
</style>
