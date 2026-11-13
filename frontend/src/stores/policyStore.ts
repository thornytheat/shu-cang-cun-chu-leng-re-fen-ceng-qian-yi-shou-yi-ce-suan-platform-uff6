import { defineStore } from 'pinia'
import { fetchPolicy, runTrial, updatePolicy, type PolicyUpdatePayload } from '../api/policies'
import type { PolicyGroup, TrialResult } from '../types/domain'

interface PolicyState {
  policy: PolicyGroup | null
  threshold: number
  trial: TrialResult | null
  selected: string[]
  loading: boolean
  trialLoading: boolean
  saving: boolean
  error: string
  notice: string
}

export const usePolicyStore = defineStore('policy', {
  state: (): PolicyState => ({
    policy: null,
    threshold: 20,
    trial: null,
    selected: [],
    loading: false,
    trialLoading: false,
    saving: false,
    error: '',
    notice: '',
  }),
  getters: {
    priceOf: (state) => (tier: string): number => {
      const row = state.policy?.tiers.find((item) => item.tier === tier)
      return row ? row.unit_price : 0
    },
    selectedHits: (state) =>
      (state.trial?.hits ?? []).filter((hit) => state.selected.includes(hit.table_id)),
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.policy = await fetchPolicy()
        const warm = this.policy.tiers.find((row) => row.tier === 'warm')
        if (warm) this.threshold = warm.score_min
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载策略失败'
      } finally {
        this.loading = false
      }
    },
    async trialRun(threshold?: number) {
      this.trialLoading = true
      this.error = ''
      this.notice = ''
      if (typeof threshold === 'number') this.threshold = threshold
      try {
        this.trial = await runTrial(this.threshold)
        this.selected = this.trial.hits.map((hit) => hit.table_id)
        this.notice = `试算完成：命中 ${this.trial.hit_count} 张，预估月省 ¥${this.trial.save_month.toLocaleString('zh-CN')}`
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '试算失败'
        this.trial = null
      } finally {
        this.trialLoading = false
      }
    },
    toggle(tableId: string) {
      if (this.selected.includes(tableId)) {
        this.selected = this.selected.filter((id) => id !== tableId)
      } else {
        this.selected = [...this.selected, tableId]
      }
    },
    selectTop(count: number) {
      this.selected = (this.trial?.hits ?? []).slice(0, count).map((hit) => hit.table_id)
    },
    async save(payload: PolicyUpdatePayload) {
      this.saving = true
      this.error = ''
      this.notice = ''
      try {
        this.policy = await updatePolicy(payload)
        this.notice = `策略已升版至 v${this.policy.version}（旧版本归档可追溯）`
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '保存失败'
      } finally {
        this.saving = false
      }
    },
  },
})
