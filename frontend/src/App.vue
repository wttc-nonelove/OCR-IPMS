<template>
  <router-view v-if="$route.name === 'login'" />
  <el-container v-else class="app-shell">
    <el-aside width="260px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">PM</div>
        <div>
          <strong>智能项目管理</strong>
          <span>OCR/NLP 项目全周期</span>
        </div>
      </div>

      <el-menu router :default-active="$route.path" class="menu">
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>

      <section class="side-panel">
        <span class="panel-label">当前审批流</span>
        <ol class="mini-flow">
          <li class="done">业务提交</li>
          <li class="current">{{ flowCurrent }}</li>
          <li>{{ flowNext }}</li>
        </ol>
      </section>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <h1>{{ routeTitle }}</h1>
          <p>{{ routeSubtitle }}</p>
        </div>
        <div class="top-actions">
          <el-tag effect="light">{{ auth.user?.name }} / {{ currentRoleName }}</el-tag>
          <el-button v-if="auth.can('project') && auth.user?.role === 'business'" type="primary" @click="router.push('/project')">
            新建立项
          </el-button>
          <el-button @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Checked, Coin, DataAnalysis, FolderOpened, HomeFilled, Setting } from '@element-plus/icons-vue'
import { roleNames, roleRoutes, useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const allMenus = [
  { name: 'dashboard', path: '/dashboard', label: '工作台', icon: HomeFilled, subtitle: '多角色协同、待办审批、项目经营指标总览' },
  { name: 'project', path: '/project', label: '立项管理', icon: FolderOpened, subtitle: '合同解析、差异确认、立项审核与项目启动' },
  { name: 'invoice', path: '/invoice', label: '开票回款', icon: Coin, subtitle: '发票识别、开票约束、回款绑定与应收计算' },
  { name: 'close', path: '/close', label: '结项管理', icon: Checked, subtitle: '结项申请、财务审批、归档只读和撤回' },
  { name: 'report', path: '/report', label: '查询报表', icon: DataAnalysis, subtitle: '项目、财务、明细查询和运行时导出任务' },
  { name: 'system', path: '/system', label: '系统管理', icon: Setting, subtitle: '用户、角色、字典、审批模板和操作日志' }
]

const menus = computed(() => {
  if (!auth.user) return []
  return allMenus.filter((item) => roleRoutes[auth.user!.role].includes(item.name))
})
const currentMenu = computed(() => allMenus.find((item) => item.name === route.name))
const routeTitle = computed(() => currentMenu.value?.label || '系统')
const routeSubtitle = computed(() => currentMenu.value?.subtitle || '智能项目管理系统')
const currentRoleName = computed(() => (auth.user ? roleNames[auth.user.role] : '未登录'))
const flowCurrent = computed(() => {
  if (route.name === 'invoice') return '财务登记'
  if (route.name === 'close') return '财务审批'
  if (route.name === 'system') return '模板配置'
  return '管理员审核'
})
const flowNext = computed(() => {
  if (route.name === 'invoice') return '金额校验'
  if (route.name === 'close') return '已结项只读'
  if (route.name === 'system') return '权限生效'
  return '项目已立项'
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>
