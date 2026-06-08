<template>
  <main class="login-page">
    <section class="login-card">
      <div class="login-copy">
        <div class="brand-mark">PM</div>
        <h1>智能项目管理系统</h1>
        <p>选择身份登录后，系统会按 RBAC 权限只展示该身份可访问的功能。默认账号已预置，适合直接演示完整业务闭环。</p>
      </div>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户身份">
          <el-select v-model="selected" style="width: 100%" @change="syncUser">
            <el-option label="管理员" value="admin" />
            <el-option label="商务" value="business" />
            <el-option label="财务" value="finance" />
            <el-option label="项目经理" value="pm" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">登录进入系统</el-button>
      </el-form>

      <div class="login-role-grid">
        <button
          v-for="role in roleCards"
          :key="role.value"
          type="button"
          class="login-role"
          :class="{ active: selected === role.value }"
          @click="chooseRole(role.value)"
        >
          <strong>{{ role.label }}</strong>
          <span>{{ role.desc }}</span>
        </button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore, type Role } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const selected = ref<Role>('admin')
const username = ref('admin')
const password = ref('123456')
const loading = ref(false)
const users: Record<Role, string> = { admin: 'admin', business: 'business01', finance: 'finance01', pm: 'pm01' }
const roleCards: Array<{ value: Role; label: string; desc: string }> = [
  { value: 'admin', label: '管理员', desc: '立项审核、项目启动、系统配置、全量查询' },
  { value: 'business', label: '商务', desc: '合同解析、立项登记、差异确认、提交审批' },
  { value: 'finance', label: '财务', desc: '发票识别、开票登记、回款登记、结项审批' },
  { value: 'pm', label: '项目经理', desc: '项目跟踪、验收报告、结项申请、材料补充' }
]

function syncUser(role: Role) {
  username.value = users[role]
}

function chooseRole(role: Role) {
  selected.value = role
  syncUser(role)
}

async function submit() {
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
