import http from './http'
import type { Overview } from '../types/domain'

export async function fetchOverview(): Promise<Overview> {
  const { data } = await http.get<Overview>('/overview')
  return data
}

export async function fetchAuditLogs(limit = 30): Promise<{ items: import('../types/domain').AuditEntry[] }> {
  const { data } = await http.get('/audit-logs', { params: { limit } })
  return data
}
