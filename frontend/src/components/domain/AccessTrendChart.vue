<script setup lang="ts">
import { computed } from 'vue'
import type { AccessPoint } from '../../types/domain'

const props = withDefaults(
  defineProps<{ series: AccessPoint[]; quietDays?: number; halfLife?: number }>(),
  { quietDays: 30, halfLife: 14 },
)

const W = 1000
const H = 240
const PAD_L = 46
const PAD_R = 12
const PAD_T = 14
const PAD_B = 30

const points = computed(() => [...props.series].sort((a, b) => a.stat_date.localeCompare(b.stat_date)))
const maxAccess = computed(() => Math.max(1, ...points.value.map((point) => point.access_count)))
const innerW = computed(() => W - PAD_L - PAD_R)
const innerH = computed(() => H - PAD_T - PAD_B)
const barW = computed(() => (points.value.length ? innerW.value / points.value.length : 0))

const weightMax = computed(() => Math.max(0.0001, ...points.value.map((point) => point.decay_weight)))

function xOf(index: number): number {
  return PAD_L + index * barW.value + barW.value / 2
}

function yOf(value: number): number {
  return PAD_T + innerH.value - (value / maxAccess.value) * innerH.value
}

const areaPath = computed(() => {
  if (!points.value.length) return ''
  const coords = points.value.map((point, index) => [xOf(index), yOf(point.access_count)])
  const line = coords.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return `${line} L${coords[coords.length - 1][0].toFixed(1)},${(PAD_T + innerH.value).toFixed(1)} L${coords[0][0].toFixed(1)},${(PAD_T + innerH.value).toFixed(1)} Z`
})

const weightPath = computed(() => {
  if (!points.value.length) return ''
  return points.value
    .map((point, index) => {
      const normalized = (point.decay_weight / weightMax.value) * 0.35
      const y = PAD_T + innerH.value - normalized * innerH.value
      return `${index === 0 ? 'M' : 'L'}${xOf(index).toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const quietX = computed(() => {
  const count = points.value.length
  const quiet = Math.min(props.quietDays, count)
  return PAD_L + (count - quiet) * barW.value
})

const yTicks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(maxAccess.value * ratio)))
const xTicks = computed(() => {
  const list = points.value
  if (!list.length) return []
  const step = Math.ceil(list.length / 6)
  return list.filter((_, index) => index % step === 0).map((point, index) => ({
    x: xOf(index * step),
    label: point.stat_date.slice(5),
  }))
})
</script>

<template>
  <figure class="chart">
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="近 90 天访问趋势">
      <rect
        :x="quietX"
        :y="PAD_T"
        :width="Math.max(W - PAD_R - quietX, 0)"
        :height="innerH"
        style="fill: var(--cold-wash); opacity: 0.7"
      />
      <line
        :x1="PAD_L"
        :x2="W - PAD_R"
        :y1="PAD_T + innerH"
        :y2="PAD_T + innerH"
        stroke="var(--line-strong)"
      />
      <g v-for="tick in yTicks" :key="tick">
        <line
          :x1="PAD_L - 4"
          :x2="W - PAD_R"
          :y1="yOf(tick)"
          :y2="yOf(tick)"
          stroke="var(--line-soft)"
          stroke-dasharray="2 4"
        />
        <text :x="PAD_L - 8" :y="yOf(tick) + 3" class="axis" text-anchor="end">{{ tick }}</text>
      </g>
      <path :d="areaPath" style="fill: var(--cold-soft); opacity: 0.32" />
      <path :d="areaPath" fill="none" stroke="var(--cold)" stroke-width="1.6" />
      <path :d="weightPath" fill="none" stroke="var(--wood)" stroke-width="2" stroke-dasharray="5 4" />
      <g v-for="(point, index) in points" :key="point.stat_date">
        <rect
          v-if="point.access_count > 0"
          :x="xOf(index) - Math.max(barW * 0.3, 0.8)"
          :y="yOf(point.access_count)"
          :width="Math.max(barW * 0.6, 1.2)"
          :height="PAD_T + innerH - yOf(point.access_count)"
          style="fill: var(--slate); opacity: 0.24"
        />
      </g>
      <line
        :x1="quietX"
        :x2="quietX"
        :y1="PAD_T"
        :y2="PAD_T + innerH"
        stroke="var(--block)"
        stroke-dasharray="4 4"
      />
      <text :x="quietX + 6" :y="PAD_T + 12" class="axis axis-strong">
        近 {{ quietDays }} 天静默线
      </text>
      <g v-for="tick in xTicks" :key="tick.label">
        <text :x="tick.x" :y="H - 10" class="axis" text-anchor="middle">{{ tick.label }}</text>
      </g>
    </svg>
    <figcaption>
      <span class="key"><i class="swatch bar-swatch"></i>每日访问次数</span>
      <span class="key"><i class="swatch line-swatch"></i>衰减权重（半衰期 {{ halfLife }} 天）</span>
      <span class="key mono">峰值 {{ maxAccess }}/日</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.chart {
  margin: 0;
  border: 1px solid var(--line);
  background: var(--frost-1);
  padding: 8px 8px 4px;
}
svg {
  display: block;
  width: 100%;
  height: auto;
}
.axis {
  font-family: var(--font-mono);
  font-size: 9.5px;
  fill: var(--slate-faint);
}
.axis-strong {
  fill: var(--block);
  font-size: 9.5px;
}
figcaption {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  padding: 6px 6px 2px;
  font-size: 10.5px;
  color: var(--slate-soft);
}
.key {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.swatch {
  width: 14px;
  height: 3px;
  display: inline-block;
}
.bar-swatch {
  background: var(--slate);
  opacity: 0.4;
  height: 8px;
  width: 6px;
}
.line-swatch {
  background: var(--wood);
}
</style>
