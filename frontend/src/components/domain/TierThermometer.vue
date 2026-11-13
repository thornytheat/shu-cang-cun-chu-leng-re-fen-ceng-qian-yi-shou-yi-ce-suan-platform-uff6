<script setup lang="ts">
import { computed } from 'vue'
import type { StorageTier } from '../../types/domain'

const props = withDefaults(
  defineProps<{
    score: number
    threshold?: number
    hotMin?: number
    warmMin?: number
    label?: string
    height?: number
    compact?: boolean
  }>(),
  { threshold: undefined, hotMin: 60, warmMin: 20, label: '热度', height: 168, compact: false },
)

const clamp = (value: number) => Math.max(0, Math.min(100, value))
const position = computed(() => `${100 - clamp(props.score)}%`)
const thresholdPos = computed(() =>
  props.threshold === undefined ? null : `${100 - clamp(props.threshold)}%`,
)
const hotPos = computed(() => `${100 - clamp(props.hotMin)}%`)
const warmPos = computed(() => `${100 - clamp(props.warmMin)}%`)
const ticks = computed(() => [0, 20, 40, 60, 80, 100])

const zoneOf = computed<StorageTier>(() => {
  if (props.score >= props.hotMin) return 'hot'
  if (props.score >= props.warmMin) return 'warm'
  return 'cold'
})
</script>

<template>
  <figure class="thermo" :style="{ '--h': `${height}px` }">
    <div class="scale" aria-hidden="true">
      <div class="tube">
        <div class="band band-hot" :style="{ top: '0%', height: `calc(100% - ${hotPos})` }"></div>
        <div class="band band-warm" :style="{ top: hotPos, height: `calc(${hotPos} - ${warmPos})` }"></div>
        <div class="band band-cold" :style="{ top: warmPos, height: `calc(100% - ${warmPos})` }"></div>
        <div class="mercury" :class="`m-${zoneOf}`" :style="{ height: `calc(100% - ${position})` }"></div>
        <div class="needle" :style="{ top: position }">
          <span class="needle-dot"></span>
        </div>
        <div v-if="thresholdPos" class="threshold" :style="{ top: thresholdPos }">
          <span class="threshold-line"></span>
        </div>
      </div>
      <ul class="ticks">
        <li v-for="tick in ticks" :key="tick" :style="{ top: `${100 - tick}%` }">
          <span class="tick-line"></span>
          <span class="tick-num mono">{{ tick }}</span>
        </li>
      </ul>
    </div>
    <figcaption>
      <span class="label">{{ label }}</span>
      <strong class="value mono">{{ score.toFixed(1) }}</strong>
      <span v-if="!compact" class="hint mono">
        热 ≥{{ hotMin }} · 温 ≥{{ warmMin }} · 冷 &lt;{{ warmMin }}
      </span>
      <span v-if="threshold !== undefined && !compact" class="hint mono threshold-hint">
        试算阈值线 {{ threshold }}
      </span>
    </figcaption>
  </figure>
</template>

<style scoped>
.thermo {
  margin: 0;
  display: flex;
  gap: 16px;
  align-items: stretch;
}
.scale {
  position: relative;
  height: var(--h);
  display: flex;
  gap: 6px;
}
.tube {
  position: relative;
  width: 26px;
  background: var(--frost-2);
  border: 1px solid var(--line-strong);
  overflow: hidden;
}
.band {
  position: absolute;
  left: 0;
  right: 0;
  opacity: 0.5;
}
.band-hot {
  background: var(--hot-wash);
}
.band-warm {
  background: var(--warm-wash);
}
.band-cold {
  background: var(--cold-wash);
}
.mercury {
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: 0;
  transition: height 620ms var(--ease);
}
.m-hot {
  background: var(--hot);
}
.m-warm {
  background: var(--warm);
}
.m-cold {
  background: var(--cold);
}
.needle {
  position: absolute;
  left: -4px;
  right: -4px;
  height: 0;
  border-top: 2px solid var(--slate);
  transition: top 620ms var(--ease);
}
.needle-dot {
  position: absolute;
  right: -7px;
  top: -3px;
  width: 6px;
  height: 6px;
  background: var(--slate);
}
.threshold {
  position: absolute;
  left: -6px;
  right: -6px;
  border-top: 1px dashed var(--block);
}
.ticks {
  position: relative;
  width: 30px;
}
.ticks li {
  position: absolute;
  left: 0;
  display: flex;
  align-items: center;
  gap: 3px;
  transform: translateY(-50%);
}
.tick-line {
  width: 8px;
  height: 1px;
  background: var(--line-strong);
}
.tick-num {
  font-size: 9px;
  color: var(--slate-faint);
}
figcaption {
  display: flex;
  flex-direction: column;
  gap: 3px;
  justify-content: flex-start;
  padding-top: 2px;
}
.value {
  font-size: clamp(20px, 1.8vw, 28px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.hint {
  font-size: 10.5px;
  color: var(--slate-faint);
  letter-spacing: 0.02em;
}
.threshold-hint {
  color: var(--block);
}
</style>
