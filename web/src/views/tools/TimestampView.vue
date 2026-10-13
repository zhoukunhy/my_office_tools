<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

// 实时时间戳
const now = ref(Date.now())
let timer: number
onMounted(() => {
  timer = window.setInterval(() => (now.value = Date.now()), 1000)
})
onUnmounted(() => clearInterval(timer))

const nowSec = computed(() => Math.floor(now.value / 1000))

// 时间戳 -> 日期
const tsInput = ref(String(Math.floor(Date.now() / 1000)))
const tsResult = computed(() => {
  const raw = tsInput.value.trim()
  if (!raw || !/^\d+$/.test(raw)) return { valid: false as const, err: '请输入纯数字时间戳' }
  let n = parseInt(raw, 10)
  // 10 位当秒，13 位当毫秒，其余按毫秒
  if (raw.length === 10) n *= 1000
  if (raw.length === 13) n = n
  else if (raw.length < 10) n *= 1000
  const d = new Date(n)
  if (isNaN(d.getTime())) return { valid: false as const, err: '无效时间戳' }
  return {
    valid: true as const,
    ms: n,
    local: d.toLocaleString('zh-CN'),
    iso: d.toISOString(),
    date: d.toLocaleDateString('zh-CN'),
    time: d.toLocaleTimeString('zh-CN')
  }
})

function useNowSec() {
  tsInput.value = String(nowSec.value)
}
function useNowMs() {
  tsInput.value = String(now.value)
}

// 日期 -> 时间戳
const dateInput = ref(new Date())
const dateMs = computed(() => dateInput.value.getTime())
const dateSec = computed(() => Math.floor(dateMs.value / 1000))

function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

// 常用时区
const zones = [
  { label: 'UTC', value: 'UTC' },
  { label: '北京时间 (UTC+8)', value: 'Asia/Shanghai' },
  { label: '东京 (UTC+9)', value: 'Asia/Tokyo' },
  { label: '纽约 (UTC-5)', value: 'America/New_York' },
  { label: '伦敦 (UTC+0)', value: 'Europe/London' },
  { label: '洛杉矶 (UTC-8)', value: 'America/Los_Angeles' }
]
const zoneInput = ref(String(Math.floor(Date.now() / 1000)))
const zoneSel = ref('Asia/Shanghai')
const zoneResult = computed(() => {
  const raw = zoneInput.value.trim()
  if (!/^\d+$/.test(raw)) return '无效'
  let n = parseInt(raw, 10)
  if (raw.length === 10) n *= 1000
  const d = new Date(n)
  try {
    return d.toLocaleString('zh-CN', { timeZone: zoneSel.value })
  } catch {
    return '时区不支持'
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- 实时时间戳 -->
    <div class="card p-5">
      <h3 class="font-semibold mb-3 flex items-center gap-2">
        <el-icon class="text-primary"><Timer /></el-icon> 当前时间戳
      </h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="bg-bg-soft rounded-md p-3">
          <div class="text-xs text-text-mute mb-1">秒（10 位）</div>
          <div class="font-mono text-lg flex items-center gap-2">
            <span>{{ nowSec }}</span>
            <button class="btn-ghost !px-1" @click="copy(String(nowSec))">
              <el-icon><CopyDocument /></el-icon>
            </button>
          </div>
        </div>
        <div class="bg-bg-soft rounded-md p-3">
          <div class="text-xs text-text-mute mb-1">毫秒（13 位）</div>
          <div class="font-mono text-lg flex items-center gap-2">
            <span>{{ now }}</span>
            <button class="btn-ghost !px-1" @click="copy(String(now))">
              <el-icon><CopyDocument /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 时间戳转日期 -->
    <div class="card p-5">
      <h3 class="font-semibold mb-3">时间戳 → 日期</h3>
      <div class="flex gap-2 mb-3">
        <el-input v-model="tsInput" placeholder="输入秒或毫秒时间戳" class="font-mono" />
        <button class="btn-ghost !border !border-border whitespace-nowrap" @click="useNowSec">当前秒</button>
        <button class="btn-ghost !border !border-border whitespace-nowrap" @click="useNowMs">当前毫秒</button>
      </div>
      <div v-if="tsResult.valid" class="space-y-2 text-sm">
        <div class="flex justify-between bg-bg-soft rounded p-2">
          <span class="text-text-mute">本地时间</span>
          <span class="font-mono">{{ tsResult.local }}</span>
        </div>
        <div class="flex justify-between bg-bg-soft rounded p-2">
          <span class="text-text-mute">ISO 8601</span>
          <span class="font-mono">{{ tsResult.iso }}</span>
        </div>
        <div class="flex justify-between bg-bg-soft rounded p-2">
          <span class="text-text-mute">日期 / 时间</span>
          <span class="font-mono">{{ tsResult.date }} · {{ tsResult.time }}</span>
        </div>
      </div>
      <p v-else class="text-sm text-red-500">{{ tsResult.err }}</p>
    </div>

    <!-- 日期转时间戳 -->
    <div class="card p-5">
      <h3 class="font-semibold mb-3">日期 → 时间戳</h3>
      <el-date-picker
        v-model="dateInput"
        type="datetime"
        placeholder="选择日期时间"
        class="w-full mb-3"
      />
      <div class="grid grid-cols-2 gap-4">
        <div class="bg-bg-soft rounded p-3 flex items-center justify-between">
          <div>
            <div class="text-xs text-text-mute mb-1">秒</div>
            <div class="font-mono">{{ dateSec }}</div>
          </div>
          <button class="btn-ghost !px-1" @click="copy(String(dateSec))">
            <el-icon><CopyDocument /></el-icon>
          </button>
        </div>
        <div class="bg-bg-soft rounded p-3 flex items-center justify-between">
          <div>
            <div class="text-xs text-text-mute mb-1">毫秒</div>
            <div class="font-mono">{{ dateMs }}</div>
          </div>
          <button class="btn-ghost !px-1" @click="copy(String(dateMs))">
            <el-icon><CopyDocument /></el-icon>
          </button>
        </div>
      </div>
    </div>

    <!-- 时区转换 -->
    <div class="card p-5">
      <h3 class="font-semibold mb-3">时区转换</h3>
      <div class="flex flex-col sm:flex-row gap-2 mb-3">
        <el-input v-model="zoneInput" placeholder="时间戳" class="font-mono sm:max-w-xs" />
        <el-select v-model="zoneSel" class="flex-1">
          <el-option v-for="z in zones" :key="z.value" :label="z.label" :value="z.value" />
        </el-select>
      </div>
      <div class="bg-bg-soft rounded p-3 text-sm flex justify-between">
        <span class="text-text-mute">目标时区时间</span>
        <span class="font-mono">{{ zoneResult }}</span>
      </div>
    </div>
  </div>
</template>
