import http from './http'
import type { ListResponse } from '../types/api'
import type {
  BillsAck,
  ExecutionAck,
  Plan,
  PlanReconciliation,
  ReceiptsAck,
} from '../types/domain'

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

export async function startBatch(id: string, batchNo: string, note = ''): Promise<ExecutionAck> {
  const { data } = await http.post<ExecutionAck>(`/plans/${id}/batches`, {
    batch_no: batchNo,
    note,
  })
  return data
}

export interface ReceiptPayload {
  receipt_no: string
  item_id: string
  result: 'success' | 'failed'
  actual_migrate_cost?: number
  message?: string
}

export async function postReceipts(
  id: string,
  receipts: ReceiptPayload[],
  batchNo = '',
): Promise<ReceiptsAck> {
  const { data } = await http.post<ReceiptsAck>(`/plans/${id}/receipts`, {
    batch_no: batchNo,
    receipts,
  })
  return data
}

export interface BillPayload {
  bill_no: string
  item_id: string
  bill_month: string
  actual_save_month: number
}

export async function postBills(id: string, bills: BillPayload[]): Promise<BillsAck> {
  const { data } = await http.post<BillsAck>(`/plans/${id}/bills`, { bills })
  return data
}

export async function fetchReconciliation(id: string): Promise<PlanReconciliation> {
  const { data } = await http.get<PlanReconciliation>(`/plans/${id}/reconciliation`)
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
