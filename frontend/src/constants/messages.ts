export const ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: '请先登录',
  AUTH_INVALID: '登录状态无效，请重新登录',
  TOKEN_EXPIRED: '登录已过期，请重新登录',
  FORBIDDEN: '当前角色无权执行该操作',
  NOT_FOUND: '对象不存在',
  VALIDATION_ERROR: '请求参数不合法',
  RATE_LIMITED: '请求过于频繁，请稍后重试',
  INTERNAL_ERROR: '服务内部错误',
  PLAN_NOT_DRAFT: '只有草稿状态的计划可以修改',
  PLAN_EMPTY: '计划中没有可提交的表',
  PLAN_HAS_BLOCKERS: '计划中仍有被阻断的表，请先移除',
  EXPORT_EMPTY: '没有可导出的计划项',
  THRESHOLD_INVALID: '阈值必须落在 0 到 100 之间',
  TRIAL_NO_HIT: '当前阈值下没有命中的表',
}

export const EMPTY_HINTS = {
  tables: '换个温区/分层筛选，或清空搜索词再看一遍货架。',
  trial: '把阈值调高（例如 30）再试算一次；阈值越高，命中的低热表越多。',
  plans: '先在「策略与试算」里跑一次试算，勾选候选表后即可建计划。',
}
