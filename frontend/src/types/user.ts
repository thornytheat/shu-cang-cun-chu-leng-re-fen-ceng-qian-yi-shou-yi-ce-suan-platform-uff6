export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface User {
  id: string
  email: string
  display_name: string
  role: UserRole
  role_label: string
  team: string
  permissions: string[]
}

export interface LoginResult {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}
