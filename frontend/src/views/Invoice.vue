<template>
  <section class="page-grid">
    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>开票回款</h2>
          <p>输入项目编号、合同编号、项目名称或甲方关键字，选择候选项目后进行登记、查询和台账核对。</p>
        </div>
        <span v-if="summary.project_id" class="badge" :class="summary.is_payment_complete ? 'ok' : 'danger'">
          {{ summary.payment_status_label }}
        </span>
      </div>

      <div class="finance-toolbar">
        <el-select
          v-model="selectedProjectId"
          filterable
          remote
          reserve-keyword
          clearable
          :remote-method="searchProjects"
          :loading="projectSearching"
          placeholder="输入关键字搜索项目"
          style="width: 100%"
          @change="onProjectChange"
        >
          <el-option v-for="project in projectOptions" :key="project.id" :label="projectLabel(project)" :value="project.id" />
        </el-select>
        <el-button :disabled="!selectedProjectId" @click="refreshFinance()">刷新</el-button>
        <el-button v-if="selectedProjectId" @click="openProjectDetail(selectedProjectId)">查看立项详情</el-button>
      </div>

      <el-tabs v-model="activeTab" class="finance-tabs" @tab-change="switchTab">
        <el-tab-pane label="开票登记" name="invoice" />
        <el-tab-pane label="回款登记" name="payment" />
        <el-tab-pane label="发票记录" name="invoice-records" />
        <el-tab-pane label="回款记录" name="payment-records" />
        <el-tab-pane label="台账" name="ledger" />
      </el-tabs>
    </section>

    <section v-if="activeTab === 'invoice'" class="panel">
      <div class="panel-head">
        <div>
          <h2>开票登记</h2>
          <p>上传发票后自动识别票面字段；合同额度按不含税金额累计校验。</p>
        </div>
        <span class="badge info">{{ invoiceRecognizing ? '识别中' : '发票 OCR' }}</span>
      </div>

      <div class="form-grid compact">
        <label>
          发票号码
          <el-input v-model="invoice.invoice_no" placeholder="全局唯一" />
        </label>
        <label>
          不含税金额
          <el-input v-model="invoice.amount_without_tax" placeholder="例如 4800000.00" />
        </label>
        <label>
          税率（%）
          <el-input v-model="invoice.tax_rate" placeholder="例如 8" />
        </label>
        <label>
          税额
          <el-input v-model="invoice.tax_amount" placeholder="例如 384000.00" />
        </label>
        <label>
          价税合计
          <el-input v-model="invoice.amount" placeholder="例如 5184000.00" />
        </label>
        <label>
          开票日期
          <el-date-picker v-model="invoice.invoice_date" value-format="YYYY-MM-DD" placeholder="开票日期" style="width: 100%" />
        </label>
        <label>
          发票类型
          <el-select v-model="invoice.invoice_type" style="width: 100%">
            <el-option label="增值税专票" value="special" />
            <el-option label="普通发票" value="normal" />
          </el-select>
        </label>
        <label>
          购方名称
          <el-input v-model="invoice.buyer" placeholder="购方名称" />
        </label>
        <label>
          销方名称
          <el-input v-model="invoice.seller" placeholder="销方名称" />
        </label>
        <label class="full">
          发票文件
          <el-upload ref="invoiceUploadRef" :auto-upload="false" :on-change="onInvoiceFile" :limit="1" :show-file-list="false">
            <el-button :loading="invoiceRecognizing">选择并识别发票</el-button>
          </el-upload>
          <span v-if="invoiceFileName" class="muted">已选择：{{ invoiceFileName }}</span>
          <el-button v-if="invoiceFileName" link type="danger" @click="clearInvoiceUpload">取消文件</el-button>
        </label>
      </div>

      <el-alert v-if="ocrStatus" :title="ocrStatus" type="info" :closable="false" style="margin-top: 12px" />
      <div class="rule-box">
        <div>
          <strong>金额规则</strong>
          <span>发票价税合计进入台账，回款累计不得超过项目累计开票价税合计。</span>
        </div>
      </div>
      <div class="form-actions">
        <el-button type="primary" :loading="invoiceSaving" :disabled="!canEditFinance || !selectedProjectId" @click="createInvoice">保存开票</el-button>
      </div>
    </section>

    <section v-if="activeTab === 'payment'" class="panel">
      <div class="panel-head">
        <div>
          <h2>回款登记</h2>
          <p>回款按项目登记，不再强制绑定单张发票；系统按项目累计开票价税合计做上限控制。</p>
        </div>
        <span class="badge info">{{ paymentRecognizing ? '识别中' : '回款 OCR' }}</span>
      </div>

      <div class="form-grid compact">
        <label>
          回款金额
          <el-input v-model="payment.amount" placeholder="回款金额" />
        </label>
        <label>
          回款日期
          <el-date-picker v-model="payment.payment_date" value-format="YYYY-MM-DD" placeholder="回款日期" style="width: 100%" />
        </label>
        <label class="full">
          回款方式
          <el-select v-model="payment.payment_method" style="width: 100%">
            <el-option label="银行转账" value="bank" />
            <el-option label="支票" value="check" />
            <el-option label="现金" value="cash" />
          </el-select>
        </label>
        <label class="full">
          回款凭证
          <el-upload ref="paymentUploadRef" :auto-upload="false" :on-change="onPaymentFile" :limit="1" :show-file-list="false">
            <el-button :loading="paymentRecognizing">选择并识别回款凭证</el-button>
          </el-upload>
          <span v-if="paymentFileName" class="muted">已选择：{{ paymentFileName }}</span>
          <el-button v-if="paymentFileName" link type="danger" @click="clearPaymentUpload">取消文件</el-button>
        </label>
        <label class="full">
          备注
          <el-input v-model="payment.remark" type="textarea" :rows="3" placeholder="流水号、付款方、收款方或其他说明" />
        </label>
      </div>

      <el-alert v-if="paymentOcrStatus" :title="paymentOcrStatus" type="info" :closable="false" style="margin-top: 12px" />
      <div class="rule-box">
        <div>
          <strong>回款规则</strong>
          <span>项目累计回款 + 本次回款不能超过项目累计开票价税合计。</span>
        </div>
      </div>
      <div class="form-actions">
        <el-button type="primary" :loading="paymentSaving" :disabled="!canEditFinance || !selectedProjectId" @click="createPayment">保存回款</el-button>
      </div>
    </section>

    <section v-if="activeTab === 'invoice-records'" class="panel">
      <div class="panel-head">
        <h2>发票记录</h2>
        <span class="badge info">{{ invoices.length }} 条</span>
      </div>
      <el-table :data="invoices" empty-text="暂无发票记录">
        <el-table-column prop="invoice_no" label="发票号码" min-width="140" />
        <el-table-column label="不含税金额" width="130">
          <template #default="{ row }">{{ money(row.amount_without_tax) }}</template>
        </el-table-column>
        <el-table-column label="税率" width="90">
          <template #default="{ row }">{{ row.tax_rate ? `${row.tax_rate}%` : '-' }}</template>
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
        <el-table-column v-if="canEditFinance" label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="deleteInvoice(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section v-if="activeTab === 'payment-records'" class="panel">
      <div class="panel-head">
        <h2>回款记录</h2>
        <span class="badge info">{{ payments.length }} 条</span>
      </div>
      <el-table :data="payments" empty-text="暂无回款记录">
        <el-table-column prop="invoice_label" label="历史发票关联" min-width="140" />
        <el-table-column label="回款金额" width="130">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="payment_date" label="回款日期" width="120" />
        <el-table-column prop="payment_method" label="方式" width="100" />
        <el-table-column label="凭证" width="100">
          <template #default="{ row }">{{ row.voucher_file ? '已上传' : '未上传' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column v-if="canEditFinance" label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="deletePayment(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section v-if="activeTab === 'ledger'" class="panel">
      <div class="panel-head">
        <div>
          <h2>台账</h2>
          <p>按项目汇总合同、开票、回款和未回款金额。</p>
        </div>
        <span class="badge danger">未回款 {{ money(summary.unpaid_amount) }}</span>
      </div>
      <el-empty v-if="!summary.project_id" description="请选择项目查看台账" />
      <template v-else>
        <el-alert v-if="summary.ledger_warning" :title="summary.ledger_warning" type="warning" :closable="false" style="margin-bottom: 12px" />
        <div class="receivable-grid">
          <div><span>合同金额</span><strong>{{ money(summary.contract_amount) }}</strong></div>
          <div><span>累计开票价税合计</span><strong>{{ money(summary.invoice_total_tax_included || summary.invoiced_amount) }}</strong></div>
          <div><span>累计开票不含税</span><strong>{{ money(summary.invoiced_without_tax_amount) }}</strong></div>
          <div><span>累计回款</span><strong>{{ money(summary.payment_total || summary.paid_amount) }}</strong></div>
          <div><span>未回款金额</span><strong>{{ money(summary.unpaid_amount) }}</strong></div>
          <div><span>剩余可开票</span><strong>{{ money(summary.remaining_invoice_amount) }}</strong></div>
        </div>
        <div class="progress-stack">
          <div>
            <span>开票进度 {{ summary.invoice_progress || 0 }}%</span>
            <i :style="{ '--w': `${summary.invoice_progress || 0}%` }"></i>
          </div>
          <div>
            <span>回款进度 {{ summary.payment_progress || 0 }}%</span>
            <i :style="{ '--w': `${summary.payment_progress || 0}%` }"></i>
          </div>
        </div>
        <el-table :data="summary.ledger_rows || []" empty-text="暂无台账记录" style="margin-top: 14px">
          <el-table-column prop="date" label="日期" width="130" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">{{ row.type === 'invoice' ? '开票' : '回款' }}</template>
          </el-table-column>
          <el-table-column prop="no" label="编号/关联" min-width="150" />
          <el-table-column label="金额" width="140">
            <template #default="{ row }">{{ money(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="180" />
        </el-table>
      </template>
    </section>

    <el-dialog v-model="detailVisible" title="立项申请详情" width="860px">
      <el-skeleton v-if="detailLoading" :rows="6" animated />
      <template v-else-if="projectDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目编号">{{ projectDetail.project.project_no }}</el-descriptions-item>
          <el-descriptions-item label="合同编号">{{ projectDetail.project.contract_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ projectDetail.project.name }}</el-descriptions-item>
          <el-descriptions-item label="项目状态">{{ projectDetail.project.display_status || projectDetail.project.status }}</el-descriptions-item>
          <el-descriptions-item label="甲方/客户">{{ projectDetail.project.party_a || projectDetail.project.customer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="乙方">{{ projectDetail.project.party_b || '-' }}</el-descriptions-item>
          <el-descriptions-item label="合同金额">{{ money(projectDetail.project.amount) }}</el-descriptions-item>
          <el-descriptions-item label="签订日期">{{ projectDetail.project.sign_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="项目类型">{{ projectDetail.project.project_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="项目说明" :span="2">{{ projectDetail.project.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const FINANCE_PROJECT_KEY = 'finance.currentProjectId'
const validTabs = new Set(['invoice', 'payment', 'invoice-records', 'payment-records', 'ledger'])

const activeTab = ref(validTabs.has(String(route.query.tab)) ? String(route.query.tab) : 'invoice')
const selectedProjectId = ref<number | string>('')
const projectOptions = ref<any[]>([])
const projectSearching = ref(false)
const invoices = ref<any[]>([])
const payments = ref<any[]>([])
const invoiceFile = ref<any>(null)
const paymentFile = ref<any>(null)
const invoiceUploadRef = ref<any>(null)
const paymentUploadRef = ref<any>(null)
const invoiceFileName = ref('')
const paymentFileName = ref('')
const ocrStatus = ref('')
const paymentOcrStatus = ref('')
const invoiceRecognizing = ref(false)
const paymentRecognizing = ref(false)
const invoiceSaving = ref(false)
const paymentSaving = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const projectDetail = ref<any>(null)

const invoice = reactive({
  invoice_no: '',
  amount: '',
  amount_without_tax: '',
  tax_rate: '',
  tax_amount: '',
  invoice_date: '',
  invoice_type: 'special',
  buyer: '',
  seller: '',
})
const payment = reactive({ amount: '', payment_date: '', payment_method: 'bank', remark: '' })
const summary = reactive<any>({
  project_id: null,
  contract_amount: 0,
  invoiced_amount: 0,
  invoice_total_tax_included: 0,
  invoiced_without_tax_amount: 0,
  paid_amount: 0,
  payment_total: 0,
  receivable: 0,
  unpaid_amount: 0,
  remaining_invoice_amount: 0,
  invoice_progress: 0,
  payment_progress: 0,
  ledger_rows: [],
})

const canEditFinance = computed(() => ['finance', 'admin'].includes(auth.user?.role || ''))

watch(() => route.query.tab, (tab) => {
  const next = validTabs.has(String(tab)) ? String(tab) : 'invoice'
  activeTab.value = next
})

async function searchProjects(keyword = '') {
  projectSearching.value = true
  try {
    const res: any = await http.get('/project/options', { params: { usage: 'invoice', keyword } })
    projectOptions.value = res.data || []
  } finally {
    projectSearching.value = false
  }
}

async function switchTab(name: any) {
  activeTab.value = String(name)
  await router.replace({ path: '/invoice', query: { tab: activeTab.value } })
}

async function onProjectChange(projectId: number | string) {
  if (!projectId) {
    clearFinanceData()
    return
  }
  localStorage.setItem(FINANCE_PROJECT_KEY, String(projectId))
  await refreshFinance(projectId)
}

async function refreshFinance(projectId?: number | string) {
  const id = projectId || selectedProjectId.value
  if (!id) return
  const [summaryRes, invoiceRes, paymentRes]: any[] = await Promise.all([
    http.get('/finance/summary', { params: { project_id: id } }),
    http.get('/invoice/list', { params: { project_id: id, page_size: 100 } }),
    http.get('/payment/list', { params: { project_id: id, page_size: 100 } }),
  ])
  Object.assign(summary, summaryRes.data || {})
  invoices.value = invoiceRes.data.items || []
  payments.value = paymentRes.data.items || []
}

function clearFinanceData() {
  Object.assign(summary, {
    project_id: null,
    contract_amount: 0,
    invoiced_amount: 0,
    invoice_total_tax_included: 0,
    invoiced_without_tax_amount: 0,
    paid_amount: 0,
    payment_total: 0,
    receivable: 0,
    unpaid_amount: 0,
    remaining_invoice_amount: 0,
    invoice_progress: 0,
    payment_progress: 0,
    ledger_rows: [],
  })
  invoices.value = []
  payments.value = []
}

async function onInvoiceFile(upload: any) {
  invoiceFile.value = upload.raw
  invoiceFileName.value = upload.name || upload.raw?.name || ''
  if (invoiceFile.value) await recognizeInvoice()
}

async function onPaymentFile(upload: any) {
  paymentFile.value = upload.raw
  paymentFileName.value = upload.name || upload.raw?.name || ''
  if (paymentFile.value) await recognizePayment()
}

async function recognizeInvoice() {
  if (!invoiceFile.value) return
  invoiceRecognizing.value = true
  ocrStatus.value = '正在识别发票...'
  try {
    const data = new FormData()
    data.append('file', invoiceFile.value)
    const res: any = await http.post('/ocr/invoice', data)
    const extracted = res.data.extracted_info || {}
    invoice.invoice_no = extracted.invoice_no || invoice.invoice_no
    invoice.amount = extracted.amount || invoice.amount
    invoice.amount_without_tax = extracted.amount_without_tax || invoice.amount_without_tax
    invoice.tax_rate = extracted.tax_rate || invoice.tax_rate
    invoice.tax_amount = extracted.tax_amount || invoice.tax_amount
    invoice.invoice_date = extracted.invoice_date || invoice.invoice_date
    invoice.buyer = extracted.buyer || invoice.buyer
    invoice.seller = extracted.seller || invoice.seller
    ocrStatus.value = res.data.status === 'success' ? '识别成功，已回填可识别字段' : `识别失败或置信度不足，请手动填写${res.data.error_message ? `：${res.data.error_message}` : ''}`
  } finally {
    invoiceRecognizing.value = false
  }
}

async function recognizePayment() {
  if (!paymentFile.value) return
  paymentRecognizing.value = true
  paymentOcrStatus.value = '正在识别回款凭证...'
  try {
    const data = new FormData()
    data.append('file', paymentFile.value)
    const res: any = await http.post('/ocr/payment', data)
    const extracted = res.data.extracted_info || {}
    if (res.data.status === 'manual_required' && !extracted.amount) {
      const candidates = extracted.amount_candidates?.length ? `，候选金额：${extracted.amount_candidates.join('、')}` : ''
      paymentOcrStatus.value = `${extracted.amount_warning || '未能可靠定位本次回款金额，请人工确认'}${candidates}`
      return
    }
    payment.amount = extracted.amount || payment.amount
    payment.payment_date = extracted.payment_date || payment.payment_date
    payment.remark = extracted.remark || payment.remark
    paymentOcrStatus.value = res.data.status === 'success' ? '识别成功，已回填可识别字段' : `识别失败或置信度不足，请手动填写${res.data.error_message ? `：${res.data.error_message}` : ''}`
  } finally {
    paymentRecognizing.value = false
  }
}

async function createInvoice() {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  invoiceSaving.value = true
  try {
    const data = new FormData()
    data.append('project_id', String(selectedProjectId.value))
    appendForm(data, invoice)
    if (invoiceFile.value) data.append('invoice_file', invoiceFile.value)
    await http.post('/invoice/create', data)
    ElMessage.success('开票登记成功')
    resetInvoiceForm()
    await refreshFinance()
    await switchTab('invoice-records')
  } finally {
    invoiceSaving.value = false
  }
}

async function createPayment() {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  paymentSaving.value = true
  try {
    const data = new FormData()
    data.append('project_id', String(selectedProjectId.value))
    appendForm(data, payment)
    if (paymentFile.value) data.append('voucher_file', paymentFile.value)
    await http.post('/payment/create', data)
    ElMessage.success('回款登记成功')
    resetPaymentForm()
    await refreshFinance()
    await switchTab('payment-records')
  } finally {
    paymentSaving.value = false
  }
}

async function deleteInvoice(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除发票 ${row.invoice_no}？如果删除后项目回款超过累计开票金额，系统会拒绝删除。`, '删除发票', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await http.delete(`/invoice/${row.id}`)
  ElMessage.success('发票已删除')
  await refreshFinance()
}

async function deletePayment(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除回款记录 ${money(row.amount)}？删除后可重新上传凭证登记。`, '删除回款', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await http.delete(`/payment/${row.id}`)
  ElMessage.success('回款已删除')
  await refreshFinance()
}

function clearInvoiceUpload() {
  invoiceFile.value = null
  invoiceFileName.value = ''
  ocrStatus.value = ''
  invoiceUploadRef.value?.clearFiles?.()
  resetInvoiceForm(false)
}

function clearPaymentUpload() {
  paymentFile.value = null
  paymentFileName.value = ''
  paymentOcrStatus.value = ''
  paymentUploadRef.value?.clearFiles?.()
  resetPaymentForm(false)
}

function resetInvoiceForm(clearFile = true) {
  Object.assign(invoice, { invoice_no: '', amount: '', amount_without_tax: '', tax_rate: '', tax_amount: '', invoice_date: '', invoice_type: 'special', buyer: '', seller: '' })
  if (clearFile) {
    invoiceFile.value = null
    invoiceFileName.value = ''
    ocrStatus.value = ''
    invoiceUploadRef.value?.clearFiles?.()
  }
}

function resetPaymentForm(clearFile = true) {
  Object.assign(payment, { amount: '', payment_date: '', payment_method: 'bank', remark: '' })
  if (clearFile) {
    paymentFile.value = null
    paymentFileName.value = ''
    paymentOcrStatus.value = ''
    paymentUploadRef.value?.clearFiles?.()
  }
}

async function openProjectDetail(projectId: number | string) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const res: any = await http.get('/project/detail', { params: { project_id: projectId } })
    projectDetail.value = res.data
  } finally {
    detailLoading.value = false
  }
}

function appendForm(data: FormData, source: Record<string, any>) {
  Object.entries(source).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') data.append(key, String(value))
  })
}

function projectLabel(project: any) {
  return `${project.project_no} / ${project.contract_no || '无合同编号'} / ${project.name} / ${project.party_a || project.customer || '无客户'}`
}

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

onMounted(async () => {
  await searchProjects('')
  const projectId = localStorage.getItem(FINANCE_PROJECT_KEY)
  if (projectId && projectOptions.value.some((project) => String(project.id) === projectId)) {
    selectedProjectId.value = Number(projectId)
    await refreshFinance(projectId)
  }
})
</script>

<style scoped>
.finance-toolbar {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) auto auto;
  gap: 10px;
  align-items: center;
}
</style>
