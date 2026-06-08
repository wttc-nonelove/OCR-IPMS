import { defineStore } from 'pinia'
import { http } from '../api/http'

export type Role = 'admin' | 'business' | 'finance' | 'pm'

export const roleNames: Record<Role, string> = {
  admin: '管理员',
  business: '商务',
  finance: '财务',
  pm: '项目经理'
}

export const roleRoutes: Record<Role, string[]> = {
  admin: ['dashboard', 'project', 'invoice', 'close', 'report', 'system'],
  business: ['dashboard', 'project', 'report'],
  finance: ['dashboard', 'invoice', 'close', 'report'],
  pm: ['dashboard', 'project', 'close', 'report']
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null') as null | { id: number; username: string; name: string; role: Role }
  }),
  getters: {
    role: (state) => state.user?.role,
    isLoggedIn: (state) => Boolean(state.token && state.user)
  },
  actions: {
    async login(username: string, password: string) {
      const res: any = await http.post('/user/login', { username, password })
      this.token = res.data.token
      this.user = res.data.user
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
    can(routeName: string) {
      return this.user ? roleRoutes[this.user.role].includes(routeName) : false
    }
  }
})
