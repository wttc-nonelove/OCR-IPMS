<template>
  <section class="page-grid">
    <div class="metric-grid">
      <article class="metric-card">
        <span>项目总数</span>
        <strong>{{ summary.total_projects }}</strong>
        <small>统一编号 PRJ-YYYY-NNNN</small>
      </article>
      <article class="metric-card">
        <span>进行中项目</span>
        <strong>{{ summary.active_projects }}</strong>
        <small>管理员确认后进入进行中</small>
      </article>
      <article class="metric-card">
        <span>累计开票金额</span>
        <strong>{{ money(summary.total_invoice_amount) }}</strong>
        <small>已结项项目不可再开票</small>
      </article>
      <article class="metric-card">
        <span>累计回款金额</span>
        <strong>{{ money(summary.total_payment_amount) }}</strong>
        <small>回款绑定单张发票</small>
      </article>
    </div>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>{{ roleLabel }}工作台</h2>
          <p>{{ rolePanel.summary || '暂无角色工作台数据' }}</p>
        </div>
        <span class="badge">{{ rolePanel.badge || '真实数据' }}</span>
      </div>

      <article class="role-panel active">
        <div class="role-panel-head">
          <div>
            <span class="role-label">{{ roleLabel }}</span>
            <h3>{{ rolePanel.title || '暂无待办' }}</h3>
          </div>
          <span class="badge warn">{{ rolePanel.todo_count || 0 }} 待办</span>
        </div>
        <div class="role-stats">
          <div v-for="item in rolePanel.stats" :key="item.label">
            <strong>{{ displayValue(item.value) }}</strong>
            <span>{{ item.label }}</span>
          </div>
        </div>
        <el-empty v-if="!rolePanel.stats?.length" description="暂无角色指标" />
        <ul v-else class="role-task-list">
          <li v-for="task in rolePanel.tasks" :key="task">{{ task }}</li>
        </ul>
        <div class="role-actions">
          <el-button v-for="action in rolePanel.actions" :key="action.path" @click="$router.push(action.path)">
            {{ action.label }}
          </el-button>
        </div>
      </article>
    </section>

    <div class="content-grid dashboard-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>项目全生命周期</h2>
            <p>草稿、待审核、已立项、进行中、已结项按业务规则流转</p>
          </div>
          <span class="badge info">闭环流程</span>
        </div>
        <div class="lifecycle">
          <div v-for="step in lifecycleSteps" :key="step.key" class="life-step" :class="step.className">
            <span>{{ step.no }}</span>
            <strong>{{ step.label }}</strong>
            <small>{{ step.count }} 个项目</small>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>待办事项</h2>
          <span class="badge danger">{{ rolePanel.todos?.length || 0 }}</span>
        </div>
        <el-empty v-if="!rolePanel.todos?.length" description="暂无待办事项" />
        <div v-else class="todo-list">
          <button v-for="todo in rolePanel.todos" :key="todo.title" class="todo-item" type="button" @click="$router.push(todo.path)">
            <span class="dot" :class="todo.level"></span>
            <div>
              <strong>{{ todo.title }}</strong>
              <small>{{ todo.desc }}</small>
            </div>
          </button>
        </div>
      </section>
    </div>

    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <h2>月度开票 / 回款</h2>
        </div>
        <el-empty v-if="!monthly.length" description="暂无月度数据" />
        <div v-else class="bar-chart" aria-label="月度开票回款柱状图">
          <div v-for="item in monthlyBars" :key="item.month" :style="item.style">
            <span>{{ item.label }}</span>
          </div>
        </div>
        <div class="legend">
          <span><i class="legend-invoice"></i>开票</span>
          <span><i class="legend-payment"></i>回款</span>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>快捷入口</h2>
        </div>
        <div class="quick-grid">
          <el-button v-if="auth.can('project')" @click="$router.push('/project')">合同登记</el-button>
          <el-button v-if="auth.can('invoice')" @click="$router.push('/invoice')">发票识别</el-button>
          <el-button v-if="auth.can('close')" @click="$router.push('/close')">提交结项</el-button>
          <el-button v-if="auth.can('report')" @click="$router.push('/report')">导出报表</el-button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../api/http'
import { roleNames, useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const summary = reactive({ total_projects: 0, active_projects: 0, total_invoice_amount: 0, total_payment_amount: 0 })
const lifecycle = reactive<Record<string, number>>({ draft: 0, pending: 0, approved: 0, active: 0, closed: 0 })
const rolePanel = reactive<any>({ stats: [], tasks: [], actions: [], todos: [] })
const monthly = ref<any[]>([])

const roleLabel = computed(() => (auth.user ? roleNames[auth.user.role] : '用户'))
const lifecycleSteps = computed(() => [
  { key: 'draft', no: '01', label: '草稿', count: lifecycle.draft, className: lifecycle.draft > 0 ? 'current' : '' },
  { key: 'pending', no: '02', label: '待审核', count: lifecycle.pending, className: lifecycle.pending > 0 ? 'current' : '' },
  { key: 'approved', no: '03', label: '已立项', count: lifecycle.approved, className: lifecycle.approved > 0 ? 'done' : '' },
  { key: 'active', no: '04', label: '进行中', count: lifecycle.active, className: lifecycle.active > 0 ? 'done' : '' },
  { key: 'closed', no: '05', label: '已结项', count: lifecycle.closed, className: lifecycle.closed > 0 ? 'done' : '' }
])
const monthlyBars = computed(() => {
  const max = Math.max(1, ...monthly.value.map((item) => Math.max(item.invoice || 0, item.payment || 0)))
  return monthly.value.map((item) => ({
    ...item,
    label: `${Number(item.month.slice(5))}月`,
    style: { '--invoice': `${Math.max(4, ((item.invoice || 0) / max) * 100)}%`, '--payment': `${Math.max(4, ((item.payment || 0) / max) * 100)}%` }
  }))
})

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

function displayValue(value: string | number) {
  return typeof value === 'number' ? value.toLocaleString('zh-CN') : value
}

onMounted(async () => {
  const res: any = await http.get('/statistics/dashboard')
  Object.assign(summary, res.data.summary || {})
  Object.assign(lifecycle, res.data.lifecycle || {})
  Object.assign(rolePanel, res.data.role_panel || {})
  monthly.value = res.data.monthly || []
})
</script>
