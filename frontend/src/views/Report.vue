<template>
  <section class="page-grid report-page">
    <section class="panel report-hero-panel">
      <div class="panel-head">
        <div>
          <h2>开票回款查询</h2>
          <p>{{ mode === 'year' ? '按自然年汇总项目、开票、回款与应收余额' : '按自然月查看每日趋势和当月明细记录' }}</p>
        </div>
        <span class="badge ok">{{ rangeTitle }}</span>
      </div>

      <div class="report-mode-bar">
        <el-segmented
          v-model="mode"
          :options="[
            { label: '按年查询', value: 'year' },
            { label: '按月查询', value: 'month' }
          ]"
          @change="load"
        />
        <el-date-picker
          v-if="mode === 'year'"
          v-model="year"
          type="year"
          value-format="YYYY"
          placeholder="选择年份"
          @change="load"
        />
        <el-date-picker
          v-else
          v-model="month"
          type="month"
          value-format="YYYY-MM"
          placeholder="选择月份"
          @change="load"
        />
        <el-input v-model="keyword" clearable placeholder="项目 / 客户 / 合同编号" @keyup.enter="load" />
        <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      </div>

      <div class="report-summary">
        <div>
          <span>{{ mode === 'year' ? '年度项目数' : '月度项目数' }}</span>
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
          <span>回款金额</span>
          <strong>{{ money(summary.total_payment_amount) }}</strong>
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
          <div>
            <h2>{{ rangeTitle }}趋势图</h2>
            <p>{{ mode === 'year' ? '横轴固定展示 1-12 月' : '横轴展示当月每日开票与回款' }}</p>
          </div>
          <span class="badge">{{ hasTrendData ? (mode === 'year' ? '年度趋势' : '月度趋势') : '暂无数据' }}</span>
        </div>
        <el-empty v-if="!hasTrendData" :description="`${rangeTitle}暂无开票或回款数据`" />
        <div v-else class="line-chart yearly-chart">
          <svg viewBox="0 0 680 300" role="img" :aria-label="chartAriaLabel">
            <g class="axis-labels">
              <text v-for="tick in yTicks" :key="tick.y" x="12" :y="tick.y + 4">{{ tick.label }}</text>
            </g>
            <g>
              <line v-for="tick in yTicks" :key="gridKey(tick)" class="grid-line" x1="58" :y1="tick.y" x2="638" :y2="tick.y"></line>
              <line class="axis-line" x1="58" y1="30" x2="58" y2="224"></line>
              <line class="axis-line" x1="58" y1="224" x2="638" y2="224"></line>
            </g>
            <polyline class="line invoice-line" :points="invoicePoints"></polyline>
            <polyline class="line payment-line" :points="paymentPoints"></polyline>
            <g>
              <circle
                v-for="point in invoicePointList"
                :key="pointKey('invoice', point)"
                class="invoice-point"
                :cx="point.x"
                :cy="point.y"
                r="4.5"
                :aria-label="pointLabel('开票', point)"
              ></circle>
              <circle
                v-for="point in paymentPointList"
                :key="pointKey('payment', point)"
                class="payment-point"
                :cx="point.x"
                :cy="point.y"
                r="4.5"
                :aria-label="pointLabel('回款', point)"
              ></circle>
            </g>
            <g class="month-labels">
              <text v-for="point in axisLabelPoints" :key="point.period" :x="point.x" y="252">{{ point.label }}</text>
            </g>
          </svg>
        </div>
        <div class="legend">
          <span><i class="legend-invoice"></i>开票趋势</span>
          <span><i class="legend-payment"></i>回款趋势</span>
          <span>峰值：{{ money(maxTrend) }}</span>
        </div>
      </section>

      <section v-if="auth.user?.role === 'admin' || auth.user?.role === 'finance'" class="panel">
        <div class="panel-head">
          <div>
            <h2>导出任务</h2>
            <p>按当前查询模式、时间范围和关键字导出表格</p>
          </div>
          <span class="badge ok">运行时队列</span>
        </div>
        <div class="export-list">
          <label><input v-model="exportTypes" type="checkbox" value="project" /> 项目明细</label>
          <label><input v-model="exportTypes" type="checkbox" value="invoice" /> 开票记录</label>
          <label><input v-model="exportTypes" type="checkbox" value="payment" /> 回款记录</label>
        </div>
        <el-alert
          v-if="task"
          :title="taskTitle"
          type="info"
          :closable="false"
          style="margin-top: 12px"
        />
        <div class="form-actions">
          <el-button :disabled="!task?.task_id" @click="checkStatus">刷新状态</el-button>
          <el-button v-if="task?.status === 'finished'" type="success" @click="downloadExport">下载文件</el-button>
          <el-button type="primary" :disabled="!exportTypes.length" @click="exportFile">开始导出</el-button>
        </div>
      </section>
    </div>

    <section v-if="mode === 'month'" class="panel">
      <div class="panel-head">
        <div>
          <h2>{{ rangeTitle }}明细记录</h2>
          <p>按当前月份展示真实发票与回款记录</p>
        </div>
      </div>
      <el-tabs v-model="detailTab" class="finance-tabs">
        <el-tab-pane :label="`当月发票记录（${invoices.length}）`" name="invoice">
          <el-table :data="invoices" empty-text="当月暂无发票记录">
            <el-table-column prop="project_no" label="项目编号" min-width="130" />
            <el-table-column prop="project_name" label="项目名称" min-width="160" />
            <el-table-column prop="invoice_no" label="发票号码" min-width="130" />
            <el-table-column label="不含税金额" width="130">
              <template #default="{ row }">{{ money(row.amount_without_tax) }}</template>
            </el-table-column>
            <el-table-column label="税额" width="120">
              <template #default="{ row }">{{ money(row.tax_amount) }}</template>
            </el-table-column>
            <el-table-column label="价税合计" width="130">
              <template #default="{ row }">{{ money(row.amount) }}</template>
            </el-table-column>
            <el-table-column prop="invoice_date" label="开票日期" width="120" />
            <el-table-column prop="buyer" label="购方" min-width="160" />
            <el-table-column prop="seller" label="销方" min-width="160" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="`当月回款记录（${payments.length}）`" name="payment">
          <el-table :data="payments" empty-text="当月暂无回款记录">
            <el-table-column prop="project_no" label="项目编号" min-width="130" />
            <el-table-column prop="project_name" label="项目名称" min-width="160" />
            <el-table-column prop="invoice_no" label="关联发票" min-width="130" />
            <el-table-column label="回款金额" width="130">
              <template #default="{ row }">{{ money(row.amount) }}</template>
            </el-table-column>
            <el-table-column prop="payment_date" label="回款日期" width="120" />
            <el-table-column prop="payment_method" label="方式" width="100" />
            <el-table-column label="凭证" width="100">
              <template #default="{ row }">{{ row.voucher_file ? '已上传' : '未上传' }}</template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" min-width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const now = new Date()
const mode = ref<'year' | 'month'>('year')
const year = ref(String(now.getFullYear()))
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const keyword = ref('')
const loading = ref(false)
const detailTab = ref('invoice')
const exportTypes = ref(['project', 'invoice', 'payment'])
const summary = reactive({
  total_projects: 0,
  total_contract_amount: 0,
  total_invoice_amount: 0,
  total_payment_amount: 0,
  total_receivable: 0,
})
const trend = ref<any[]>([])
const invoices = ref<any[]>([])
const payments = ref<any[]>([])
const task = ref<any>(null)

const rangeTitle = computed(() => (mode.value === 'year' ? `${year.value} 年` : `${month.value} 月`))
const maxTrend = computed(() => Math.max(1, ...trend.value.map((item) => Math.max(item.invoice || 0, item.payment || 0))))
const hasTrendData = computed(() => trend.value.some((item) => Number(item.invoice || 0) > 0 || Number(item.payment || 0) > 0))
const invoicePointList = computed(() => buildPointList('invoice'))
const paymentPointList = computed(() => buildPointList('payment'))
const invoicePoints = computed(() => invoicePointList.value.map((point) => `${point.x},${point.y}`).join(' '))
const paymentPoints = computed(() => paymentPointList.value.map((point) => `${point.x},${point.y}`).join(' '))
const axisLabelPoints = computed(() => {
  const points = buildPointList('invoice')
  if (mode.value === 'year') {
    return points.map((point, index) => ({ x: point.x, period: point.period, label: `${index + 1}月` }))
  }
  const step = Math.max(1, Math.ceil(points.length / 8))
  return points
    .filter((_point, index) => index === 0 || index === points.length - 1 || index % step === 0)
    .map((point) => ({ x: point.x, period: point.period, label: `${Number(point.period.slice(-2))}日` }))
})
const chartAriaLabel = computed(() => `${rangeTitle.value}开票回款趋势图`)
const taskTitle = computed(() => `导出任务：${task.value?.task_id || '-'} / ${task.value?.status || '-'}`)
const yTicks = computed(() => {
  const top = 30
  const height = 194
  return [1, 0.75, 0.5, 0.25, 0].map((rate) => ({
    y: top + (1 - rate) * height,
    label: compactMoney(maxTrend.value * rate),
  }))
})

function buildPointList(key: 'invoice' | 'payment') {
  const left = 58
  const top = 30
  const width = 580
  const height = 194
  const data = trend.value.length ? trend.value : defaultTrend()
  const step = data.length === 1 ? 0 : width / (data.length - 1)
  return data.map((item, index) => {
    const value = Number(item[key] || 0)
    return {
      period: item.period || item.month,
      value,
      x: left + index * step,
      y: top + height - (value / maxTrend.value) * height,
    }
  })
}

function defaultTrend() {
  if (mode.value === 'year') {
    return Array.from({ length: 12 }, (_item, index) => ({ period: `${year.value}-${String(index + 1).padStart(2, '0')}`, invoice: 0, payment: 0 }))
  }
  const [targetYear, targetMonth] = month.value.split('-').map(Number)
  const days = new Date(targetYear, targetMonth, 0).getDate()
  return Array.from({ length: days }, (_item, index) => ({ period: `${month.value}-${String(index + 1).padStart(2, '0')}`, invoice: 0, payment: 0 }))
}

function gridKey(tick: { y: number }) {
  return `grid-${tick.y}`
}

function pointKey(type: 'invoice' | 'payment', point: { period: string }) {
  return `${type}-${point.period}`
}

function pointLabel(label: string, point: { period: string; value: number }) {
  return `${point.period} ${label}：${money(point.value)}`
}

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

function compactMoney(value: number) {
  const amount = Number(value || 0)
  if (amount >= 10000) return `${Math.round(amount / 10000)}万`
  return `${Math.round(amount)}`
}

async function load() {
  loading.value = true
  try {
    const res: any = await http.get('/statistics/report', {
      params: {
        mode: mode.value,
        year: Number(year.value),
        month: month.value,
        keyword: keyword.value || undefined,
      },
    })
    Object.assign(summary, res.data.summary || {})
    trend.value = res.data.trend || res.data.monthly || []
    invoices.value = res.data.invoices || []
    payments.value = res.data.payments || []
    task.value = null
  } finally {
    loading.value = false
  }
}

async function exportFile() {
  const res: any = await http.post('/export/batch', {
    export_types: exportTypes.value,
    format: 'excel',
    mode: mode.value,
    year: Number(year.value),
    month: month.value,
    keyword: keyword.value || undefined,
  })
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
