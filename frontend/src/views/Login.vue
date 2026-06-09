<template>
  <main class="login-page">
    <canvas ref="canvasRef" class="login-canvas" aria-hidden="true" role="presentation"></canvas>
    <div class="sky-glow" aria-hidden="true">
      <span class="moon"></span>
      <span class="halo halo-a"></span>
      <span class="halo halo-b"></span>
    </div>
    <div class="star-layer" aria-hidden="true"></div>
    <div class="meteor-layer" aria-hidden="true">
      <span class="meteor meteor-a"></span>
      <span class="meteor meteor-b"></span>
      <span class="meteor meteor-c"></span>
    </div>
    <div class="login-grid" aria-hidden="true"></div>
    <div class="cloud-layer" aria-hidden="true">
      <span class="cloud cloud-a"></span>
      <span class="cloud cloud-b"></span>
      <span class="cloud cloud-c"></span>
      <span class="cloud cloud-d"></span>
      <span class="cloud cloud-e"></span>
      <span class="cloud cloud-f"></span>
      <span class="cloud cloud-g"></span>
    </div>
    <div class="fog-bank" aria-hidden="true"></div>

    <section class="login-shell">
      <header class="login-brand">
        <div class="login-brand-mark">PRJ</div>
        <div>
          <h1>智能项目管理系统</h1>
          <p>合同识别、立项审批、开票回款与结项闭环管理</p>
        </div>
      </header>

      <section class="login-card">
        <div class="login-card-head">
          <span>Project Management Console</span>
          <h2>欢迎登录后台管理系统</h2>
        </div>

        <el-form class="login-form" label-position="top" @submit.prevent="submit">
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
          <el-button type="primary" native-type="submit" :loading="loading" class="login-submit">
            登录进入系统
          </el-button>
        </el-form>

        <div class="login-role-grid" role="group" aria-label="选择登录角色">
          <button
            v-for="role in roleCards"
            :key="role.value"
            type="button"
            class="login-role"
            :class="{ active: selected === role.value }"
            :aria-pressed="selected === role.value"
            :aria-label="`以${role.label}身份登录：${role.desc}`"
            @click="chooseRole(role.value)"
          >
            <strong>{{ role.label }}</strong>
            <span>{{ role.desc }}</span>
          </button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore, type Role } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const selected = ref<Role>('admin')
const username = ref('admin')
const password = ref('123456')
const loading = ref(false)
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationId = 0
let resizeHandler: (() => void) | null = null

const users: Record<Role, string> = { admin: 'admin', business: 'business01', finance: 'finance01', pm: 'pm01' }
const roleCards: Array<{ value: Role; label: string; desc: string }> = [
  { value: 'admin', label: '管理员', desc: '立项审核 / 项目启动 / 系统配置' },
  { value: 'business', label: '商务', desc: '合同解析 / 差异确认 / 提交审批' },
  { value: 'finance', label: '财务', desc: '发票识别 / 开票回款 / 结项审批' },
  { value: 'pm', label: '项目经理', desc: '项目跟踪 / 验收报告 / 结项申请' }
]

function syncUser(role: Role) {
  username.value = users[role]
}

function chooseRole(role: Role) {
  selected.value = role
  syncUser(role)
}

function startCanvas() {
  // Respect user's reduced motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const canvas = canvasRef.value
  if (!canvas) return
  const context = canvas.getContext('2d')
  if (!context) return

  const particles = Array.from({ length: 48 }, () => ({
    x: Math.random(),
    y: Math.random(),
    vx: (Math.random() - 0.5) * 0.00035,
    vy: (Math.random() - 0.5) * 0.00035,
    size: Math.random() * 1.4 + 0.6,
  }))

  const resize = () => {
    const ratio = window.devicePixelRatio || 1
    canvas.width = Math.floor(window.innerWidth * ratio)
    canvas.height = Math.floor(window.innerHeight * ratio)
    canvas.style.width = `${window.innerWidth}px`
    canvas.style.height = `${window.innerHeight}px`
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
  }

  const draw = () => {
    const width = window.innerWidth
    const height = window.innerHeight
    context.clearRect(0, 0, width, height)
    const sky = context.createLinearGradient(0, 0, 0, height)
    sky.addColorStop(0, '#061f45')
    sky.addColorStop(0.38, '#08152f')
    sky.addColorStop(0.74, '#040916')
    sky.addColorStop(1, '#02050c')
    context.fillStyle = sky
    context.fillRect(0, 0, width, height)

    for (const particle of particles) {
      particle.x += particle.vx
      particle.y += particle.vy
      if (particle.x < 0 || particle.x > 1) particle.vx *= -1
      if (particle.y < 0 || particle.y > 1) particle.vy *= -1
    }

    for (let i = 0; i < particles.length; i += 1) {
      const current = particles[i]
      const x = current.x * width
      const y = current.y * height
      context.beginPath()
      context.arc(x, y, current.size, 0, Math.PI * 2)
      context.fillStyle = 'rgba(123, 211, 255, 0.68)'
      context.fill()

      for (let j = i + 1; j < particles.length; j += 1) {
        const next = particles[j]
        const nx = next.x * width
        const ny = next.y * height
        const distance = Math.hypot(x - nx, y - ny)
        if (distance < 145) {
          context.beginPath()
          context.moveTo(x, y)
          context.lineTo(nx, ny)
          context.strokeStyle = `rgba(79, 189, 255, ${0.18 * (1 - distance / 145)})`
          context.lineWidth = 1
          context.stroke()
        }
      }
    }

    animationId = window.requestAnimationFrame(draw)
  }

  resizeHandler = resize
  window.addEventListener('resize', resize)
  resize()
  draw()
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

onMounted(startCanvas)

onUnmounted(() => {
  if (animationId) window.cancelAnimationFrame(animationId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  display: grid;
  place-items: center;
  padding: 28px;
  background: #02050c;
}

.login-canvas,
.sky-glow,
.star-layer,
.meteor-layer,
.login-grid,
.cloud-layer,
.fog-bank {
  position: absolute;
  inset: 0;
}

.login-canvas {
  z-index: 0;
}

.sky-glow {
  z-index: 1;
  pointer-events: none;
  background:
    radial-gradient(circle at 22% 18%, rgba(93, 189, 255, 0.34), transparent 24%),
    radial-gradient(circle at 70% 20%, rgba(77, 123, 255, 0.16), transparent 24%),
    linear-gradient(180deg, rgba(15, 80, 142, 0.16), transparent 58%);
}

.moon {
  position: absolute;
  top: 8%;
  right: 13%;
  width: 74px;
  height: 74px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 36% 32%, #ffffff 0 12px, transparent 13px),
    radial-gradient(circle at 63% 58%, rgba(213, 238, 255, 0.92) 0 8px, transparent 9px),
    linear-gradient(135deg, #ffffff, #dbeeff);
  box-shadow:
    0 0 28px rgba(205, 239, 255, 0.7),
    0 0 90px rgba(79, 178, 255, 0.42);
  opacity: 0.92;
}

.halo {
  position: absolute;
  border-radius: 50%;
  filter: blur(4px);
}

.halo-a {
  top: 5%;
  left: 7%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(74, 192, 255, 0.22), transparent 62%);
}

.halo-b {
  right: 4%;
  bottom: 6%;
  width: 360px;
  height: 260px;
  background: radial-gradient(circle, rgba(56, 114, 214, 0.22), transparent 66%);
}

.star-layer {
  z-index: 1;
  pointer-events: none;
  opacity: 0.72;
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.95) 0 1px, transparent 1.6px),
    radial-gradient(circle, rgba(152, 221, 255, 0.8) 0 1px, transparent 1.7px),
    radial-gradient(circle, rgba(255, 255, 255, 0.5) 0 1px, transparent 1.5px);
  background-position: 16px 28px, 90px 64px, 42px 116px;
  background-size: 150px 150px, 210px 210px, 260px 260px;
  animation: starTwinkle 5.6s ease-in-out infinite alternate;
}

.meteor-layer {
  z-index: 1;
  overflow: hidden;
  pointer-events: none;
}

.meteor {
  position: absolute;
  width: 170px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.96), rgba(100, 216, 255, 0.14));
  opacity: 0;
  transform: rotate(-18deg);
  animation: meteorFall 7s linear infinite;
}

.meteor-a {
  top: 16%;
  left: 56%;
  animation-delay: 0.8s;
}

.meteor-b {
  top: 28%;
  left: 74%;
  width: 130px;
  animation-duration: 9s;
  animation-delay: 4.2s;
}

.meteor-c {
  top: 10%;
  left: 34%;
  width: 120px;
  animation-duration: 8.4s;
  animation-delay: 6.1s;
}

.login-grid {
  z-index: 2;
  opacity: 0.16;
  background-image:
    linear-gradient(rgba(125, 214, 255, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(125, 214, 255, 0.12) 1px, transparent 1px);
  background-size: 64px 64px;
  mask-image: linear-gradient(180deg, transparent 0, black 20%, black 76%, transparent 100%);
}

.cloud-layer {
  z-index: 2;
  overflow: hidden;
  pointer-events: none;
}

.cloud {
  position: absolute;
  display: block;
  width: 210px;
  height: 72px;
  border-radius: 999px;
  background:
    radial-gradient(ellipse at 28% 30%, rgba(255, 255, 255, 1) 0 24px, transparent 42px),
    radial-gradient(ellipse at 48% 18%, rgba(255, 255, 255, 0.98) 0 40px, transparent 66px),
    radial-gradient(ellipse at 72% 34%, rgba(255, 255, 255, 0.96) 0 30px, transparent 52px),
    radial-gradient(ellipse at 52% 78%, rgba(184, 222, 244, 0.48), transparent 66%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(220, 240, 252, 0.9) 64%, rgba(148, 190, 218, 0.7));
  box-shadow:
    inset 16px 18px 26px rgba(255, 255, 255, 0.72),
    inset -18px -20px 30px rgba(93, 143, 178, 0.28),
    inset 0 -12px 18px rgba(80, 125, 158, 0.22),
    0 18px 26px rgba(11, 34, 62, 0.22),
    0 0 32px rgba(180, 230, 255, 0.18);
  filter: drop-shadow(0 12px 22px rgba(108, 173, 220, 0.22));
  opacity: 0.76;
  animation-name: cloudDrift;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

.cloud::before,
.cloud::after {
  content: "";
  position: absolute;
  border-radius: 50%;
  background:
    radial-gradient(circle at 36% 26%, rgba(255, 255, 255, 1), rgba(244, 251, 255, 0.98) 42%, rgba(174, 214, 238, 0.82) 100%);
  box-shadow:
    inset 14px 16px 20px rgba(255, 255, 255, 0.76),
    inset -12px -16px 22px rgba(92, 142, 176, 0.24),
    0 10px 18px rgba(83, 141, 184, 0.14);
}

.cloud::before {
  left: 34px;
  top: -30px;
  width: 88px;
  height: 88px;
}

.cloud::after {
  right: 28px;
  top: -20px;
  width: 76px;
  height: 76px;
}

.cloud-a {
  top: 8%;
  left: -220px;
  transform: scale(0.92);
  animation-duration: 54s;
}

.cloud-b {
  top: 18%;
  left: 18%;
  transform: scale(0.62);
  opacity: 0.48;
  animation-duration: 74s;
  animation-delay: -24s;
}

.cloud-c {
  top: 36%;
  left: -260px;
  transform: scale(0.78);
  opacity: 0.42;
  animation-duration: 68s;
  animation-delay: -16s;
}

.cloud-d {
  top: 68%;
  left: 62%;
  transform: scale(0.52);
  opacity: 0.34;
  animation-duration: 86s;
  animation-delay: -44s;
}

.cloud-e {
  top: 76%;
  left: -180px;
  transform: scale(0.7);
  opacity: 0.32;
  animation-duration: 92s;
  animation-delay: -10s;
}

.cloud-f {
  top: 3%;
  left: 48%;
  transform: scale(0.48);
  opacity: 0.28;
  animation-duration: 96s;
  animation-delay: -58s;
}

.cloud-g {
  top: 52%;
  left: 12%;
  transform: scale(0.58);
  opacity: 0.26;
  animation-duration: 110s;
  animation-delay: -72s;
}

.fog-bank {
  z-index: 1;
  top: auto;
  height: 34vh;
  pointer-events: none;
  background:
    radial-gradient(ellipse at 16% 78%, rgba(255, 255, 255, 0.42), transparent 32%),
    radial-gradient(ellipse at 38% 86%, rgba(208, 241, 255, 0.34), transparent 34%),
    radial-gradient(ellipse at 68% 82%, rgba(255, 255, 255, 0.38), transparent 36%),
    linear-gradient(180deg, transparent, rgba(184, 231, 255, 0.2) 42%, rgba(255, 255, 255, 0.22));
  filter: blur(8px);
}

@keyframes starTwinkle {
  from {
    opacity: 0.48;
  }

  to {
    opacity: 0.82;
  }
}

@keyframes meteorFall {
  0% {
    opacity: 0;
    translate: 0 0;
  }

  8% {
    opacity: 0.9;
  }

  22% {
    opacity: 0;
    translate: -280px 96px;
  }

  100% {
    opacity: 0;
    translate: -280px 96px;
  }
}

@keyframes cloudDrift {
  from {
    translate: -15vw 0;
  }

  to {
    translate: 125vw 0;
  }
}

.login-shell {
  position: relative;
  z-index: 4;
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: minmax(280px, 0.88fr) minmax(340px, 0.78fr);
  gap: 34px;
  align-items: center;
}

.login-brand {
  color: #ffffff;
}

.login-brand-mark {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(136, 217, 255, 0.72);
  border-radius: 8px;
  background: rgba(11, 31, 68, 0.78);
  color: #95dcff;
  font-size: 22px;
  font-weight: 800;
  box-shadow: 0 0 28px rgba(47, 174, 255, 0.28);
}

.login-brand h1 {
  margin: 24px 0 12px;
  font-size: 42px;
  line-height: 1.18;
  color: #ffffff;
  letter-spacing: 0;
}

.login-brand p {
  width: min(520px, 100%);
  margin: 0;
  color: #b8cae8;
  font-size: 16px;
  line-height: 1.8;
}

.login-card {
  display: block;
  width: 100%;
  min-width: 0;
  padding: 30px;
  border: 1px solid rgba(132, 212, 255, 0.32);
  border-radius: 8px;
  background: rgba(8, 20, 48, 0.78);
  box-shadow:
    0 22px 60px rgba(0, 0, 0, 0.38),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(14px);
}

.login-card-head {
  margin-bottom: 22px;
  text-align: center;
}

.login-card-head span {
  display: block;
  color: #76d6ff;
  font-size: 12px;
  text-transform: uppercase;
}

.login-card-head h2 {
  margin: 10px 0 0;
  color: #ffffff;
  font-size: 24px;
  font-weight: 700;
}

.login-form {
  margin-bottom: 20px;
}

.login-submit {
  width: 100%;
  height: 42px;
  margin-top: 2px;
  font-weight: 700;
}

.login-role-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.login-role {
  min-height: 78px;
  padding: 12px;
  border: 1px solid rgba(130, 192, 232, 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #d9ecff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.login-role:hover,
.login-role.active {
  border-color: rgba(118, 214, 255, 0.82);
  background: rgba(24, 106, 174, 0.32);
  transform: translateY(-1px);
}

.login-role strong,
.login-role span {
  display: block;
}

.login-role strong {
  font-size: 15px;
}

.login-role span {
  margin-top: 7px;
  color: #a9bddb;
  font-size: 12px;
  line-height: 1.45;
}

:deep(.el-form-item__label) {
  color: #c8dcf7;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  min-height: 42px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 0 0 1px rgba(126, 204, 255, 0.2);
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 22px;
  }

  .login-brand {
    text-align: center;
  }

  .login-brand-mark {
    margin: 0 auto;
  }

  .login-brand h1 {
    font-size: 32px;
  }
}

@media (max-width: 560px) {
  .login-page {
    padding: 16px;
  }

  .login-card {
    padding: 22px;
  }

  .login-role-grid {
    grid-template-columns: 1fr;
  }
}
</style>
