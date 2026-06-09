<template>
  <section class="page-grid">
    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>开票登记</h2>
            <p>上传发票后自动识别票面字段，合同额度按不含税金额校验</p>
          </div>
          <span class="badge info">{{ invoiceRecognizing ? '识别中' : '自动识别' }}</span>
        </div>

        <div class="form-grid compact">
          <label class="full">
            关联项目
            <el-select v-model="invoice.project_id" filterable placeholder="选择已立项/进行中项目" style="width: 100%" @change="onInvoiceProjectChange">
              <el-option v-for="project in invoiceProjectOptions" :key="project.id" :label="projectLabel(project)" :value="project.id" />
            </el-select>
          </label>
          <label>
            发票号码
            <el-input v-model="invoice.invoice_no" placeholder="全局唯一" />
          </label>
          <label>
            不含税金额
            <el-input v-model="invoice.amount_without_tax" placeholder="发票金额栏" />
          </label>
          <label>
            税率（%）
            <el-input v-model="invoice.tax_rate" placeholder="如 13" />
          </label>
          <label>
            税额
            <el-input v-model="invoice.tax_amount" placeholder="发票税额栏" />
          </label>
          <label>
            价税合计
            <el-input v-model="invoice.amount" placeholder="发票价税合计" />
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
          <label>
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
            <strong>金额校验</strong>
            <span>不含税金额累计不得超过合同金额；价税合计作为票面总额保存和展示。</span>
          </div>
        </div>
        <div class="form-actions">
          <el-button type="primary" :loading="invoiceSaving" @click="createInvoice">保存开票</el-button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>回款登记</h2>
          <span class="badge">绑定单张发票</span>
        </div>
        <div class="form-grid compact">
          <label class="full">
            关联项目
            <el-select v-model="payment.project_id" filterable placeholder="选择已有发票的项目" style="width: 100%" @change="onPaymentProjectChange">
              <el-option v-for="project in paymentProjectOptions" :key="project.id" :label="projectLabel(project)" :value="project.id" />
            </el-select>
          </label>
          <label class="full">
            关联发票
            <el-select v-model="payment.invoice_id" filterable placeholder="选择发票" style="width: 100%">
              <el-option v-for="item in invoices" :key="item.id" :label="`${item.invoice_no} / 价税合计 ${money(item.amount)}`" :value="item.id" />
            </el-select>
          </label>
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
            <strong>回款校验</strong>
            <span>单张发票累计回款不能超过该发票价税合计。</span>
          </div>
        </div>
        <div class="form-actions">
          <el-button type="primary" :loading="paymentSaving" @click="createPayment">保存回款</el-button>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>应收款计算</h2>
          <p>剩余可开票按不含税累计额计算，累计开票展示票面价税合计。</p>
        </div>
        <span class="badge danger">应收 {{ money(summary.receivable) }}</span>
        <span v-if="summary.project_id" class="badge" :class="summary.is_payment_complete ? 'ok' : 'danger'">{{ summary.payment_status_label }}</span>
        <el-button v-if="summary.project_id" size="small" @click="openProjectDetail(summary.project_id)">查看立项详情</el-button>
      </div>
      <el-empty v-if="!summary.project_id" description="请选择项目查看财务汇总" />
      <template v-else>
        <div class="receivable-grid">
          <div>
            <span>合同金额</span>
            <strong>{{ money(summary.contract_amount) }}</strong>
          </div>
          <div>
            <span>累计开票（价税合计）</span>
            <strong>{{ money(summary.invoiced_amount) }}</strong>
          </div>
          <div>
            <span>累计开票（不含税）</span>
            <strong>{{ money(summary.invoiced_without_tax_amount) }}</strong>
          </div>
          <div>
            <span>剩余可开票</span>
            <strong>{{ money(summary.remaining_invoice_amount) }}</strong>
          </div>
        </div>
        <div class="progress-stack">
          <div>
            <span>开票进度 {{ summary.invoice_progress }}%</span>
            <i :style="{ '--w': `${summary.invoice_progress || 0}%` }"></i>
          </div>
          <div>
            <span>回款进度 {{ summary.payment_progress }}%</span>
            <i :style="{ '--w': `${summary.payment_progress || 0}%` }"></i>
          </div>
        </div>
      </template>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>发票与回款记录</h2>
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
        <el-table-column prop="buyer" label="购方" min-width="150" />
        <el-table-column prop="seller" label="销方" min-width="150" />
        <el-table-column v-if="auth.user?.role === 'finance'" label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="deleteInvoice(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table :data="payments" empty-text="暂无回款记录" style="margin-top: 16px">
        <el-table-column prop="invoice_no" label="关联发票" min-width="140" />
        <el-table-column label="回款金额" width="130">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="payment_date" label="回款日期" width="120" />
        <el-table-column prop="payment_method" label="方式" width="100" />
        <el-table-column label="凭证" width="100">
          <template #default="{ row }">{{ row.voucher_file ? '已上传' : '未上传' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column v-if="auth.user?.role === 'finance'" label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="deletePayment(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
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

        <h3 class="dialog-section-title">合同差异</h3>
        <el-table :data="projectDetail.diffs" empty-text="暂无合同差异">
          <el-table-column prop="field_label" label="字段" width="130" />
          <el-table-column prop="registered_value" label="登记值" />
          <el-table-column prop="recognized_value" label="识别值" />
          <el-table-column prop="adopted_value" label="采用值" />
          <el-table-column prop="diff_status" label="状态" width="110" />
          <el-table-column prop="remark" label="备注" />
        </el-table>

        <h3 class="dialog-section-title">审批记录</h3>
        <el-table :data="projectDetail.approvals" empty-text="暂无审批记录">
          <el-table-column prop="business_type" label="类型" width="100" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="start_time" label="开始时间" />
        </el-table>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const invoiceProjectOptions = ref<any[]>([])
const paymentProjectOptions = ref<any[]>([])
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
const FINANCE_PROJECT_KEY = 'finance.currentProjectId'
const invoice = reactive({ project_id: '', invoice_no: '', amount: '', amount_without_tax: '', tax_rate: '', tax_amount: '', invoice_date: '', invoice_type: 'special', buyer: '', seller: '' })
const payment = reactive({ project_id: '', invoice_id: '', amount: '', payment_date: '', payment_method: 'bank', remark: '' })
const summary = reactive<any>({ project_id: null, contract_amount: 0, invoiced_amount: 0, invoiced_without_tax_amount: 0, paid_amount: 0, receivable: 0, remaining_invoice_amount: 0, invoice_progress: 0, payment_progress: 0 })

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

async function loadOptions() {
  const [invoiceRes, paymentRes]: any[] = await Promise.all([
    http.get('/project/options', { params: { usage: 'invoice' } }),
    http.get('/project/options', { params: { usage: 'payment' } })
  ])
  invoiceProjectOptions.value = invoiceRes.data || []
  paymentProjectOptions.value = paymentRes.data || []
  restoreSelectedProject()
}

async function onInvoiceProjectChange(projectId: number) {
  rememberProject(projectId)
  if (paymentProjectOptions.value.some((project) => String(project.id) === String(projectId))) {
    ;(payment as any).project_id = projectId
  }
  await refreshFinance(projectId)
}

async function onPaymentProjectChange(projectId: number) {
  rememberProject(projectId)
  if (invoiceProjectOptions.value.some((project) => String(project.id) === String(projectId))) {
    ;(invoice as any).project_id = projectId
  }
  payment.invoice_id = ''
  await refreshFinance(projectId)
}

async function refreshFinance(projectId?: number | string) {
  const id = projectId || invoice.project_id || payment.project_id
  if (!id) return
  rememberProject(id)
  const [summaryRes, invoiceRes, paymentRes]: any[] = await Promise.all([
    http.get('/finance/summary', { params: { project_id: id } }),
    http.get('/invoice/list', { params: { project_id: id, page_size: 100 } }),
    http.get('/payment/list', { params: { project_id: id, page_size: 100 } })
  ])
  Object.assign(summary, summaryRes.data || {})
  invoices.value = invoiceRes.data.items || []
  payments.value = paymentRes.data.items || []
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
    if (extracted.invoice_no) {
      const matched = invoices.value.find((item) => String(item.invoice_no) === String(extracted.invoice_no))
      if (matched) payment.invoice_id = matched.id
    }
    paymentOcrStatus.value = res.data.status === 'success' ? '识别成功，已回填可识别字段' : `识别失败或置信度不足，请手动填写${res.data.error_message ? `：${res.data.error_message}` : ''}`
  } finally {
    paymentRecognizing.value = false
  }
}

async function deleteInvoice(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除发票 ${row.invoice_no}？如果该发票存在回款，系统会拒绝删除。`, '删除发票', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await http.delete(`/invoice/${row.id}`)
  ElMessage.success('发票已删除')
  await loadOptions()
  await refreshFinance(row.project_id || invoice.project_id || payment.project_id)
}

async function deletePayment(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除回款记录 ${money(row.amount)}？删除后可重新上传凭证登记。`, '删除回款', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await http.delete(`/payment/${row.id}`)
  ElMessage.success('回款已删除')
  await loadOptions()
  await refreshFinance(row.project_id || invoice.project_id || payment.project_id)
}

function clearInvoiceUpload() {
  invoiceFile.value = null
  invoiceFileName.value = ''
  ocrStatus.value = ''
  invoiceUploadRef.value?.clearFiles?.()
  Object.assign(invoice, {
    project_id: invoice.project_id,
    invoice_no: '',
    amount: '',
    amount_without_tax: '',
    tax_rate: '',
    tax_amount: '',
    invoice_date: '',
    invoice_type: invoice.invoice_type || 'special',
    buyer: '',
    seller: ''
  })
}

function clearPaymentUpload() {
  paymentFile.value = null
  paymentFileName.value = ''
  paymentOcrStatus.value = ''
  paymentUploadRef.value?.clearFiles?.()
  Object.assign(payment, {
    project_id: payment.project_id,
    invoice_id: payment.invoice_id,
    amount: '',
    payment_date: '',
    payment_method: payment.payment_method || 'bank',
    remark: ''
  })
}

async function createInvoice() {
  invoiceSaving.value = true
  const projectId = invoice.project_id
  try {
    const data = new FormData()
    appendForm(data, invoice)
    if (invoiceFile.value) data.append('invoice_file', invoiceFile.value)
    await http.post('/invoice/create', data)
    ElMessage.success('开票登记成功')
    Object.assign(invoice, { project_id: projectId, invoice_no: '', amount: '', amount_without_tax: '', tax_rate: '', tax_amount: '', invoice_date: '', invoice_type: 'special', buyer: '', seller: '' })
    clearInvoiceUpload()
    ;(invoice as any).project_id = projectId
    rememberProject(projectId)
    await loadOptions()
    if (paymentProjectOptions.value.some((project) => String(project.id) === String(projectId))) {
      ;(payment as any).project_id = projectId
    }
    await refreshFinance(projectId)
  } finally {
    invoiceSaving.value = false
  }
}

async function createPayment() {
  paymentSaving.value = true
  const projectId = payment.project_id
  try {
    const data = new FormData()
    appendForm(data, payment)
    if (paymentFile.value) data.append('voucher_file', paymentFile.value)
    await http.post('/payment/create', data)
    ElMessage.success('回款登记成功')
    Object.assign(payment, { project_id: projectId, invoice_id: '', amount: '', payment_date: '', payment_method: 'bank', remark: '' })
    clearPaymentUpload()
    ;(payment as any).project_id = projectId
    rememberProject(projectId)
    await loadOptions()
    await refreshFinance(projectId)
  } finally {
    paymentSaving.value = false
  }
}

function projectLabel(project: any) {
  return `${project.project_no} / ${project.contract_no || '无合同编号'} / ${project.name} / ${project.party_a || project.customer || '无客户'}`
}

function appendForm(data: FormData, source: Record<string, any>) {
  Object.entries(source).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') data.append(key, String(value))
  })
}

function rememberProject(projectId?: number | string) {
  if (projectId) localStorage.setItem(FINANCE_PROJECT_KEY, String(projectId))
}

function restoreSelectedProject() {
  const projectId = localStorage.getItem(FINANCE_PROJECT_KEY)
  if (!projectId) return
  if (invoiceProjectOptions.value.some((project) => String(project.id) === projectId)) {
    ;(invoice as any).project_id = Number(projectId)
  }
  if (paymentProjectOptions.value.some((project) => String(project.id) === projectId)) {
    ;(payment as any).project_id = Number(projectId)
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

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

onMounted(async () => {
  await loadOptions()
  const projectId = localStorage.getItem(FINANCE_PROJECT_KEY)
  if (projectId && (invoice.project_id || payment.project_id)) {
    await refreshFinance(projectId)
  }
})
</script>
