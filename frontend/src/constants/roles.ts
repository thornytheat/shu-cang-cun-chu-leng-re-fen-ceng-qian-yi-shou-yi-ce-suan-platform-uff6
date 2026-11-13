// 角色与前端可操作项 —— 后端真源：backend/src/constants/roles.py
// 前端只用于「按钮显隐」，真正的 403 由后端 RBAC 返回。
import type { UserRole } from '../types/user'

export const ROLES: UserRole[] = ['admin', 'analyst', 'viewer']

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: '平台负责人',
  analyst: '数据开发',
  viewer: '财务 / 报表 owner（只读）',
}

export const ROLE_SCOPE: Record<UserRole, string> = {
  admin: '策略与单价 · 审批 · 计划全流程 · 审计台账',
  analyst: '试算 · 建计划 · 风险复检 · 提交 · 执行对账 · 导出工单',
  viewer: '只读：存储概览、表热度、收益与风险',
}

export const DEMO_ACCOUNTS: Array<{ email: string; role: UserRole; name: string; note: string }> = [
  { email: 'admin@coldtier.io', role: 'admin', name: '陈可欣', note: '策略/审批/审计' },
  { email: 'analyst@coldtier.io', role: 'analyst', name: '林哲', note: '试算/计划/导出' },
  { email: 'viewer@coldtier.io', role: 'viewer', name: '赵敏', note: '只读收益与风险' },
]
