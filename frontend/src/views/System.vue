<template>
  <section class="page-grid">
    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <h2>用户管理</h2>
          <el-button type="primary" disabled>新增用户</el-button>
        </div>
        <el-table :data="users" empty-text="暂无用户">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="name" label="姓名" />
          <el-table-column label="角色">
            <template #default="{ row }">{{ roleText(row.role) }}</template>
          </el-table-column>
          <el-table-column prop="dept" label="部门" />
          <el-table-column label="状态">
            <template #default="{ row }">
              <span class="status" :class="row.status === 1 ? 'ok' : 'muted'">{{ row.status === 1 ? '启用' : '禁用' }}</span>
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
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '../api/http'
import { roleNames, type Role } from '../stores/auth'

const users = ref<any[]>([])
const dicts = ref<any[]>([])
const templates = ref<any[]>([])
const logs = ref<any[]>([])
const ocrLogs = ref<any[]>([])

const dictGroups = computed(() => {
  const groups: Record<string, string[]> = {}
  dicts.value.forEach((item) => {
    if (!groups[item.dict_type]) groups[item.dict_type] = []
    groups[item.dict_type].push(item.dict_name)
  })
  return Object.entries(groups).map(([type, items]) => ({ type, items }))
})

function roleText(role: Role) {
  return roleNames[role] || role
}

function businessTypeText(type: string) {
  return ({ project: '立项审批', invoice: '开票审批', close: '结项审批' } as Record<string, string>)[type] || type
}

async function load() {
  const [userRes, dictRes, templateRes, logRes, ocrRes]: any[] = await Promise.all([
    http.get('/user/list'),
    http.get('/system/dicts'),
    http.get('/approval/template/list'),
    http.get('/system/logs'),
    http.get('/system/ocr-logs')
  ])
  users.value = userRes.data
  dicts.value = dictRes.data
  templates.value = templateRes.data
  logs.value = logRes.data
  ocrLogs.value = ocrRes.data
}

onMounted(load)
</script>
