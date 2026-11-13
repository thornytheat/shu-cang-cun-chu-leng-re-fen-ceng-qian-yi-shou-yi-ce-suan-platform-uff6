export interface ApiError {
  code: string
  message: string
  detail?: string
  traceId?: string | null
  status?: number
}

export interface PageMeta {
  total: number
  returned: number
  filters: Record<string, unknown>
}

export interface ListResponse<T> {
  items: T[]
  meta: PageMeta
}
