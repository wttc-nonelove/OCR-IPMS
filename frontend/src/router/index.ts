import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import Project from '../views/Project.vue'
import Invoice from '../views/Invoice.vue'
import Close from '../views/Close.vue'
import Report from '../views/Report.vue'
import System from '../views/System.vue'

const routes = [
  { path: '/login', name: 'login', component: Login },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: Dashboard },
  { path: '/project', name: 'project', component: Project },
  { path: '/invoice', name: 'invoice', component: Invoice },
  { path: '/close', name: 'close', component: Close },
  { path: '/report', name: 'report', component: Report },
  { path: '/system', name: 'system', component: System }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.name === 'login') return true
  if (!auth.isLoggedIn) return '/login'
  if (!auth.can(String(to.name))) return '/dashboard'
  return true
})

export default router
