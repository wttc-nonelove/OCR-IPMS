<template>
  <section class="page-grid">
    <div class="content-grid project-grid">
      <section v-if="auth.user?.role === 'business'" class="panel">
        <div class="panel-head">
          <div>
            <h2>立项前登记</h2>
            <p>上传 Word 合同后创建真实项目草稿，合同解析结果写入 OCR 日志</p>
          </div>
          <span class="badge">{{ nextNo || '编号加载中' }}</span>
        </div>

        <div class="upload-strip">
          <div>
            <strong>Word 合同附件</strong>
            <span>.doc / .docx 走文档解析；PDF/图片在项目更新时走 OCR 并生成差异</span>
          </div>
          <el-upload :auto-upload="false" :on-change="onWordFile" :limit="1">
            <el-button type="primary">选择 Word 合同</el-button>
          </el-upload>
        </div>

        <div class="form-grid">
          <label>
            项目名称
            <el-input v-model="form.name" placeholder="项目名称" />
          </label>
          <label>
            客户名称
            <el-input v-model="form.customer" placeholder="客户公司名称" />
          </label>
          <label>
            合同金额
            <el-input v-model="form.amount" placeholder="合同金额" />
          </label>
          <label>
            合同编号
            <el-input v-model="form.contract_no" placeholder="合同编号" />
          </label>
          <label>
            签订日期
            <el-date-picker v-model="form.sign_date" value-format="YYYY-MM-DD" placeholder="签订日期" style="width: 100%" />
          </label>
          <label>
            项目类型
            <el-select v-model="form.project_type" style="width: 100%">
              <el-option label="软件开发" value="software" />
              <el-option label="系统集成" value="integration" />
              <el-option label="咨询服务" value="consulting" />
            </el-select>
          </label>
        </div>

        <div class="form-actions">
          <el-button type="primary" @click="createProject">创建草稿</el-button>
        </div>
      </section>

      <section v-if="auth.user?.role === 'business' || auth.user?.role === 'admin'" class="panel">
        <div class="panel-head">
          <h2>盖章合同差异生成</h2>
          <span class="badge info">真实项目</span>
        </div>
        <el-select v-model="selectedProjectId" placeholder="选择项目" style="width: 100%; margin-bottom: 12px" @change="loadDiffs">
          <el-option v-for="project in projects" :key="project.id" :label="`${project.project_no} ${project.name}`" :value="project.id" />
        </el-select>
        <el-upload :auto-upload="false" :on-change="onPdfFile" :limit="1">
          <el-button>选择 PDF/图片合同</el-button>
        </el-upload>
        <div class="form-actions">
          <el-button :disabled="!selectedProjectId || !pdfFile" type="primary" @click="uploadStampedContract">上传并生成差异</el-button>
        </div>
      </section>
    </div>

    <section v-if="auth.user?.role === 'business' || auth.user?.role === 'admin'" class="panel">
      <div class="panel-head">
        <div>
          <h2>合同差异确认</h2>
          <p>差异、人工采用值、确认人、确认时间和备注均来自数据库</p>
        </div>
        <span class="badge info">{{ diffs.length }} 条</span>
      </div>
      <el-empty v-if="!selectedProjectId" description="请先选择项目" />
      <el-table v-else :data="diffs" empty-text="暂无合同差异">
        <el-table-column prop="field_label" label="字段" />
        <el-table-column prop="registered_value" label="登记值" />
        <el-table-column prop="recognized_value" label="识别值" />
        <el-table-column label="人工采用值" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.adopted_value" placeholder="采用值" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.remark" placeholder="备注" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status" :class="row.diff_status === 'confirmed' ? 'ok' : 'warn'">{{ row.diff_status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link @click="confirmDiff(row)">确认</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>项目列表</h2>
          <p>支持按编号、名称、客户、状态筛选；项目经理可查看所有项目</p>
        </div>
        <div class="filter-row">
          <el-input v-model="keyword" placeholder="项目名称 / 编号 / 客户" style="width: 240px" />
          <el-select v-model="status" clearable placeholder="状态" style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="待审核" value="pending" />
            <el-option label="已立项" value="approved" />
            <el-option label="进行中" value="active" />
            <el-option label="已结项" value="closed" />
          </el-select>
          <el-button @click="load">查询</el-button>
        </div>
      </div>

      <el-table :data="projects" empty-text="暂无项目">
        <el-table-column prop="project_no" label="项目编号" min-width="140" />
        <el-table-column prop="name" label="项目名称" min-width="180" />
        <el-table-column prop="customer" label="客户" min-width="160" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status" :class="statusClass(row.status)">{{ statusText(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'draft' && auth.user?.role === 'business'" link @click="submit(row.id)">提交审核</el-button>
            <el-button v-if="row.status === 'pending' && auth.user?.role === 'admin'" link @click="approve(row.id)">审核通过</el-button>
            <el-button v-if="row.status === 'approved' && auth.user?.role === 'admin'" link @click="start(row.id)">确认开始</el-button>
            <el-button link @click="selectProject(row.id)">查看差异</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const projects = ref<any[]>([])
const diffs = ref<any[]>([])
const keyword = ref('')
const status = ref('')
const nextNo = ref('')
const selectedProjectId = ref<number | null>(null)
const wordFile = ref<any>(null)
const pdfFile = ref<any>(null)
const form = reactive({ name: '', customer: '', amount: '', contract_no: '', sign_date: '', project_type: 'software' })

function onWordFile(upload: any) {
  wordFile.value = upload.raw
}

function onPdfFile(upload: any) {
  pdfFile.value = upload.raw
}

async function loadNextNo() {
  const res: any = await http.get('/project/next-no')
  nextNo.value = res.data.project_no
}

async function load() {
  const res: any = await http.get('/project/list', { params: { keyword: keyword.value || undefined, status: status.value || undefined } })
  projects.value = res.data
}

async function createProject() {
  const data = new FormData()
  Object.entries(form).forEach(([k, v]) => {
    if (v !== '') data.append(k, String(v))
  })
  if (wordFile.value) data.append('word_contract', wordFile.value)
  await http.post('/project/create', data)
  ElMessage.success('创建成功')
  Object.assign(form, { name: '', customer: '', amount: '', contract_no: '', sign_date: '', project_type: 'software' })
  wordFile.value = null
  await Promise.all([load(), loadNextNo()])
}

async function uploadStampedContract() {
  if (!selectedProjectId.value || !pdfFile.value) return
  const data = new FormData()
  data.append('project_id', String(selectedProjectId.value))
  data.append('pdf_contract', pdfFile.value)
  await http.post('/project/update', data)
  ElMessage.success('已生成合同差异')
  pdfFile.value = null
  await loadDiffs()
}

async function selectProject(id: number) {
  selectedProjectId.value = id
  await loadDiffs()
}

async function loadDiffs() {
  if (!selectedProjectId.value) return
  const res: any = await http.get('/project/diff/list', { params: { project_id: selectedProjectId.value } })
  diffs.value = res.data
}

async function confirmDiff(row: any) {
  await http.post('/project/contract-diff/confirm', {
    diff_id: row.id,
    adopted_value: row.adopted_value || row.recognized_value || row.registered_value,
    diff_status: 'confirmed',
    remark: row.remark || ''
  })
  ElMessage.success('差异已确认')
  await loadDiffs()
}

async function submit(id: number) {
  await http.post('/project/submit', null, { params: { project_id: id } })
  ElMessage.success('已提交审核')
  await load()
}

async function approve(id: number) {
  await http.post('/project/approve', { project_id: id, result: 'approved' })
  ElMessage.success('审核通过')
  await load()
}

async function start(id: number) {
  await http.post('/project/start', { project_id: id })
  ElMessage.success('项目已进入进行中')
  await load()
}

function money(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN')}`
}

function statusText(value: string) {
  return ({ draft: '草稿', pending: '待审核', approved: '已立项', active: '进行中', closed: '已结项' } as Record<string, string>)[value] || value
}

function statusClass(value: string) {
  return ({ draft: 'muted', pending: 'warn', approved: 'ok', active: 'info', closed: 'muted' } as Record<string, string>)[value] || ''
}

onMounted(async () => {
  await Promise.all([load(), loadNextNo()])
})
</script>
