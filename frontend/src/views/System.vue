<template>
  <section class="page-grid">
    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <h2>用户管理</h2>
          <el-button type="primary" @click="openCreate">新增用户</el-button>
        </div>
        <el-table :data="users" empty-text="暂无用户">
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column label="角色" width="100">
            <template #default="{ row }">{{ roleText(row.role) }}</template>
          </el-table-column>
          <el-table-column prop="dept" label="部门" width="120" />
          <el-table-column prop="phone" label="手机号" width="130" />
          <el-table-column prop="email" label="邮箱" min-width="160" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                {{ row.status === 1 ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link @click="openEdit(row)">编辑</el-button>
              <el-button link :type="row.status === 1 ? 'warning' : 'success'" @click="toggleStatus(row)">
                {{ row.status === 1 ? '禁用' : '启用' }}
              </el-button>
              <el-button link type="danger" @click="deleteUser(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>审批流配置</h2>
          <span class="badge">RBAC</span>
        </div>
        <div class="approval-template">
          <div v-for="template in templates" :key="template.id">
            <strong>{{ template.template_name }}</strong>
            <span>{{ businessTypeText(template.business_type) }}</span>
            <small>{{ template.nodes.map((node: any) => `${node.node_order}.${node.node_name}/${node.timeout_hours}小时`).join(' -> ') || '暂无节点' }}</small>
          </div>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h2>数据字典</h2>
        <el-button @click="load">刷新</el-button>
      </div>
      <div class="dict-grid">
        <span v-for="group in dictGroups" :key="group.type">{{ group.type }}：{{ group.items.join('、') }}</span>
      </div>
      <el-empty v-if="!dictGroups.length" description="暂无字典数据" />
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>PaddleOCR 服务状态</h2>
          <p>{{ ocrHealthText }}</p>
        </div>
        <span class="status" :class="ocrHealthClass">{{ ocrHealthStatus }}</span>
      </div>
      <div v-if="ocrHealth" class="dict-grid">
        <span>服务地址：{{ ocrHealth.service.url }}</span>
        <span>健康检查：{{ ocrHealth.service.health_url }}</span>
        <span>模型加载：{{ ocrHealth.service.model_loaded ? '已加载' : '未加载' }}</span>
        <span v-if="ocrHealth.service.error">服务错误：{{ ocrHealth.service.error }}</span>
        <span v-if="ocrHealth.service.load_error">模型错误：{{ ocrHealth.service.load_error }}</span>
        <span v-if="ocrHealth.latest_log">最近识别：{{ ocrHealth.latest_log.status }} / {{ ocrHealth.latest_log.file_name || '-' }}</span>
      </div>
      <el-empty v-else description="暂无 OCR 健康状态" />
    </section>

    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <h2>审计日志</h2>
        </div>
        <el-table :data="logs" empty-text="暂无审计日志">
          <el-table-column prop="create_time" label="时间" min-width="170" />
          <el-table-column prop="username" label="用户" />
          <el-table-column prop="action" label="动作" />
          <el-table-column prop="content" label="内容" min-width="220" />
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>OCR 日志</h2>
        </div>
        <el-table :data="ocrLogs" empty-text="暂无 OCR 日志">
          <el-table-column prop="file_name" label="文件" />
          <el-table-column prop="recognition_type" label="类型" width="90" />
          <el-table-column prop="engine" label="引擎" width="100" />
          <el-table-column label="置信度" width="100">
            <template #default="{ row }">{{ row.confidence == null ? '-' : `${Math.round(row.confidence * 100)}%` }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
        </el-table>
      </section>
    </div>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px" destroy-on-close>
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="userForm.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" required>
          <el-input v-model="userForm.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="userForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" required>
          <el-input v-model="userForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="userForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="商务" value="business" />
            <el-option label="财务" value="finance" />
            <el-option label="项目经理" value="pm" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="userForm.dept" placeholder="请输入部门" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitUser">确定</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http } from '../api/http'
import { roleNames, type Role } from '../stores/auth'

const users = ref<any[]>([])
const dicts = ref<any[]>([])
const templates = ref<any[]>([])
const logs = ref<any[]>([])
const ocrLogs = ref<any[]>([])
const ocrHealth = ref<any>(null)

// 用户表单
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editingUserId = ref<number | null>(null)
const userForm = reactive({
  username: '',
  password: '',
  name: '',
  phone: '',
  email: '',
  role: '',
  dept: '',
})

const dictGroups = computed(() => {
  const groups: Record<string, string[]> = {}
  dicts.value.forEach((item) => {
    if (!groups[item.dict_type]) groups[item.dict_type] = []
    groups[item.dict_type].push(item.dict_name)
  })
  return Object.entries(groups).map(([type, items]) => ({ type, items }))
})

const ocrHealthStatus = computed(() => {
  if (!ocrHealth.value) return '未知'
  if (!ocrHealth.value.service.reachable) return '服务不可达'
  if (ocrHealth.value.latest_log?.status === 'failed') return '最近识别失败'
  if (!ocrHealth.value.service.model_loaded) return '服务可达'
  return '正常'
})

const ocrHealthClass = computed(() => {
  if (!ocrHealth.value?.service?.reachable) return 'danger'
  if (ocrHealth.value.latest_log?.status === 'failed') return 'warn'
  return 'ok'
})

const ocrHealthText = computed(() => {
  if (!ocrHealth.value) return '正在读取服务健康状态'
  if (!ocrHealth.value.service.reachable) return 'PaddleOCR HTTP 服务不可达，请检查容器状态'
  if (ocrHealth.value.service.load_error) return '服务可达，但模型加载存在错误'
  if (ocrHealth.value.latest_log?.status === 'failed') return '服务可达，但最近一次识别失败，请查看 OCR 日志'
  return '服务可达，OCR 日志用于展示识别历史'
})

function roleText(role: Role) {
  return roleNames[role] || role
}

function businessTypeText(type: string) {
  return ({ project: '立项审批', invoice: '开票审批', close: '结项审批' } as Record<string, string>)[type] || type
}

// 用户管理
function openCreate() {
  isEdit.value = false
  editingUserId.value = null
  Object.assign(userForm, { username: '', password: '', name: '', phone: '', email: '', role: '', dept: '' })
  dialogVisible.value = true
}

function openEdit(row: any) {
  isEdit.value = true
  editingUserId.value = row.id
  Object.assign(userForm, {
    username: row.username,
    password: '',
    name: row.name || '',
    phone: row.phone || '',
    email: row.email || '',
    role: row.role || '',
    dept: row.dept || '',
  })
  dialogVisible.value = true
}

async function submitUser() {
  if (!userForm.username || !userForm.name || !userForm.phone || !userForm.role) {
    ElMessage.warning('请填写必填项')
    return
  }
  if (!isEdit.value && !userForm.password) {
    ElMessage.warning('请输入密码')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await http.put('/user/update', {
        user_id: editingUserId.value,
        name: userForm.name,
        phone: userForm.phone,
        email: userForm.email || undefined,
        role: userForm.role,
        dept: userForm.dept || undefined,
      })
      ElMessage.success('用户更新成功')
    } else {
      await http.post('/user/create', {
        username: userForm.username,
        password: userForm.password,
        name: userForm.name,
        phone: userForm.phone,
        email: userForm.email || undefined,
        role: userForm.role,
        dept: userForm.dept || undefined,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    await loadUsers()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row: any) {
  const action = row.status === 1 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${action}用户 ${row.name}？`, '提示', { type: 'warning' })
  } catch { return }
  await http.put(`/user/${row.id}/status`)
  ElMessage.success(`已${action}`)
  await loadUsers()
}

async function deleteUser(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除用户 ${row.name}？此操作不可恢复。`, '删除用户', { type: 'error', confirmButtonText: '删除' })
  } catch { return }
  await http.delete(`/user/${row.id}`)
  ElMessage.success('用户已删除')
  await loadUsers()
}

async function loadUsers() {
  const res: any = await http.get('/user/list')
  users.value = res.data
}

async function load() {
  const [dictRes, templateRes, logRes, ocrRes, healthRes]: any[] = await Promise.all([
    http.get('/system/dicts'),
    http.get('/approval/template/list'),
    http.get('/system/logs'),
    http.get('/system/ocr-logs'),
    http.get('/system/ocr-health')
  ])
  dicts.value = dictRes.data
  templates.value = templateRes.data
  logs.value = logRes.data.items
  ocrLogs.value = ocrRes.data.items
  ocrHealth.value = healthRes.data
}

onMounted(async () => {
  await Promise.all([loadUsers(), load()])
})
</script>
