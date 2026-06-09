<template>
  <section class="page-grid">
    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>开票回款查询</h2>
          <p>汇总和趋势来自真实业务表；导出任务不落库，仅运行时队列维护</p>
        </div>
        <div class="filter-row">
          <el-date-picker v-model="month" type="month" value-format="YYYY-MM" placeholder="月份" />
          <el-input v-model="keyword" placeholder="项目 / 客户" style="width: 180px" />
          <el-button type="primary" @click="load">查询</el-button>
        </div>
      </div>
      <div class="report-summary">
        <div>
          <span>项目总数</span>
          <strong>{{ summary.total_projects }}</strong>
        </div>
        <div>
          <span>合同金额</span>
          <strong>{{ money(summary.total_contract_amount) }}</strong>
        </div>
        <div>
          <span>开票金额</span>
          <strong>{{ money(summary.total_invoice_amount) }}</strong>
        </div>
        <div>
          <span>应收余额</span>
          <strong>{{ money(summary.total_receivable) }}</strong>
        </div>
      </div>
    </section>

    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <h2>趋势图</h2>
        </div>
        <el-empty v-if="!monthly.length" description="暂无趋势数据" />
        <div v-else class="line-chart">
          <svg viewBox="0 0 520 220" role="img" aria-label="开票回款趋势图">
            <polyline class="grid-line" points="30,40 500,40"></polyline>
            <polyline class="grid-line" points="30,95 500,95"></polyline>
            <polyline class="grid-line" points="30,150 500,150"></polyline>
            <polyline class="line invoice-line" :points="invoicePoints"></polyline>
            <polyline class="line payment-line" :points="paymentPoints"></polyline>
          </svg>
        </div>
        <div class="legend">
          <span><i class="legend-invoice"></i>开票趋势</span>
          <span><i class="legend-payment"></i>回款趋势</span>
        </div>
      </section>

      <section v-if="auth.user?.role === 'admin' || auth.user?.role === 'finance'" class="panel">
        <div class="panel-head">
          <h2>导出任务</h2>
          <span class="badge ok">运行时队列</span>
        </div>
        <div class="export-list">
          <label><input v-model="exportTypes" type="checkbox" value="project" /> 项目明细</label>
          <label><input v-model="exportTypes" type="checkbox" value="invoice" /> 开票记录</label>
          <label><input v-model="exportTypes" type="checkbox" value="payment" /> 回款记录</label>
        </div>
        <el-alert
          v-if="task"
          :title="`导出任务：${task.task_id || '-'} / ${task.status}`"
          type="info"
          :closable="false"
          style="margin-top: 12px"
        />
        <div class="form-actions">
          <el-button :disabled="!task?.task_id" @click="checkStatus">刷新状态</el-button>
          <el-button v-if="task?.status === 'finished'" type="success" @click="downloadExport">下载文件</el-button>
          <el-button type="primary" @click="exportFile">开始导出</el-button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const month = ref('')
const keyword = ref('')
const exportTypes = ref(['project', 'invoice', 'payment'])
const summary = reactive({ total_projects: 0, total_contract_amount: 0, total_invoice_amount: 0, total_receivable: 0 })
const monthly = ref<any[]>([])
const task = ref<any>(null)

const maxTrend = computed(() => Math.max(1, ...monthly.value.map((item) => Math.max(item.invoice || 0, item.payment || 0))))
const invoicePoints = computed(() => buildPoints('invoice'))
const paymentPoints = computed(() => buildPoints('payment'))

function buildPoints(key: 'invoice' | 'payment') {
  if (!monthly.value.length) return ''
  const width = 470
  const step = monthly.value.length === 1 ? 0 : width / (monthly.value.length - 1)
  return monthly.value
    .map((item, index) => {
      const x = 30 + index * step
      const y = 180 - ((item[key] || 0) / maxTrend.value) * 140
      return `${x},${Math.max(40, y)}`
    })
    .join(' ')
}

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

async function load() {
  const res: any = await http.get('/statistics/dashboard')
  Object.assign(summary, res.data.summary || {})
  monthly.value = res.data.monthly || []
}

async function exportFile() {
  const res: any = await http.post('/export/batch', { export_types: exportTypes.value, format: 'excel' })
  task.value = res.data
  ElMessage.success('导出任务已创建，请稍后刷新状态')
}

async function checkStatus() {
  if (!task.value?.task_id) return
  const res: any = await http.get('/export/status', { params: { task_id: task.value.task_id } })
  task.value = res.data
}

async function downloadExport() {
  if (!task.value?.task_id) return
  const blob: any = await http.get('/export/download', { params: { task_id: task.value.task_id }, responseType: 'blob' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = task.value.file_name || `${task.value.task_id}.xlsx`
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

onMounted(load)
</script>
