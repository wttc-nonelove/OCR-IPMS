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
            <el-upload :auto-upload="false" :on-change="onInvoiceFile" :limit="1" :show-file-list="false">
              <el-button :loading="invoiceRecognizing">选择并识别发票</el-button>
            </el-upload>
            <span v-if="invoiceFileName" class="muted">已选择：{{ invoiceFileName }}</span>
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
            <el-upload :auto-upload="false" :on-change="onPaymentFile" :limit="1" :show-file-list="false">
              <el-button :loading="paymentRecognizing">选择并识别回款凭证</el-button>
            </el-upload>
            <span v-if="paymentFileName" class="muted">已选择：{{ paymentFileName }}</span>
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
      </el-table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'

const invoiceProjectOptions = ref<any[]>([])
const paymentProjectOptions = ref<any[]>([])
const invoices = ref<any[]>([])
const payments = ref<any[]>([])
const invoiceFile = ref<any>(null)
const paymentFile = ref<any>(null)
const invoiceFileName = ref('')
const paymentFileName = ref('')
const ocrStatus = ref('')
const paymentOcrStatus = ref('')
const invoiceRecognizing = ref(false)
const paymentRecognizing = ref(false)
const invoiceSaving = ref(false)
const paymentSaving = ref(false)
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
}

async function onInvoiceProjectChange(projectId: number) {
  await refreshFinance(projectId)
}

async function onPaymentProjectChange(projectId: number) {
  payment.invoice_id = ''
  await refreshFinance(projectId)
}

async function refreshFinance(projectId?: number | string) {
  const id = projectId || invoice.project_id || payment.project_id
  if (!id) return
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
    payment.amount = extracted.amount || payment.amount
    payment.payment_date = extracted.payment_date || payment.payment_date
    payment.remark = extracted.remark || payment.remark
    paymentOcrStatus.value = res.data.status === 'success' ? '识别成功，已回填可识别字段' : `识别失败或置信度不足，请手动填写${res.data.error_message ? `：${res.data.error_message}` : ''}`
  } finally {
    paymentRecognizing.value = false
  }
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
    invoiceFile.value = null
    invoiceFileName.value = ''
    ocrStatus.value = ''
    await loadOptions()
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
    paymentFile.value = null
    paymentFileName.value = ''
    paymentOcrStatus.value = ''
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

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

onMounted(loadOptions)
</script>
