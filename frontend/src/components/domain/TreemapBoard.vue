<script setup lang="ts">
import { computed } from 'vue'
import type { LayerCell } from '../../types/domain'
import { LAYER_LABELS, TIER_LABELS } from '../../constants/enums'
import { gb, money } from '../../utils/format'

const props = withDefaults(defineProps<{ cells: LayerCell[]; width?: number; height?: number }>(), {
  width: 1000,
  height: 400,
})

interface Box {
  cell: LayerCell
  x: number
  y: number
  w: number
  h: number
}

/** 经典 squarified treemap（按面积排序后逐行最优化长宽比），自绘不引外部库。 */
function squarify(items: LayerCell[], x: number, y: number, w: number, h: number): Box[] {
  const boxes: Box[] = []
  const source = items.filter((item) => item.size_gb > 0).sort((a, b) => b.size_gb - a.size_gb)
  if (!source.length || w <= 0 || h <= 0) return boxes
  const total = source.reduce((sum, item) => sum + item.size_gb, 0)
  const scale = (w * h) / total
  const areas = source.map((item) => item.size_gb * scale)

  let index = 0
  let cx = x
  let cy = y
  let cw = w
  let ch = h

  while (index < areas.length) {
    const shortSide = Math.min(cw, ch)
    const row: number[] = []
    let best = Number.POSITIVE_INFINITY
    let cursor = index
    while (cursor < areas.length) {
      const candidate = [...row, areas[cursor]]
      const ratio = worst(candidate, shortSide)
      if (row.length === 0 || ratio <= best) {
        row.push(areas[cursor])
        best = ratio
        cursor += 1
      } else {
        break
      }
    }
    const rowArea = row.reduce((sum, area) => sum + area, 0)
    const horizontal = cw >= ch
    const rowThickness = horizontal ? rowArea / ch : rowArea / cw
    let offset = 0
    row.forEach((area, rowIndex) => {
      const span = horizontal ? area / rowThickness : area / rowThickness
      const item = source[index + rowIndex]
      if (horizontal) {
        boxes.push({ cell: item, x: cx, y: cy + offset, w: rowThickness, h: span })
      } else {
        boxes.push({ cell: item, x: cx + offset, y: cy, w: span, h: rowThickness })
      }
      offset += span
    })
    if (horizontal) {
      cx += rowThickness
      cw -= rowThickness
    } else {
      cy += rowThickness
      ch -= rowThickness
    }
    index += row.length
  }
  return boxes
}

function worst(areas: number[], side: number): number {
  const sum = areas.reduce((acc, area) => acc + area, 0)
  const max = Math.max(...areas)
  const min = Math.min(...areas)
  if (sum <= 0 || side <= 0) return Number.POSITIVE_INFINITY
  return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min))
}

const boxes = computed(() => squarify(props.cells, 0, 0, props.width, props.height))
const totalSize = computed(() => props.cells.reduce((sum, cell) => sum + cell.size_gb, 0))

function fillOf(cell: LayerCell): string {
  return cell.tier === 'hot' ? 'var(--hot)' : cell.tier === 'warm' ? 'var(--warm)' : 'var(--cold)'
}
</script>

<template>
  <div class="board">
    <svg :viewBox="`0 0 ${width} ${height}`" role="img" aria-label="分层体积树图">
      <g v-for="box in boxes" :key="`${box.cell.layer}-${box.cell.tier}`">
        <rect
          :x="box.x + 1"
          :y="box.y + 1"
          :width="Math.max(box.w - 2, 0)"
          :height="Math.max(box.h - 2, 0)"
          :style="{ fill: fillOf(box.cell), opacity: box.cell.tier === 'cold' ? 0.72 : 0.86 }"
        />
        <text
          v-if="box.w > 74 && box.h > 34"
          :x="box.x + 9"
          :y="box.y + 21"
          class="cell-title"
        >
          {{ LAYER_LABELS[box.cell.layer] }} · {{ TIER_LABELS[box.cell.tier] }}
        </text>
        <text v-if="box.w > 74 && box.h > 52" :x="box.x + 9" :y="box.y + 38" class="cell-num">
          {{ gb(box.cell.size_gb) }}
        </text>
        <text v-if="box.w > 74 && box.h > 68" :x="box.x + 9" :y="box.y + 54" class="cell-sub">
          {{ box.cell.table_count }} 表 · ¥{{ money(box.cell.monthly_cost) }}/月
        </text>
      </g>
      <rect
        x="0.5"
        y="0.5"
        :width="width - 1"
        :height="height - 1"
        fill="none"
        stroke="var(--line-strong)"
      />
    </svg>
    <p class="caption mono">
      面积 = 分区体积，合计 {{ gb(totalSize) }}；色块 = 温区（热 / 温 / 冷）
    </p>
  </div>
</template>

<style scoped>
.board {
  border: 1px solid var(--line);
  background: var(--frost-1);
  padding: 10px 10px 6px;
}
svg {
  display: block;
  width: 100%;
  height: auto;
}
.cell-title {
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 700;
  fill: var(--frost-0);
}
.cell-num {
  font-family: var(--font-mono);
  font-size: 12.5px;
  fill: var(--frost-0);
  font-weight: 500;
}
.cell-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  fill: var(--frost-0);
  opacity: 0.86;
}
.caption {
  font-size: 10.5px;
  color: var(--slate-faint);
  letter-spacing: 0.04em;
  padding: 6px 2px 2px;
}
</style>
