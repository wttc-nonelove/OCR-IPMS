<template>
  <section class="page-grid">
    <div class="content-grid">
      <section v-if="auth.user?.role === 'pm'" class="panel">
        <div class="panel-head">
          <div>
            <h2>结项申请</h2>
            <p>选择真实可结项项目，记录结项时间并提交财务审批</p>
          </div>
          <span class="badge info">验收材料</span>
        </div>
        <div class="form-grid compact">
          <label class="full">
            项目
            <el-select v-model="form.project_id" placeholder="选择已立项/进行中项目" style="width: 100%">
              <el-option v-for="project in projectOptions" :key="project.id" :label="`${project.project_no} ${project.name}`" :value="project.id" />
            </el-select>
          </label>
          <label>
            结项时间
            <el-date-picker v-model="form.close_time" value-format="YYYY-MM-DD" placeholder="结项时间" style="width: 100%" />
          </label>
          <label class="full">
            验收报告
            <el-upload :auto-upload="false" :on-change="onReportFile" :limit="1" :show-file-list="false">
              <el-button>选择验收报告</el-button>
            </el-upload>
            <span v-if="reportFileName" class="muted">已选择：{{ reportFileName }}</span>
            <el-button v-if="reportFileName" link type="danger" @click="clearReportFile">清除</el-button>
          </label>
          <label class="full">
            其他附件
            <el-upload :auto-upload="false" :on-change="onAttachmentFile" :limit="1" :show-file-list="false">
              <el-button>选择其他附件</el-button>
            </el-upload>
            <span v-if="attachmentFileName" class="muted">已选择：{{ attachmentFileName }}</span>
            <el-button v-if="attachmentFileName" link type="danger" @click="clearAttachmentFile">清除</el-button>
          </label>
          <label class="full">
            结项说明
            <el-input v-model="form.description" type="textarea" :rows="4" placeholder="项目已完成交付并通过客户验收" />
          </label>
        </div>
        <div class="form-actions">
          <el-button type="primary" @click="apply">提交结项审批</el-button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>结项审批链路</h2>
          <span class="badge">依次审批</span>
        </div>
        <ol class="approval-flow">
          <li class="done">
            <strong>项目经理提交</strong>
            <span>记录结项时间、上传验收报告、填写说明</span>
          </li>
          <li class="current">
            <strong>财务审核</strong>
            <span>确认开票、回款、应收款和尾款状态</span>
          </li>
          <li>
            <strong>已结项</strong>
            <span>财务审批通过后项目只读，不允许继续开票</span>
          </li>
        </ol>
      </section>
    </div>

    <section v-if="auth.user?.role === 'finance' || auth.user?.role === 'admin'" class="panel">
      <div class="panel-head">
        <div>
          <h2>我的审批任务</h2>
          <p>待办直接来自 approval_task，不使用通知或消息表</p>
        </div>
      </div>
      <el-table :data="tasks" empty-text="暂无审批待办">
        <el-table-column prop="business_type" label="类型" width="100" />
        <el-table-column prop="project_no" label="项目编号" />
        <el-table-column prop="title" label="业务标题" />
        <el-table-column prop="node_name" label="节点" />
        <el-table-column prop="start_by" label="申请人" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button link @click="processTask(row.id, 'approved')">通过</el-button>
            <el-button link type="danger" @click="processTask(row.id, 'rejected')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>结项列表</h2>
          <p>财务审批通过后项目状态变为已结项；管理员可撤回到进行中</p>
        </div>
      </div>
      <el-table :data="items" empty-text="暂无结项申请">
        <el-table-column prop="project_no" label="项目编号" />
        <el-table-column prop="project_name" label="项目名称" />
        <el-table-column prop="close_time" label="结项时间" />
        <el-table-column prop="balance_status" label="尾款状态" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <span class="status" :class="row.status === 'closed' ? 'ok' : row.status === 'rejected' ? 'danger' : 'warn'">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="auth.user?.role === 'admin' && row.status === 'closed'" link @click="withdraw(row)">撤回</el-button>
            <el-button link @click="$router.push('/project')">查看项目</el-button>
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
const items = ref<any[]>([])
const tasks = ref<any[]>([])
const projectOptions = ref<any[]>([])
const reportFile = ref<any>(null)
const attachmentFile = ref<any>(null)
const reportFileName = ref('')
const attachmentFileName = ref('')
const form = reactive({ project_id: '', close_time: '', description: '' })

function onReportFile(upload: any) {
  reportFile.value = upload.raw
  reportFileName.value = upload.name || upload.raw?.name || ''
}

function onAttachmentFile(upload: any) {
  attachmentFile.value = upload.raw
  attachmentFileName.value = upload.name || upload.raw?.name || ''
}

function clearReportFile() {
  reportFile.value = null
  reportFileName.value = ''
}

function clearAttachmentFile() {
  attachmentFile.value = null
  attachmentFileName.value = ''
}

async function loadProjects() {
  const res: any = await http.get('/project/options', { params: { usage: 'close' } })
  projectOptions.value = res.data
}

async function load() {
  const [closeRes, taskRes]: any[] = await Promise.all([http.get('/close/list'), http.get('/approval/task/list')])
  items.value = closeRes.data
  tasks.value = taskRes.data.filter((task: any) => task.business_type === 'close')
}

async function apply() {
  const data = new FormData()
  Object.entries(form).forEach(([k, v]) => data.append(k, String(v)))
  if (reportFile.value) data.append('report_file', reportFile.value)
  if (attachmentFile.value) data.append('attachment', attachmentFile.value)
  await http.post('/close/apply', data)
  ElMessage.success('已提交')
  Object.assign(form, { project_id: '', close_time: '', description: '' })
  clearReportFile()
  clearAttachmentFile()
  await Promise.all([load(), loadProjects()])
}

async function processTask(taskId: number, result: 'approved' | 'rejected') {
  await http.post('/approval/process', { task_id: taskId, result, opinion: result === 'approved' ? '同意' : '驳回' })
  ElMessage.success('审批完成')
  await Promise.all([load(), loadProjects()])
}

async function withdraw(row: any) {
  await http.post('/close/withdraw', { project_id: row.project_id, reason: '管理员撤回结项' })
  ElMessage.success('已撤回')
  await Promise.all([load(), loadProjects()])
}

onMounted(async () => {
  await Promise.all([load(), loadProjects()])
})
</script>
