<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import QRCode from 'qrcode'
import jsQR from 'jsqr'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '@/utils/file'
import { resolveApiUrl } from '@/utils/api'

type Tab = 'generate' | 'parse'

const tab = ref<Tab>('generate')

// ===== 生成 =====
const text = ref('https://example.com')
const size = ref(256)
const margin = ref(2)
const dark = ref('#000000')
const light = ref('#ffffff')
const ec = ref<'L' | 'M' | 'Q' | 'H'>('M')
const dataUrl = ref('')

// URL 校验状态
const urlStatus = ref<'idle' | 'checking' | 'valid' | 'invalid' | 'unreachable'>('idle')
const urlMessage = ref('')

/** 判断内容是否像 URL */
function looksLikeUrl(s: string): boolean {
  const trimmed = s.trim()
  return /^https?:\/\//i.test(trimmed)
}

/** 客户端 URL 格式校验 */
function isValidUrl(s: string): boolean {
  try {
    const u = new URL(s.trim())
    return u.protocol === 'http:' || u.protocol === 'https:'
  } catch {
    return false
  }
}

/** 调用后端接口检查 URL 可访问性 */
async function checkUrlAccessible(url: string): Promise<{ ok: boolean; reason: string }> {
  const apiBase = resolveApiUrl('/check-url')
  if (!apiBase) {
    // 后端未开启，跳过可访问性检查
    return { ok: true, reason: '后端未开启，跳过可访问性检查' }
  }
  try {
    const resp = await fetch(`${apiBase}?url=${encodeURIComponent(url)}`)
    const data = await resp.json()
    return { ok: data.ok, reason: data.reason }
  } catch {
    return { ok: false, reason: '无法连接后端服务' }
  }
}

/** 对输入内容进行 URL 校验 */
let checkTimer: ReturnType<typeof setTimeout> | null = null
async function validateUrl() {
  const content = text.value.trim()

  if (!content) {
    urlStatus.value = 'idle'
    urlMessage.value = ''
    return
  }

  // 非 URL 内容（纯文本），直接放行
  if (!looksLikeUrl(content)) {
    urlStatus.value = 'idle'
    urlMessage.value = ''
    return
  }

  // URL 格式校验
  if (!isValidUrl(content)) {
    urlStatus.value = 'invalid'
    urlMessage.value = 'URL 格式不正确，请输入完整的网址（如 https://example.com）'
    return
  }

  // URL 可访问性检查（防抖）
  urlStatus.value = 'checking'
  urlMessage.value = '正在检查 URL 可访问性…'

  if (checkTimer) clearTimeout(checkTimer)
  checkTimer = setTimeout(async () => {
    const result = await checkUrlAccessible(content)
    if (result.ok) {
      urlStatus.value = 'valid'
      urlMessage.value = result.reason
    } else {
      urlStatus.value = 'unreachable'
      urlMessage.value = result.reason
    }
  }, 800)
}

async function generate() {
  if (!text.value.trim()) {
    ElMessage.warning('请输入要生成二维码的内容')
    return
  }

  // 如果内容像 URL，先做格式校验
  if (looksLikeUrl(text.value)) {
    if (!isValidUrl(text.value)) {
      ElMessage.error('URL 格式不正确，请输入完整的网址（如 https://example.com）')
      return
    }
    // 提示可访问性状态
    if (urlStatus.value === 'unreachable') {
      ElMessage.warning(`URL 无法访问：${urlMessage.value}，二维码仍会生成，但扫码后可能无法打开`)
    }
  }

  try {
    dataUrl.value = await QRCode.toDataURL(text.value, {
      width: size.value,
      margin: margin.value,
      errorCorrectionLevel: ec.value,
      color: { dark: dark.value, light: light.value }
    })
  } catch (e) {
    ElMessage.error('生成失败：' + (e as Error).message)
  }
}

// 文本变化时触发 URL 校验
watch(text, () => {
  validateUrl()
})

// 文本或样式变化时重新生成
watch([text, size, margin, ec, dark, light], () => {
  if (tab.value === 'generate') generate()
})

// 初始化：校验默认 URL + 生成二维码
onMounted(() => {
  validateUrl()
  generate()
})

function downloadPng() {
  if (!dataUrl.value) return
  fetch(dataUrl.value)
    .then((r) => r.blob())
    .then((b) => downloadBlob(b, 'qrcode.png'))
}

// ===== 解析 =====
const parseText = ref('')
const parsePreview = ref('')

async function onImage(file: File) {
  parsePreview.value = URL.createObjectURL(file)
  try {
    const bitmap = await createImageBitmap(file)
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(bitmap, 0, 0)
    const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height)
    const code = jsQR(data, canvas.width, canvas.height)
    if (code) {
      parseText.value = code.data
      ElMessage.success('解析成功')
    } else {
      parseText.value = ''
      ElMessage.warning('未识别到二维码')
    }
  } catch (e) {
    ElMessage.error('解析失败：' + (e as Error).message)
  }
}

function pickFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = () => {
    if (input.files?.[0]) onImage(input.files[0])
  }
  input.click()
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f && f.type.startsWith('image/')) onImage(f)
}

function copyParse() {
  navigator.clipboard.writeText(parseText.value).then(() => ElMessage.success('已复制'))
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <el-tabs v-model="tab" class="mb-6">
      <el-tab-pane label="生成二维码" name="generate" />
      <el-tab-pane label="解析二维码" name="parse" />
    </el-tabs>

    <!-- 生成 -->
    <div v-if="tab === 'generate'" class="grid md:grid-cols-2 gap-6">
      <div class="card p-5 space-y-4">
        <div>
          <label class="text-sm text-text-soft block mb-1">内容（链接/文本）</label>
          <el-input
            v-model="text"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="https://…"
          />
          <!-- URL 校验状态提示 -->
          <div v-if="urlStatus !== 'idle'" class="mt-1.5 flex items-center gap-1.5 text-xs">
            <span v-if="urlStatus === 'checking'" class="text-blue-500">
              <el-icon class="animate-spin"><Loading /></el-icon> {{ urlMessage }}
            </span>
            <span v-else-if="urlStatus === 'valid'" class="text-green-600">
              <el-icon><CircleCheckFilled /></el-icon> {{ urlMessage }}
            </span>
            <span v-else-if="urlStatus === 'invalid'" class="text-red-500">
              <el-icon><CircleCloseFilled /></el-icon> {{ urlMessage }}
            </span>
            <span v-else-if="urlStatus === 'unreachable'" class="text-orange-500">
              <el-icon><WarningFilled /></el-icon> {{ urlMessage }}
            </span>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-sm text-text-soft block mb-1">尺寸 {{ size }}px</label>
            <el-slider v-model="size" :min="64" :max="512" :step="32" />
          </div>
          <div>
            <label class="text-sm text-text-soft block mb-1">边距 {{ margin }}</label>
            <el-slider v-model="margin" :min="0" :max="8" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="text-sm text-text-soft block mb-1">容错</label>
            <el-select v-model="ec" size="default">
              <el-option label="L (7%)" value="L" />
              <el-option label="M (15%)" value="M" />
              <el-option label="Q (25%)" value="Q" />
              <el-option label="H (30%)" value="H" />
            </el-select>
          </div>
          <div>
            <label class="text-sm text-text-soft block mb-1">前景色</label>
            <el-color-picker v-model="dark" />
          </div>
          <div>
            <label class="text-sm text-text-soft block mb-1">选择背景色</label>
            <el-color-picker v-model="light" />
          </div>
        </div>
      </div>

      <div class="card p-5 flex flex-col items-center justify-center gap-4">
        <img v-if="dataUrl" :src="dataUrl" class="w-48 h-48 rounded border border-border" alt="qrcode" />
        <el-icon v-else :size="48" class="text-text-mute"><Picture /></el-icon>
        <button class="btn-primary" :disabled="!dataUrl" @click="downloadPng">
          <el-icon><Download /></el-icon> 下载 PNG
        </button>
      </div>
    </div>

    <!-- 解析 -->
    <div v-else class="space-y-4">
      <div
        class="border-2 border-dashed border-border rounded-xl p-10 text-center cursor-pointer hover:border-primary hover:bg-primary-soft/40 transition-all"
        @click="pickFile"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <el-icon :size="36" class="text-primary mb-2"><PictureFilled /></el-icon>
        <p class="font-medium">点击或拖入二维码图片</p>
        <p class="text-sm text-text-mute mt-1">支持 PNG / JPG，本地解析不上传</p>
      </div>
      <div v-if="parsePreview" class="text-center">
        <img :src="parsePreview" class="w-40 h-40 object-contain mx-auto rounded border border-border" alt="" />
      </div>
      <div v-if="parseText !== ''">
        <label class="text-sm text-text-soft block mb-1">解析结果</label>
        <el-input v-model="parseText" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" readonly />
        <button class="btn-ghost mt-2" @click="copyParse">
          <el-icon><CopyDocument /></el-icon> 复制结果
        </button>
      </div>
    </div>
  </div>
</template>
