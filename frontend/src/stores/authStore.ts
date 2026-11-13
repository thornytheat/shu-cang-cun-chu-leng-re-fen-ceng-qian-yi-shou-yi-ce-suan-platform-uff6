import { defineStore } from 'pinia'
import { fetchMe, login as apiLogin } from '../api/auth'
import type { User, UserRole } from '../types/user'
import { TOKEN_KEY } from '../utils/request'

interface AuthState {
  token: string
  user: User | null
  loading: boolean
  error: string
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY) ?? '',
    user: null,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token),
    role: (state): UserRole => (state.user?.role ?? 'viewer') as UserRole,
    displayName: (state): string => state.user?.display_name ?? '',
    email: (state): string => state.user?.email ?? '',
    isReadOnly: (state): boolean => (state.user?.role ?? 'viewer') === 'viewer',
    can: (state) => (action: string): boolean => Boolean(state.user?.permissions?.includes(action)),
  },
  actions: {
    async login(email: string, password: string) {
      this.loading = true
      this.error = ''
      try {
        const result = await apiLogin(email, password)
        this.token = result.access_token
        this.user = result.user
        localStorage.setItem(TOKEN_KEY, result.access_token)
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async restore() {
      if (!this.token) return
      try {
        this.user = await fetchMe()
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
