<template>
  <section class="page-grid">
    <div class="content-grid">
      <section class="panel user-panel">
        <div class="panel-head">
          <div>
            <h2>用户管理</h2>
            <p>维护系统账号、角色与启用状态</p>
          </div>
          <el-button type="primary" @click="openCreate">新增用户</el-button>
        </div>

        <div class="user-stats">
          <div class="user-stat">
            <span>总用户</span>
            <strong>{{ userStats.total }}</strong>
          </div>
          <div class="user-stat is-enabled">
            <span>启用</span>
            <strong>{{ userStats.enabled }}</strong>
          </div>
          <div class="user-stat is-disabled">
            <span>禁用</span>
            <strong>{{ userStats.disabled }}</strong>
          </div>
          <div v-for="role in roleOptions" :key="role.value" class="user-stat">
            <span>{{ role.label }}</span>
            <strong>{{ userStats.roles[role.value] || 0 }}</strong>
          </div>
        </div>

        <div class="user-filters">
          <el-input
            v-model="userFilters.keyword"
            clearable
            placeholder="搜索用户名、姓名、部门、手机号、邮箱"
            @keyup.enter="loadUsers"
          />
          <el-select v-model="userFilters.role" clearable placeholder="全部角色">
            <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
          <el-select v-model="userFilters.status" clearable placeholder="全部状态">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
          <el-button :loading="loadingUsers" @click="loadUsers">查询</el-button>
          <el-button @click="resetUserFilters">重置</el-button>
        </div>

        <el-table
          v-loading="loadingUsers"
          :data="users"
          empty-text="暂无用户"
          :row-class-name="userRowClass"
        >
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="name" label="姓名" min-width="100" />
          <el-table-column label="角色" width="110">
            <template #default="{ row }">
              <el-tag :type="roleTagType(row.role)" size="small">{{ roleText(row.role) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="dept" label="部门" min-width="120">
            <template #default="{ row }">{{ row.dept || '-' }}</template>
          </el-table-column>
          <el-table-column prop="phone" label="手机号" min-width="130" />
          <el-table-column prop="email" label="邮箱" min-width="170">
            <template #default="{ row }">{{ row.email || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light" size="small">
                {{ row.status === 1 ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="230" fixed="right">
            <template #default="{ row }">
              <el-button link @click="openEdit(row)">编辑</el-button>
              <el-tooltip :disabled="!isSelf(row)" content="不能禁用当前登录账号" placement="top">
                <span>
                  <el-button
                    link
                    :disabled="isSelf(row)"
                    :type="row.status === 1 ? 'warning' : 'success'"
                    @click="toggleStatus(row)"
                  >
                    {{ row.status === 1 ? '禁用' : '启用' }}
                  </el-button>
                </span>
              </el-tooltip>
              <el-tooltip :disabled="!isSelf(row)" content="不能删除当前登录账号" placement="top">
                <span>
                  <el-button link type="danger" :disabled="isSelf(row)" @click="deleteUser(row)">删除</el-button>
                </span>
              </el-tooltip>
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

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="560px"
      destroy-on-close
      @closed="resetUserForm"
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="88px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model.trim="userForm.username" :disabled="isEdit" placeholder="3-50位字母、数字或下划线" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model.trim="userForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="选择角色" style="width: 100%">
            <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门" prop="dept">
          <el-input v-model.trim="userForm.dept" placeholder="请输入部门" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model.trim="userForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model.trim="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitUser">
          {{ isEdit ? '保存修改' : '创建用户' }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { http } from '../api/http'
import { roleNames, type Role, useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const users = ref<any[]>([])
const dicts = ref<any[]>([])
const templates = ref<any[]>([])
const logs = ref<any[]>([])
const ocrLogs = ref<any[]>([])
const ocrHealth = ref<any>(null)

const roleOptions: Array<{ label: string; value: Role }> = [
  { label: '管理员', value: 'admin' },
  { label: '商务', value: 'business' },
  { label: '财务', value: 'finance' },
  { label: '项目经理', value: 'pm' },
]

const userFilters = reactive<{ keyword: string; role: Role | ''; status: number | '' }>({
  keyword: '',
  role: '',
  status: '',
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const loadingUsers = ref(false)
const editingUserId = ref<number | null>(null)
const userFormRef = ref<FormInstance>()
const userForm = reactive({
  username: '',
  password: '',
  name: '',
  phone: '',
  email: '',
  role: '' as Role | '',
  dept: '',
})

const userRules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]{3,50}$/, message: '用户名需为3-50位字母、数字或下划线', trigger: 'blur' },
  ],
  password: [
    {
      validator: (_rule, value, callback) => {
        if (isEdit.value) {
          callback()
          return
        }
        if (!value) {
          callback(new Error('请输入密码'))
          return
        }
        if (String(value).length < 6) {
          callback(new Error('密码至少6位'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^[0-9+\-\s]{6,20}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!value || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(value))) {
          callback()
          return
        }
        callback(new Error('邮箱格式不正确'))
      },
      trigger: 'blur',
    },
  ],
}))

const userStats = computed(() => {
  const roles: Record<string, number> = {}
  users.value.forEach((item) => {
    roles[item.role] = (roles[item.role] || 0) + 1
  })
  return {
    total: users.value.length,
    enabled: users.value.filter((item) => item.status === 1).length,
    disabled: users.value.filter((item) => item.status !== 1).length,
    roles,
  }
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

function roleTagType(role: Role) {
  return ({ admin: 'danger', business: 'primary', finance: 'success', pm: 'warning' } as Record<Role, string>)[role] || 'info'
}

function businessTypeText(type: string) {
  return ({ project: '立项审批', invoice: '开票审批', close: '结项审批' } as Record<string, string>)[type] || type
}

function isSelf(row: any) {
  return row.id === authStore.user?.id
}

function userRowClass({ row }: { row: any }) {
  return row.status === 1 ? '' : 'disabled-user-row'
}

function resetUserForm() {
  editingUserId.value = null
  Object.assign(userForm, { username: '', password: '', name: '', phone: '', email: '', role: '', dept: '' })
  userFormRef.value?.clearValidate()
}

function openCreate() {
  isEdit.value = false
  resetUserForm()
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
  if (!userFormRef.value) return
  const valid = await userFormRef.value.validate().catch(() => false)
  if (!valid) return
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
  if (isSelf(row)) {
    ElMessage.warning('不能禁用当前登录账号')
    return
  }
  const action = row.status === 1 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${action}用户 ${row.name || row.username}？`, '提示', { type: 'warning' })
  } catch { return }
  await http.put(`/user/${row.id}/status`)
  ElMessage.success(`已${action}`)
  await loadUsers()
}

async function deleteUser(row: any) {
  if (isSelf(row)) {
    ElMessage.warning('不能删除当前登录账号')
    return
  }
  try {
    await ElMessageBox.confirm(`确认删除用户 ${row.name || row.username}？此操作不可恢复。`, '删除用户', {
      type: 'error',
      confirmButtonText: '删除',
      confirmButtonClass: 'el-button--danger',
    })
  } catch { return }
  await http.delete(`/user/${row.id}`)
  ElMessage.success('用户已删除')
  await loadUsers()
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const res: any = await http.get('/user/list', {
      params: {
        keyword: userFilters.keyword || undefined,
        role: userFilters.role || undefined,
        status: userFilters.status === '' ? undefined : userFilters.status,
      },
    })
    users.value = res.data
  } finally {
    loadingUsers.value = false
  }
}

async function resetUserFilters() {
  Object.assign(userFilters, { keyword: '', role: '', status: '' })
  await loadUsers()
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

<style scoped>
.user-panel {
  min-width: 0;
}

.user-stats {
  display: grid;
  grid-template-columns: repeat(7, minmax(86px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.user-stat {
  min-height: 68px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface-2);
}

.user-stat span,
.user-stat strong {
  display: block;
}

.user-stat span {
  color: var(--muted);
  font-size: 12px;
}

.user-stat strong {
  margin-top: 8px;
  font-size: 22px;
  line-height: 1;
}

.user-stat.is-enabled {
  background: var(--green-soft);
}

.user-stat.is-disabled {
  background: #f1f5f9;
}

.user-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 140px 140px auto auto;
  gap: 10px;
  margin-bottom: 14px;
}

:deep(.disabled-user-row) {
  color: #8a94a6;
  background: #f8fafc;
}

@media (max-width: 1180px) {
  .user-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .user-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .user-stats,
  .user-filters {
    grid-template-columns: 1fr;
  }
}
</style>
