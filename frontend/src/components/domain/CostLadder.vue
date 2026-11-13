<script setup lang="ts">
import { computed } from 'vue'
import type { TierBucket } from '../../types/domain'
import { TIER_HINT, TIER_LABELS } from '../../constants/enums'
import { gb, money, pct } from '../../utils/format'

const props = defineProps<{ buckets: TierBucket[] }>()

const maxSize = computed(() => Math.max(1, ...props.buckets.map((bucket) => bucket.size_gb)))
</script>

<template>
  <div class="ladder">
    <div v-for="bucket in buckets" :key="bucket.tier" class="rung" :class="`rung-${bucket.tier}`">
      <div class="head">
        <span class="zone mono">{{ bucket.tier === 'hot' ? 'H' : bucket.tier === 'warm' ? 'W' : 'C' }}</span>
        <span class="zone-name">{{ TIER_LABELS[bucket.tier] }}</span>
        <span class="price mono">¥{{ bucket.unit_price.toFixed(2) }}/GB·月</span>
      </div>
      <div class="track">
        <span class="fill" :style="{ width: `${Math.max((bucket.size_gb / maxSize) * 100, 1.5)}%` }"></span>
      </div>
      <div class="facts mono">
        <span>{{ gb(bucket.size_gb) }}</span>
        <span>{{ bucket.table_count }} 表</span>
        <span>{{ pct(bucket.share_pct) }}</span>
        <span class="cost">¥{{ money(bucket.monthly_cost) }}/月</span>
      </div>
      <p class="hint mono">{{ TIER_HINT[bucket.tier] }}</p>
    </div>
  </div>
</template>

<style scoped>
.ladder {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rung {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-left: 9px;
  border-left: 2px solid var(--line-strong);
}
.rung-hot {
  border-left-color: var(--hot);
}
.rung-warm {
  border-left-color: var(--warm);
}
.rung-cold {
  border-left-color: var(--cold);
}
.head {
  display: flex;
  align-items: baseline;
  gap: 7px;
}
.zone {
  font-size: 11px;
  font-weight: 700;
  color: var(--frost-0);
  background: var(--slate-soft);
  padding: 0 4px;
}
.rung-hot .zone {
  background: var(--hot);
}
.rung-warm .zone {
  background: var(--warm);
}
.rung-cold .zone {
  background: var(--cold);
}
.zone-name {
  font-size: 13px;
  font-weight: 500;
}
.price {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--slate-faint);
}
.track {
  height: 9px;
  background: var(--frost-2);
}
.fill {
  display: block;
  height: 100%;
  transition: width 620ms var(--ease);
}
.rung-hot .fill {
  background: var(--hot);
  opacity: 0.82;
}
.rung-warm .fill {
  background: var(--warm);
  opacity: 0.82;
}
.rung-cold .fill {
  background: var(--cold);
  opacity: 0.82;
}
.facts {
  display: flex;
  gap: 12px;
  font-size: 10.5px;
  color: var(--slate-soft);
  flex-wrap: wrap;
}
.cost {
  color: var(--slate);
  font-weight: 500;
}
.hint {
  font-size: 10px;
  color: var(--slate-faint);
  letter-spacing: 0.02em;
}
</style>
