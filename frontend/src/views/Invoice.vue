<template>
  <section class="page-grid">
    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>开票登记</h2>
            <p>选择真实项目，上传发票 PDF/图片后调用 OCR 回填字段</p>
          </div>
          <el-button :disabled="!invoiceFile" type="primary" @click="recognizeInvoice">识别发票</el-button>
        </div>

        <div class="form-grid compact">
          <label class="full">
            关联项目
            <el-select v-model="invoice.project_id" placeholder="选择已立项/进行中项目" style="width: 100%" @change="onProjectChange">
              <el-option v-for="project in projectOptions" :key="project.id" :label="`${project.project_no} ${project.name}`" :value="project.id" />
            </el-select>
          </label>
          <label>
            发票号码
            <el-input v-model="invoice.invoice_no" placeholder="全局唯一" />
          </label>
          <label>
            开票金额
            <el-input v-model="invoice.amount" placeholder="开票金额" />
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
            <el-upload :auto-upload="false" :on-change="onInvoiceFile" :limit="1">
              <el-button>选择 PDF/图片</el-button>
            </el-upload>
          </label>
        </div>

        <el-alert v-if="ocrStatus" :title="ocrStatus" type="info" :closable="false" style="margin-top: 12px" />
        <div class="rule-box">
          <div>
            <strong>金额锁策略</strong>
            <span>事务内锁定项目，累计开票金额不能超过合同金额；达到 80% 自动创建审批实例。</span>
          </div>
        </div>
        <div class="form-actions">
          <el-button type="primary" @click="createInvoice">保存开票</el-button>
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
            <el-select v-model="payment.project_id" placeholder="选择项目" style="width: 100%" @change="onPaymentProjectChange">
              <el-option v-for="project in projectOptions" :key="project.id" :label="`${project.project_no} ${project.name}`" :value="project.id" />
            </el-select>
          </label>
          <label class="full">
            关联发票
            <el-select v-model="payment.invoice_id" placeholder="选择发票" style="width: 100%">
              <el-option v-for="item in invoices" :key="item.id" :label="`${item.invoice_no} / ${money(item.amount)}`" :value="item.id" />
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
        </div>
        <div class="rule-box">
          <div>
            <strong>回款校验</strong>
            <span>事务内锁定发票，单张发票累计回款不能超过该发票金额。</span>
          </div>
        </div>
        <div class="form-actions">
          <el-button type="primary" @click="createPayment">保存回款</el-button>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>应收款计算</h2>
          <p>选择项目后显示真实合同金额、开票、回款和应收余额</p>
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
            <span>累计开票</span>
            <strong>{{ money(summary.invoiced_amount) }}</strong>
          </div>
          <div>
            <span>累计回款</span>
            <strong>{{ money(summary.paid_amount) }}</strong>
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
        <el-table-column prop="invoice_no" label="发票号码" />
        <el-table-column label="金额">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="invoice_date" label="开票日期" />
        <el-table-column prop="buyer" label="购方" />
        <el-table-column prop="seller" label="销方" />
      </el-table>
      <el-table :data="payments" empty-text="暂无回款记录" style="margin-top: 16px">
        <el-table-column prop="invoice_id" label="发票ID" />
        <el-table-column label="回款金额">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="payment_date" label="回款日期" />
        <el-table-column prop="payment_method" label="方式" />
      </el-table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'

const projectOptions = ref<any[]>([])
const invoices = ref<any[]>([])
const payments = ref<any[]>([])
const invoiceFile = ref<any>(null)
const ocrStatus = ref('')
const invoice = reactive({ project_id: '', invoice_no: '', amount: '', invoice_date: '', invoice_type: 'special', buyer: '', seller: '' })
const payment = reactive({ project_id: '', invoice_id: '', amount: '', payment_date: '', payment_method: 'bank' })
const summary = reactive<any>({ project_id: null, contract_amount: 0, invoiced_amount: 0, paid_amount: 0, receivable: 0, remaining_invoice_amount: 0, invoice_progress: 0, payment_progress: 0 })

function onInvoiceFile(upload: any) {
  invoiceFile.value = upload.raw
}

async function loadOptions() {
  const res: any = await http.get('/project/options', { params: { usage: 'invoice' } })
  projectOptions.value = res.data
}

async function onProjectChange(projectId: number) {
  payment.project_id = String(projectId)
  await refreshFinance(projectId)
}

async function onPaymentProjectChange(projectId: number) {
  invoice.project_id = String(projectId)
  await refreshFinance(projectId)
}

async function refreshFinance(projectId?: number | string) {
  const id = projectId || invoice.project_id || payment.project_id
  if (!id) return
  const [summaryRes, invoiceRes, paymentRes]: any[] = await Promise.all([
    http.get('/finance/summary', { params: { project_id: id } }),
    http.get('/invoice/list', { params: { project_id: id } }),
    http.get('/payment/list', { params: { project_id: id } })
  ])
  Object.assign(summary, summaryRes.data || {})
  invoices.value = invoiceRes.data
  payments.value = paymentRes.data
}

async function recognizeInvoice() {
  if (!invoiceFile.value) return
  const data = new FormData()
  data.append('file', invoiceFile.value)
  const res: any = await http.post('/ocr/invoice', data)
  const extracted = res.data.extracted_info || {}
  invoice.invoice_no = extracted.invoice_no || invoice.invoice_no
  invoice.amount = extracted.amount || invoice.amount
  invoice.invoice_date = extracted.invoice_date || invoice.invoice_date
  invoice.buyer = extracted.buyer || invoice.buyer
  invoice.seller = extracted.seller || invoice.seller
  ocrStatus.value = res.data.status === 'success' ? '识别成功，已回填可识别字段' : '识别失败或置信度不足，请手动填写'
}

async function createInvoice() {
  const data = new FormData()
  Object.entries(invoice).forEach(([k, v]) => data.append(k, String(v)))
  if (invoiceFile.value) data.append('invoice_file', invoiceFile.value)
  await http.post('/invoice/create', data)
  ElMessage.success('开票登记成功')
  await refreshFinance(invoice.project_id)
}

async function createPayment() {
  const data = new FormData()
  Object.entries(payment).forEach(([k, v]) => data.append(k, String(v)))
  await http.post('/payment/create', data)
  ElMessage.success('回款登记成功')
  await refreshFinance(payment.project_id)
}

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

onMounted(loadOptions)
</script>
