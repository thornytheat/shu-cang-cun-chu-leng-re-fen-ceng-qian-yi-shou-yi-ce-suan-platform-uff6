import http from './http'
import type { PolicyGroup, TrialResult } from '../types/domain'

export async function fetchPolicy(): Promise<PolicyGroup> {
  const { data } = await http.get<PolicyGroup>('/policies/current')
  return data
}

export async function fetchPolicyHistory(): Promise<{ items: Array<{ version: number; tiers: unknown[] }> }> {
  const { data } = await http.get('/policies/history')
  return data
}

export interface PolicyUpdatePayload {
  tiers: Array<{ tier: string; score_min: number; unit_price: number; target_region: string }>
  quiet_days: number
  block_recent_days: number
  min_partition: number
  migrate_price: number
  migrate_fixed: number
  note: string
}

export async function updatePolicy(payload: PolicyUpdatePayload): Promise<PolicyGroup> {
  const { data } = await http.put<PolicyGroup>('/policies/current', payload)
  return data
}

export async function runTrial(threshold: number): Promise<TrialResult> {
  const { data } = await http.post<TrialResult>('/policies/trial', { threshold, include_warm: true })
  return data
}
