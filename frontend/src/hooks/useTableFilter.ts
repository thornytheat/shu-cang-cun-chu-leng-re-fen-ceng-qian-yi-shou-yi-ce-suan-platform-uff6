import { computed, ref } from 'vue'
import type { DwLayer, StorageTier, TableRow } from '../types/domain'

const LAYER_ORDER: DwLayer[] = ['ods', 'dwd', 'dws', 'ads']
const TIER_ORDER: StorageTier[] = ['hot', 'warm', 'cold']

/** 货架视图的筛选/排序状态（存储概览与表热度页共用）。 */
export function useTableFilter(source: () => TableRow[]) {
  const tier = ref<StorageTier | 'all'>('all')
  const layer = ref<DwLayer | 'all'>('all')
  const keyword = ref('')
  const sort = ref<'size' | 'score' | 'save' | 'name'>('size')

  const filtered = computed(() => {
    const term = keyword.value.trim().toLowerCase()
    const rows = source().filter((row) => {
      if (tier.value !== 'all' && row.tier !== tier.value) return false
      if (layer.value !== 'all' && row.layer !== layer.value) return false
      if (term && !row.full_name.toLowerCase().includes(term)) return false
      return true
    })
    const sorted = [...rows]
    switch (sort.value) {
      case 'score':
        sorted.sort((a, b) => b.hot_score - a.hot_score)
        break
      case 'save':
        sorted.sort((a, b) => b.cold_save_month - a.cold_save_month)
        break
      case 'name':
        sorted.sort((a, b) => a.full_name.localeCompare(b.full_name))
        break
      default:
        sorted.sort((a, b) => b.size_gb - a.size_gb)
    }
    return sorted
  })

  const layerOptions = computed(() =>
    LAYER_ORDER.map((value) => ({
      value,
      count: source().filter((row) => row.layer === value).length,
    })),
  )

  const tierOptions = computed(() =>
    TIER_ORDER.map((value) => ({
      value,
      count: source().filter((row) => row.tier === value).length,
    })),
  )

  function reset() {
    tier.value = 'all'
    layer.value = 'all'
    keyword.value = ''
    sort.value = 'size'
  }

  return { tier, layer, keyword, sort, filtered, layerOptions, tierOptions, reset }
}
