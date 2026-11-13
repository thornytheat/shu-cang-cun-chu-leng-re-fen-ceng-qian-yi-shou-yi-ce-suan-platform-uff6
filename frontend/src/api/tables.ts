import http from './http'
import type { ListResponse } from '../types/api'
import type { TableDetail, TableRow } from '../types/domain'

export interface TableQuery {
  tier?: string
  layer?: string
  q?: string
  sort?: string
  only_candidates?: boolean
}

export async function fetchTables(query: TableQuery = {}): Promise<ListResponse<TableRow>> {
  const { data } = await http.get<ListResponse<TableRow>>('/tables', { params: query })
  return data
}

export async function fetchTableDetail(id: string): Promise<TableDetail> {
  const { data } = await http.get<TableDetail>(`/tables/${id}`)
  return data
}

export async function recomputeHeat(): Promise<{ task_id: string; queued_at: string; tables: number }> {
  const { data } = await http.post('/tables/heat/recompute')
  return data
}

export async function fetchHeatStatus(): Promise<{
  last_computed_at: string | null
  table_count: number
  scored_count: number
  worker_heartbeat: string | null
  worker_online: boolean
}> {
  const { data } = await http.get('/tables/heat/status')
  return data
}
