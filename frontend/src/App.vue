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

      <el-menu router :default-active="activeMenu" class="menu">
        <template v-for="item in menus" :key="item.path">
          <el-sub-menu v-if="item.children?.length" :index="item.path">
            <template #title>
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </template>
            <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path">
              <span>{{ child.label }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </el-menu-item>
        </template>
      </el-menu>

      <section class="side-panel">
        <span class="panel-label">当前审批流</span>
        <ol class="mini-flow">
          <li
            v-for="step in flowSteps"
            :key="step.label"
            :class="{ done: step.status === 'done', current: step.status === 'current' }"
          >
            {{ step.label }}
          </li>
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
          <el-button v-if="auth.can('project') && ['business', 'admin'].includes(auth.user?.role || '')" type="primary" @click="router.push('/project')">
            新建立项
          </el-button>
          <el-button @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view v-slot="{ Component }">
          <transition name="fade-page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Checked, Coin, DataAnalysis, FolderOpened, HomeFilled, Setting } from '@element-plus/icons-vue'
import { http } from './api/http'
import { roleNames, roleRoutes, useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const allMenus = [
  { name: 'dashboard', path: '/dashboard', label: '工作台', icon: HomeFilled, subtitle: '多角色协同、待办审批与项目经营指标总览' },
  { name: 'project', path: '/project', label: '立项管理', icon: FolderOpened, subtitle: '合同解析、差异确认、立项审核与项目启动' },
  {
    name: 'invoice',
    path: '/invoice',
    label: '开票回款',
    icon: Coin,
    subtitle: '开票、回款、记录查询与项目台账',
  },
  { name: 'close', path: '/close', label: '结项管理', icon: Checked, subtitle: '结项申请、财务审批、归档只读和撤回' },
  { name: 'report', path: '/report', label: '查询报表', icon: DataAnalysis, subtitle: '项目、财务、明细查询和运行时导出任务' },
  { name: 'system', path: '/system', label: '系统管理', icon: Setting, subtitle: '用户、字典、审批模板和操作日志' },
]

const menus = computed(() => {
  if (!auth.user) return []
  return allMenus.filter((item) => roleRoutes[auth.user!.role].includes(item.name))
})
const activeMenu = computed(() => route.path)
const currentMenu = computed(() => allMenus.find((item) => item.name === route.name))
const routeTitle = computed(() => currentMenu.value?.label || '系统')
const routeSubtitle = computed(() => currentMenu.value?.subtitle || '智能项目管理系统')
const currentRoleName = computed(() => (auth.user ? roleNames[auth.user.role] : '未登录'))
const remoteFlow = ref<any>(null)

const defaultFlowSteps = computed(() => {
  if (route.name === 'invoice') return [
    { label: '登记', status: 'done' },
    { label: '金额校验', status: 'current' },
    { label: '台账更新', status: 'pending' },
  ]
  if (route.name === 'close') return [
    { label: '提交结项', status: 'done' },
    { label: '财务审批', status: 'current' },
    { label: '已结项', status: 'pending' },
  ]
  if (route.name === 'project') return [
    { label: '草稿', status: 'done' },
    { label: '待审核', status: 'current' },
    { label: '进行中', status: 'pending' },
  ]
  return [
    { label: '业务提交', status: 'done' },
    { label: '节点处理', status: 'current' },
    { label: '流程完成', status: 'pending' },
  ]
})
const flowSteps = computed(() => (remoteFlow.value?.has_todo && remoteFlow.value.steps?.length ? remoteFlow.value.steps : defaultFlowSteps.value))

async function loadFlow() {
  if (!auth.isLoggedIn) return
  try {
    const res: any = await http.get('/approval/flow/current')
    remoteFlow.value = res.data
  } catch {
    remoteFlow.value = null
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(loadFlow)
watch(() => route.fullPath, loadFlow)
</script>
