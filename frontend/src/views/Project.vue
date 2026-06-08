<template>
  <section class="page-grid">
    <div class="content-grid project-grid">
      <section v-if="auth.user?.role === 'business'" class="panel">
        <div class="panel-head">
          <div>
            <h2>立项草稿</h2>
            <p>Word 上传后自动解析并保存到后端草稿；刷新页面后自动恢复</p>
          </div>
          <span class="badge">{{ form.project_no || nextNo || '编号加载中' }}</span>
        </div>

        <div class="upload-strip">
          <div>
            <strong>Word 合同附件</strong>
            <span>.doc / .docx 选择后立即解析，识别不到的字段可手动补充</span>
          </div>
          <el-upload :auto-upload="false" :on-change="onWordFile" :limit="1" :show-file-list="false">
            <el-button type="primary" :loading="parsingWord">选择并解析 Word</el-button>
          </el-upload>
        </div>

        <el-alert v-if="parseMessage" :title="parseMessage" :type="parseAlertType" :closable="false" style="margin-bottom: 14px" />

        <div class="form-grid">
          <label>
            项目名称
            <el-input v-model="form.name" placeholder="项目名称" />
          </label>
          <label>
            甲方/客户
            <el-input v-model="form.party_a" placeholder="合同甲方、委托方或采购方" />
          </label>
          <label>
            乙方
            <el-input v-model="form.party_b" placeholder="合同乙方、承包方或服务方" />
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
          <label class="full">
            项目类型
            <el-select
              v-model="form.project_type"
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入合同中的项目类型"
              style="width: 100%"
            >
              <el-option v-for="item in projectTypes" :key="item.dict_code" :label="item.dict_name" :value="item.dict_code" />
            </el-select>
          </label>
        </div>

        <div class="form-actions">
          <span class="muted">{{ saveStatus }}</span>
          <el-button @click="newDraft">新建空白草稿</el-button>
          <el-button type="primary" :loading="saving" @click="saveDraft(true)">保存草稿</el-button>
        </div>
      </section>

      <section v-if="auth.user?.role === 'business' || auth.user?.role === 'admin'" class="panel">
        <div class="panel-head">
          <h2>盖章合同差异生成</h2>
          <span class="badge info">PDF/图片 OCR</span>
        </div>
        <el-select v-model="selectedProjectId" placeholder="选择项目" style="width: 100%; margin-bottom: 12px" @change="loadDiffs">
          <el-option v-for="project in projects" :key="project.id" :label="`${project.project_no} ${project.name}`" :value="project.id" />
        </el-select>
        <el-upload :auto-upload="false" :on-change="onPdfFile" :limit="1" :show-file-list="false">
          <el-button :loading="parsingPdf">选择并解析 PDF/图片合同</el-button>
        </el-upload>
        <el-alert v-if="pdfMessage" :title="pdfMessage" type="info" :closable="false" style="margin-top: 12px" />
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
          <p>支持按编号、名称、甲方/客户、状态筛选；项目经理可查看所有项目</p>
        </div>
        <div class="filter-row">
          <el-input v-model="keyword" placeholder="项目名称 / 编号 / 甲方" style="width: 240px" />
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
        <el-table-column prop="party_a" label="甲方/客户" min-width="160" />
        <el-table-column prop="party_b" label="乙方" min-width="160" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">{{ money(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status" :class="statusClass(row.status)">{{ statusText(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'draft' && auth.user?.role === 'business'" link @click="editDraft(row)">编辑草稿</el-button>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const projects = ref<any[]>([])
const diffs = ref<any[]>([])
const projectTypes = ref<any[]>([])
const keyword = ref('')
const status = ref('')
const nextNo = ref('')
const selectedProjectId = ref<number | null>(null)
const parsingWord = ref(false)
const parsingPdf = ref(false)
const saving = ref(false)
const saveStatus = ref('')
const parseMessage = ref('')
const pdfMessage = ref('')
const suppressAutoSave = ref(false)
const form = reactive<any>({
  id: null,
  project_no: '',
  name: '',
  party_a: '',
  party_b: '',
  amount: '',
  contract_no: '',
  sign_date: '',
  project_type: 'software'
})

const parseAlertType = computed(() => (parseMessage.value.includes('失败') || parseMessage.value.includes('补充') ? 'warning' : 'success'))

async function onWordFile(upload: UploadFile) {
  if (!upload.raw) return
  parsingWord.value = true
  parseMessage.value = '正在解析 Word 合同...'
  try {
    const data = new FormData()
    data.append('word_contract', upload.raw)
    if (form.id) data.append('draft_id', String(form.id))
    const res: any = await http.post('/project/word/parse-draft', data)
    applyProject(res.data.project)
    await loadProjectTypes()
    const missing = res.data.missing_fields || []
    parseMessage.value = missing.length ? `解析完成，请补充：${missing.join('、')}` : '解析成功，已自动回填并保存草稿'
    selectedProjectId.value = form.id
    await Promise.all([load(), loadDiffs()])
  } finally {
    parsingWord.value = false
  }
}

async function onPdfFile(upload: UploadFile) {
  if (!upload.raw) return
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }
  parsingPdf.value = true
  pdfMessage.value = '正在解析 PDF/图片合同...'
  try {
    const data = new FormData()
    data.append('project_id', String(selectedProjectId.value))
    data.append('pdf_contract', upload.raw)
    const res: any = await http.post('/project/stamped-contract/parse', data)
    diffs.value = res.data.diffs || []
    pdfMessage.value = diffs.value.length ? `识别完成，生成 ${diffs.value.length} 条差异` : '识别完成，未发现差异'
    await load()
  } finally {
    parsingPdf.value = false
  }
}

async function loadNextNo() {
  const res: any = await http.get('/project/next-no')
  nextNo.value = res.data.project_no
}

async function loadProjectTypes() {
  const res: any = await http.get('/system/dicts', { params: { dict_type: 'project_type' } })
  projectTypes.value = res.data
}

async function loadCurrentDraft() {
  if (auth.user?.role !== 'business') return
  const res: any = await http.get('/project/draft/current')
  if (res.data?.project) {
    applyProject(res.data.project)
    selectedProjectId.value = form.id
    parseMessage.value = '已恢复最近未提交草稿'
  }
}

async function load() {
  const res: any = await http.get('/project/list', { params: { keyword: keyword.value || undefined, status: status.value || undefined } })
  projects.value = res.data.map((item: any) => ({ ...item, party_a: item.party_a || item.customer }))
}

async function saveDraft(showMessage = false) {
  if (auth.user?.role !== 'business') return
  if (!hasDraftContent()) return
  saving.value = true
  try {
    const data = new FormData()
    if (form.id) data.append('project_id', String(form.id))
    appendIfPresent(data, 'name', form.name)
    appendIfPresent(data, 'party_a', form.party_a)
    appendIfPresent(data, 'party_b', form.party_b)
    appendIfPresent(data, 'amount', form.amount)
    appendIfPresent(data, 'contract_no', form.contract_no)
    appendIfPresent(data, 'sign_date', form.sign_date)
    appendIfPresent(data, 'project_type', form.project_type)
    const res: any = await http.post('/project/draft/save', data)
    applyProject(res.data.project)
    await Promise.all([load(), loadProjectTypes()])
    saveStatus.value = `已保存 ${new Date().toLocaleTimeString()}`
    if (showMessage) ElMessage.success('草稿已保存')
  } finally {
    saving.value = false
  }
}

async function newDraft() {
  suppressAutoSave.value = true
  Object.assign(form, { id: null, project_no: nextNo.value, name: '', party_a: '', party_b: '', amount: '', contract_no: '', sign_date: '', project_type: 'software' })
  selectedProjectId.value = null
  diffs.value = []
  parseMessage.value = ''
  saveStatus.value = ''
  suppressAutoSave.value = false
}

async function editDraft(row: any) {
  applyProject(row)
  selectedProjectId.value = row.id
  parseMessage.value = '已载入草稿'
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
  await Promise.all([loadDiffs(), load()])
}

async function submit(id: number) {
  if (form.id === id) await saveDraft(false)
  await http.post('/project/submit', null, { params: { project_id: id } })
  ElMessage.success('已提交审核')
  await newDraft()
  await Promise.all([load(), loadNextNo()])
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

function appendIfPresent(data: FormData, key: string, value: any) {
  if (value !== undefined && value !== null && value !== '') data.append(key, String(value))
}

function applyProject(project: any) {
  suppressAutoSave.value = true
  Object.assign(form, {
    id: project.id,
    project_no: project.project_no,
    name: project.name || '',
    party_a: project.party_a || project.customer || '',
    party_b: project.party_b || '',
    amount: project.amount ? String(project.amount) : '',
    contract_no: project.contract_no || '',
    sign_date: project.sign_date || '',
    project_type: project.project_type || 'software'
  })
  suppressAutoSave.value = false
}

function hasDraftContent() {
  return Boolean(form.id || form.name || form.party_a || form.party_b || form.amount || form.contract_no)
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

let saveTimer: number | undefined
watch(
  () => ({ name: form.name, party_a: form.party_a, party_b: form.party_b, amount: form.amount, contract_no: form.contract_no, sign_date: form.sign_date, project_type: form.project_type }),
  () => {
    if (suppressAutoSave.value || auth.user?.role !== 'business') return
    window.clearTimeout(saveTimer)
    saveStatus.value = '等待自动保存...'
    saveTimer = window.setTimeout(() => saveDraft(false), 900)
  },
  { deep: true }
)

onMounted(async () => {
  await Promise.all([load(), loadNextNo(), loadProjectTypes()])
  await loadCurrentDraft()
})
</script>
