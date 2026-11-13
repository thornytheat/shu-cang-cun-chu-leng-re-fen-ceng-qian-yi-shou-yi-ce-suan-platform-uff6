import { defineStore } from 'pinia'
import { fetchTableDetail, fetchTables, type TableQuery } from '../api/tables'
import type { TableDetail, TableRow } from '../types/domain'

interface TableState {
  rows: TableRow[]
  total: number
  loading: boolean
  error: string
  query: TableQuery
  detail: TableDetail | null
  detailLoading: boolean
  detailError: string
}

export const useTableStore = defineStore('tables', {
  state: (): TableState => ({
    rows: [],
    total: 0,
    loading: false,
    error: '',
    query: { sort: 'size' },
    detail: null,
    detailLoading: false,
    detailError: '',
  }),
  getters: {
    tierCounts: (state): Record<string, number> => {
      const counts: Record<string, number> = { hot: 0, warm: 0, cold: 0 }
      for (const row of state.rows) counts[row.tier] = (counts[row.tier] ?? 0) + 1
      return counts
    },
  },
  actions: {
    async load(query: TableQuery = {}) {
      this.loading = true
      this.error = ''
      this.query = { ...this.query, ...query }
      try {
        const result = await fetchTables(this.query)
        this.rows = result.items
        this.total = result.meta.total
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadDetail(id: string) {
      this.detailLoading = true
      this.detailError = ''
      this.detail = null
      try {
        this.detail = await fetchTableDetail(id)
      } catch (error) {
        this.detailError = (error as { message?: string }).message ?? '加载失败'
      } finally {
        this.detailLoading = false
      }
    },
  },
})
