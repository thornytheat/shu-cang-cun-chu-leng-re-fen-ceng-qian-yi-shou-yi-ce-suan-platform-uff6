import http from './http'
import type { ListResponse } from '../types/api'
import type { Plan } from '../types/domain'

export async function fetchPlans(): Promise<ListResponse<Plan>> {
  const { data } = await http.get<ListResponse<Plan>>('/plans')
  return data
}

export async function fetchPlan(id: string): Promise<Plan> {
  const { data } = await http.get<Plan>(`/plans/${id}`)
  return data
}

export async function createPlan(payload: {
  title: string
  threshold: number
  table_ids: string[]
  note?: string
}): Promise<Plan> {
  const { data } = await http.post<Plan>('/plans', payload)
  return data
}

export async function addPlanItems(id: string, tableIds: string[]): Promise<Plan> {
  const { data } = await http.post<Plan>(`/plans/${id}/items`, { table_ids: tableIds })
  return data
}

export async function removePlanItem(planId: string, itemId: string): Promise<Plan> {
  const { data } = await http.delete<Plan>(`/plans/${planId}/items/${itemId}`)
  return data
}

export async function recheckPlan(id: string): Promise<Plan> {
  const { data } = await http.post<Plan>(`/plans/${id}/recheck`)
  return data
}

export async function submitPlan(id: string): Promise<Plan> {
  const { data } = await http.post<Plan>(`/plans/${id}/submit`)
  return data
}

export function exportTicketsUrl(id: string): string {
  return `/api/plans/${id}/export.csv`
}

export async function downloadTickets(id: string): Promise<{ blob: Blob; rows: number; filename: string }> {
  const response = await http.get(`/plans/${id}/export.csv`, { responseType: 'blob' })
  const disposition = String(response.headers['content-disposition'] ?? '')
  const match = disposition.match(/filename="?([^";]+)"?/)
  const rows = Number(response.headers['x-ticket-rows'] ?? 0)
  return {
    blob: response.data as Blob,
    rows,
    filename: match?.[1] ?? `coldtier-${id}-tickets.csv`,
  }
}
