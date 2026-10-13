<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ref, computed, onMounted } from 'vue'
import { useThemeStore, THEME_COLOR_PRESETS, type FontScale } from '@/stores/theme'
import { usePreferenceStore, DEFAULT_BACKEND_BASE } from '@/stores/preference'
import ThemeToggle from '@/components/common/ThemeToggle.vue'

function clearAllLocalAndReload(): void {
  window.localStorage.clear()
  window.location.reload()
}

const theme = useThemeStore()
const pref = usePreferenceStore()

const sizes: { id: FontScale; label: string; tip: string }[] = [
  { id: 'sm', label: '紧凑', tip: '14px' },
  { id: 'base', label: '标准', tip: '15px' },
  { id: 'lg', label: '舒适', tip: '16.5px' },
  { id: 'xl', label: '大字号', tip: '18px' }
]

const backendEnabled = ref<boolean>(pref.backendEnabled)
const backendBaseUrl = ref<string>(pref.backendBaseUrl || DEFAULT_BACKEND_BASE)
const backendTesting = ref<boolean>(false)
const backendTestOk = ref<boolean | null>(null)
const backendTestMsg = ref<string>('')

function saveBackend(): void {
  pref.setBackend(backendBaseUrl.value, backendEnabled.value)
  backendBaseUrl.value = pref.backendBaseUrl // 回写规范化后的值
  ElMessage.success('后端偏好已保存')
}

async function testBackend(): Promise<void> {
  const base = backendBaseUrl.value.trim().replace(/\/+$/, '').replace(/\/api$/i, '')
  // base 不含 /api 后缀（与 resolveApiUrl 规则一致），健康检查固定拼 /api/health
  const url = base ? `${base}/api/health` : '/api/health'
  backendTesting.value = true
  backendTestOk.value = null
  backendTestMsg.value = ''
  try {
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>
    if (res.ok) {
      backendTestOk.value = true
      backendTestMsg.value = `连接成功 · ${data.version || res.status}`
    } else {
      backendTestOk.value = false
      backendTestMsg.value = `后端服务异常（HTTP ${res.status}），请检查上方链接是否需要修改`
    }
  } catch (err) {
    backendTestOk.value = false
    backendTestMsg.value = `后端服务异常：${err instanceof Error ? err.message : '网络不可达'}，请检查上方链接是否需要修改`
  } finally {
    backendTesting.value = false
  }
}

// 进入页面自动检测一次：正常时静默显示"连接成功"，异常时才提示检查链接
onMounted(() => {
  if (backendEnabled.value) void testBackend()
})

const recentCount = computed<number>(() => pref.recentTools.length)
const favCount = computed<number>(() => pref.favorites.length)
const isDark = computed<boolean>(() => theme.isDark)
</script>

<template>
  <div>
    <section class="container-page py-6 max-w-4xl">
      <h2 class="text-xl font-bold mb-6">个人中心</h2>

      <!-- 概览 -->
      <div class="card p-4 mb-5">
        <div class="grid grid-cols-3 gap-4 text-center">
          <div>
            <div class="text-2xl font-bold text-primary">{{ favCount }}</div>
            <div class="text-xs text-text-mute mt-1">收藏工具</div>
          </div>
          <div>
            <div class="text-2xl font-bold text-primary">{{ recentCount }}</div>
            <div class="text-xs text-text-mute mt-1">最近使用</div>
          </div>
          <div>
            <div class="text-2xl font-bold text-primary">{{ isDark ? '深色' : '浅色' }}</div>
            <div class="text-xs text-text-mute mt-1">当前模式</div>
          </div>
        </div>
      </div>

      <!-- 外观：模式 + 主题色 + 字号 -->
      <div class="card p-4 mb-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-semibold">外观偏好</h3>
          <ThemeToggle />
        </div>

        <div class="mb-5">
          <div class="text-sm text-text-soft mb-2">主题色</div>
          <div class="grid grid-cols-3 sm:grid-cols-6 gap-3">
            <button
              v-for="p in THEME_COLOR_PRESETS"
              :key="p.id"
              class="rounded-xl border p-2.5 text-left transition-all"
              :style="{
                borderColor: theme.colorId === p.id ? p.primary : 'var(--c-border)',
                boxShadow: theme.colorId === p.id ? `0 0 0 2px ${p.primary}33` : 'none'
              }"
              @click="theme.setColor(p.id)"
            >
              <div
                class="w-full aspect-[4/1] rounded-md mb-2"
                :style="{ background: `linear-gradient(135deg, ${p.gradientFrom}, ${p.gradientTo})` }"
              />
              <div class="text-xs font-medium">{{ p.label }}</div>
            </button>
          </div>
        </div>

        <div>
          <div class="text-sm text-text-soft mb-2">整体字号</div>
          <div class="grid grid-cols-4 gap-2">
            <button
              v-for="s in sizes"
              :key="s.id"
              class="rounded-lg border py-2.5 text-center transition-colors"
              :style="{
                borderColor: theme.fontSize === s.id ? 'var(--c-primary)' : 'var(--c-border)',
                backgroundColor:
                  theme.fontSize === s.id ? 'var(--c-primary-soft)' : 'var(--c-card)'
              }"
              @click="theme.setFontSize(s.id)"
            >
              <div class="text-sm font-semibold">{{ s.label }}</div>
              <div class="text-[11px] text-text-mute mt-0.5">{{ s.tip }}</div>
            </button>
          </div>
        </div>
      </div>

      <!-- 后端：可选加速服务 -->
      <div class="card p-4 mb-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-base font-semibold">后端加速（可选）</h3>
          <el-switch v-model="backendEnabled" />
        </div>
        <p class="text-xs text-text-mute mb-3 leading-relaxed">
          启用后，PDF 压缩、Word ↔ PDF 互转、OCR 提取文字等纯前端无法稳定完成的操作，
          将通过指定的后端 API 执行。默认已填好本机后端地址，无需修改；
          仅当检测提示"后端服务异常"时，才需要检查链接是否正确。
        </p>
        <div class="flex flex-col sm:flex-row gap-2 mb-3">
          <el-input
            v-model="backendBaseUrl"
            :placeholder="`默认 ${DEFAULT_BACKEND_BASE}，留空=使用同源 /api`"
            size="default"
            :disabled="!backendEnabled"
          />
          <button
            class="btn-ghost shrink-0 border border-border"
            :disabled="backendTesting"
            @click="testBackend"
          >
            <el-icon :size="16"><Connection /></el-icon>
            {{ backendTesting ? '检测中…' : '连通性检测' }}
          </button>
        </div>
        <div
          v-if="backendTestOk !== null"
          class="text-xs mb-3"
          :class="backendTestOk ? 'text-success' : 'text-danger'"
        >
          {{ backendTestMsg }}
        </div>
        <div class="flex justify-end">
          <button class="btn-primary" @click="saveBackend">
            <el-icon :size="16"><Check /></el-icon> 保存后端偏好
          </button>
        </div>
      </div>

      <!-- 其它链接 -->
      <div class="card p-4 mb-5">
        <h3 class="text-base font-semibold mb-3">关于 &amp; 支持</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <RouterLink to="/about" class="btn-ghost border border-border justify-start">
            <el-icon :size="16"><InfoFilled /></el-icon> 关于速用工具箱
          </RouterLink>
          <RouterLink to="/system" class="btn-ghost border border-border justify-start">
            <el-icon :size="16"><Promotion /></el-icon> 系统效率工具推荐
          </RouterLink>
        </div>
      </div>

      <!-- 数据管理（清缓存） -->
      <div class="card p-4">
        <h3 class="text-base font-semibold mb-3">数据管理</h3>
        <p class="text-xs text-text-mute mb-3 leading-relaxed">
          所有收藏、最近使用、外观设置都仅保存在你本地浏览器中，不会上传。
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            class="btn-ghost border border-border"
            @click="
              pref.favorites = [];
              ElMessage.success('已清空收藏')
            "
          >
            清空收藏
          </button>
          <button
            class="btn-ghost border border-border"
            @click="
              pref.recent = [];
              ElMessage.success('已清空最近使用')
            "
          >
            清空最近使用
          </button>
          <button
            class="btn-ghost-danger btn-ghost border border-border"
            @click="clearAllLocalAndReload()"
          >
            清空全部本地数据并刷新
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
