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
const ocrHealth = ref<any>(null)

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

async function load() {
  const [userRes, dictRes, templateRes, logRes, ocrRes, healthRes]: any[] = await Promise.all([
    http.get('/user/list'),
    http.get('/system/dicts'),
    http.get('/approval/template/list'),
    http.get('/system/logs'),
    http.get('/system/ocr-logs'),
    http.get('/system/ocr-health')
  ])
  users.value = userRes.data
  dicts.value = dictRes.data
  templates.value = templateRes.data
  logs.value = logRes.data.items
  ocrLogs.value = ocrRes.data.items
  ocrHealth.value = healthRes.data
}

onMounted(load)
</script>
