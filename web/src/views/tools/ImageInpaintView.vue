<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { RouterLink } from 'vue-router'
import { usePreferenceStore } from '@/stores/preference'
import { backendFetch } from '@/utils/api'
import { downloadBlob, formatBytes, baseName } from '@/utils/file'

const pref = usePreferenceStore()
const canUseBackend = computed(() => pref.backendEnabled)

// ========== 状态 ==========
const file = ref<File | null>(null)
const imageUrl = ref<string>('')
const originalWidth = ref(0)
const originalHeight = ref(0)
const processing = ref(false)

const brushSize = ref(20)
const drawMode = ref<'brush' | 'eraser'>('brush')
const inpaintRadius = ref(8)

// canvas 引用
const imageCanvasRef = ref<HTMLCanvasElement | null>(null)
const maskCanvasRef = ref<HTMLCanvasElement | null>(null)
const canvasWrapRef = ref<HTMLDivElement | null>(null)

// 画布显示尺寸（CSS 像素）
const displayWidth = ref(0)
const displayHeight = ref(0)

// 绘图状态
const isDrawing = ref(false)
const lastPoint = ref<{ x: number; y: number } | null>(null)

// 结果
const resultBlob = ref<Blob | null>(null)
const resultUrl = ref<string>('')
const resultName = ref<string>('')
const resultFileSize = ref(0)

// ========== 计算属性 ==========
const hasMask = ref(false)

// ========== 文件上传 ==========
function onFiles(list: File[]) {
  const img = list.find((f) => f.type.startsWith('image/'))
  if (!img) {
    ElMessage.warning('请上传图片文件（PNG / JPG / WEBP）')
    return
  }
  resetAll()
  file.value = img
  loadImage(img)
}

function loadImage(f: File) {
  const url = URL.createObjectURL(f)
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    originalWidth.value = img.naturalWidth
    originalHeight.value = img.naturalHeight
    imageUrl.value = url
    nextTick(() => {
      setupCanvases(img)
    })
  }
  img.onerror = () => {
    URL.revokeObjectURL(url)
    ElMessage.error('图片加载失败')
    file.value = null
  }
  img.src = url
}

// ========== 画布初始化 ==========
function setupCanvases(img: HTMLImageElement) {
  if (!imageCanvasRef.value || !maskCanvasRef.value || !canvasWrapRef.value) return

  const wrapWidth = canvasWrapRef.value.clientWidth
  const maxHeight = 520
  let dw = wrapWidth
  let dh = (img.naturalHeight / img.naturalWidth) * dw
  if (dh > maxHeight) {
    dh = maxHeight
    dw = (img.naturalWidth / img.naturalHeight) * dh
  }
  displayWidth.value = dw
  displayHeight.value = dh

  const w = Math.round(dw)
  const h = Math.round(dh)

  // 原图 canvas（仅显示用）
  const ic = imageCanvasRef.value
  ic.width = w
  ic.height = h
  const ictx = ic.getContext('2d')
  if (ictx) {
    ictx.clearRect(0, 0, w, h)
    ictx.drawImage(img, 0, 0, w, h)
  }

  // mask canvas（覆盖在上层，透明底，用户绘制）
  const mc = maskCanvasRef.value
  mc.width = w
  mc.height = h
  const mctx = mc.getContext('2d')
  if (mctx) {
    mctx.clearRect(0, 0, w, h)
  }
  hasMask.value = false
}

// ========== mask 绘图 ==========
function getCanvasPoint(e: MouseEvent | TouchEvent): { x: number; y: number } | null {
  const mc = maskCanvasRef.value
  if (!mc) return null
  const rect = mc.getBoundingClientRect()
  let clientX = 0
  let clientY = 0
  if (e instanceof TouchEvent) {
    const t = e.touches[0] || e.changedTouches[0]
    if (!t) return null
    clientX = t.clientX
    clientY = t.clientY
  } else {
    clientX = e.clientX
    clientY = e.clientY
  }
  return {
    x: (clientX - rect.left) * (mc.width / rect.width),
    y: (clientY - rect.top) * (mc.height / rect.height)
  }
}

function startDraw(e: MouseEvent | TouchEvent) {
  if (!maskCanvasRef.value) return
  e.preventDefault()
  isDrawing.value = true
  const p = getCanvasPoint(e)
  lastPoint.value = p
  // 单击也画一个圆点
  if (p) drawDot(p)
}

function moveDraw(e: MouseEvent | TouchEvent) {
  if (!isDrawing.value || !maskCanvasRef.value) return
  e.preventDefault()
  const p = getCanvasPoint(e)
  if (!p || !lastPoint.value) {
    lastPoint.value = p
    return
  }
  drawStroke(lastPoint.value, p)
  lastPoint.value = p
}

function endDraw() {
  if (isDrawing.value) {
    isDrawing.value = false
    lastPoint.value = null
    checkMaskHasContent()
  }
}

function drawDot(p: { x: number; y: number }) {
  const mc = maskCanvasRef.value
  if (!mc) return
  const ctx = mc.getContext('2d')
  if (!ctx) return
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = brushSize.value
  if (drawMode.value === 'brush') {
    ctx.globalCompositeOperation = 'source-over'
    ctx.fillStyle = '#ff0000'
    ctx.beginPath()
    ctx.arc(p.x, p.y, brushSize.value / 2, 0, Math.PI * 2)
    ctx.fill()
  } else {
    ctx.globalCompositeOperation = 'destination-out'
    ctx.beginPath()
    ctx.arc(p.x, p.y, brushSize.value / 2, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalCompositeOperation = 'source-over'
}

function drawStroke(from: { x: number; y: number }, to: { x: number; y: number }) {
  const mc = maskCanvasRef.value
  if (!mc) return
  const ctx = mc.getContext('2d')
  if (!ctx) return

  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = brushSize.value

  if (drawMode.value === 'brush') {
    // 在可见层用不透明红色绘制，CSS opacity 让其看起来半透明
    ctx.globalCompositeOperation = 'source-over'
    ctx.strokeStyle = '#ff0000'
    ctx.beginPath()
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(to.x, to.y)
    ctx.stroke()
  } else {
    // 橡皮擦：清空像素
    ctx.globalCompositeOperation = 'destination-out'
    ctx.beginPath()
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(to.x, to.y)
    ctx.stroke()
  }
  ctx.globalCompositeOperation = 'source-over'
}

function checkMaskHasContent() {
  const mc = maskCanvasRef.value
  if (!mc) return
  const ctx = mc.getContext('2d')
  if (!ctx) return
  const { data } = ctx.getImageData(0, 0, mc.width, mc.height)
  for (let i = 3; i < data.length; i += 4) {
    if (data[i] > 0) {
      hasMask.value = true
      return
    }
  }
  hasMask.value = false
}

function clearMask() {
  const mc = maskCanvasRef.value
  if (!mc) return
  const ctx = mc.getContext('2d')
  if (ctx) ctx.clearRect(0, 0, mc.width, mc.height)
  hasMask.value = false
}

// ========== 生成原图比例的 mask Blob（白色=修复区域，黑色=保留） ==========
async function getOriginalSizeMaskBlob(): Promise<Blob> {
  const mc = maskCanvasRef.value
  if (!mc) {
    return new Blob([], { type: 'image/png' })
  }
  // 1) 创建原图尺寸的离屏 canvas A，把显示层的 mask（红色笔划）按比例缩放到原图尺寸
  const offA = document.createElement('canvas')
  offA.width = originalWidth.value
  offA.height = originalHeight.value
  const octxA = offA.getContext('2d')
  if (!octxA) {
    return new Blob([], { type: 'image/png' })
  }
  octxA.drawImage(mc, 0, 0, offA.width, offA.height)

  // 2) 读取像素，把 alpha>0 的像素转成纯白色 RGB(255,255,255)，alpha 保持；其他像素转纯黑完全不透明。
  //    这样后端不论读 RGB 通道还是 alpha 通道都能识别修复区域。
  const imgData = octxA.getImageData(0, 0, offA.width, offA.height)
  const data = imgData.data
  for (let i = 0; i < data.length; i += 4) {
    const a = data[i + 3]
    if (a > 0) {
      data[i] = 255     // R
      data[i + 1] = 255 // G
      data[i + 2] = 255 // B
      data[i + 3] = 255 // A（完全不透明白色）
    } else {
      data[i] = 0
      data[i + 1] = 0
      data[i + 2] = 0
      data[i + 3] = 255 // 完全不透明黑色
    }
  }
  octxA.putImageData(imgData, 0, 0)

  return await new Promise<Blob>((resolve, reject) => {
    offA.toBlob(
      (b) => {
        if (b) resolve(b)
        else reject(new Error('mask 生成失败'))
      },
      'image/png'
    )
  })
}

// ========== 提交修复 ==========
async function doInpaint() {
  if (!file.value || !canUseBackend.value) return
  if (!hasMask.value) {
    ElMessage.warning('请先用画笔涂抹需要修复的区域')
    return
  }
  processing.value = true
  try {
    const maskBlob = await getOriginalSizeMaskBlob()
    const form = new FormData()
    form.append('image', file.value)
    form.append('mask', maskBlob, 'mask.png')
    form.append('radius', String(inpaintRadius.value))

    const r = await backendFetch('/image/inpaint', form, { timeoutMs: 180_000 })
    if (!r.ok) {
      if (r.needBackend) {
        ElMessage.warning('请先在「个人中心」开启后端加速')
      } else {
        throw new Error(r.message)
      }
      return
    }
    resultBlob.value = r.blob
    resultFileSize.value = r.blob.size
    if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = URL.createObjectURL(r.blob)
    const ext = (file.value.name.split('.').pop() || 'png').toLowerCase()
    const useExt = ['png', 'jpg', 'jpeg', 'webp'].includes(ext) ? ext : 'png'
    resultName.value = r.filename || `${baseName(file.value.name)}_inpaint.${useExt}`
    ElMessage.success('修复完成')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '修复失败')
  } finally {
    processing.value = false
  }
}

// ========== 下载 / 重置 ==========
function downloadResult() {
  if (!resultBlob.value || !resultName.value) return
  downloadBlob(resultBlob.value, resultName.value)
}

function resetAll() {
  if (imageUrl.value) {
    try { URL.revokeObjectURL(imageUrl.value) } catch {}
    imageUrl.value = ''
  }
  if (resultUrl.value) {
    try { URL.revokeObjectURL(resultUrl.value) } catch {}
    resultUrl.value = ''
  }
  file.value = null
  resultBlob.value = null
  resultName.value = ''
  resultFileSize.value = 0
  originalWidth.value = 0
  originalHeight.value = 0
  displayWidth.value = 0
  displayHeight.value = 0
  clearMask()
  isDrawing.value = false
  lastPoint.value = null
  processing.value = false
}

// ========== 窗口大小变化时重设画布 ==========
function onResize() {
  if (!file.value || !imageUrl.value) return
  const img = new Image()
  img.onload = () => setupCanvases(img)
  img.src = imageUrl.value
}

let resizeTimer: number | null = null
function handleResize() {
  if (resizeTimer) window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(onResize, 150)
}

// 用 watch 监听 DOM 挂载
watch(
  () => [canvasWrapRef.value, imageUrl.value],
  () => {
    if (imageUrl.value && canvasWrapRef.value) {
      const img = new Image()
      img.onload = () => setupCanvases(img)
      img.src = imageUrl.value
    }
  }
)

if (typeof window !== 'undefined') {
  window.addEventListener('resize', handleResize)
}
onBeforeUnmount(() => {
  if (resizeTimer) window.clearTimeout(resizeTimer)
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleResize)
  }
  if (imageUrl.value) try { URL.revokeObjectURL(imageUrl.value) } catch {}
  if (resultUrl.value) try { URL.revokeObjectURL(resultUrl.value) } catch {}
})
</script>

<template>
  <ToolHeader title="图片去文字 / 瑕疵修复" description="涂抹需要去除的文字或瑕疵区域，AI 自动修复">
    <template #statusTop>
      <span class="text-xs" :class="canUseBackend ? 'text-success' : 'text-warning'">
        {{ canUseBackend ? '✓ 后端加速已开启' : '⚠ 需要后端加速' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-6xl py-6">
    <FileDropZone
      accept="image/png,image/jpeg,image/jpg,image/webp,image/*"
      :multiple="false"
      hint="仅接受单张图片（PNG / JPG / WEBP，推荐 ≤ 10MB）"
      chunk-label="① 上传图片"
      :current-count="file ? 1 : 0"
      :max-size="10 * 1024 * 1024"
      @files="onFiles"
    />

    <div v-if="!file" class="empty-block">
      <el-icon :size="34" class="mb-2"><Picture /></el-icon>
      <div>还没有上传图片</div>
      <p class="text-xs text-text-mute mt-1">上传后在左侧画笔涂抹，AI 会自动修复被涂抹的区域</p>
    </div>

    <template v-else>
      <!-- 文件信息 -->
      <div class="card p-4 mt-2">
        <div class="flex items-center gap-4 flex-wrap">
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium truncate">{{ file.name }}</div>
            <div class="text-xs text-text-mute">
              {{ formatBytes(file.size) }} · {{ originalWidth }}×{{ originalHeight }}
            </div>
          </div>
          <RouterLink
            v-if="!canUseBackend"
            to="/me"
            class="text-xs text-primary hover:underline inline-block"
          >
            → 去开启后端加速
          </RouterLink>
          <button class="btn-ghost" @click="resetAll">
            <el-icon :size="16"><Delete /></el-icon>
            重置
          </button>
        </div>
      </div>

      <!-- 工具栏 -->
      <div class="card p-4 mt-2">
        <div class="flex flex-wrap items-center gap-4">
          <!-- 画笔大小 -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-text-soft whitespace-nowrap">画笔大小</span>
            <el-slider
              v-model="brushSize"
              :min="5"
              :max="80"
              :step="1"
              style="width: 160px"
              show-input
              :input-size="'small'"
            />
          </div>

          <!-- 画笔/橡皮 -->
          <div>
            <el-radio-group v-model="drawMode" size="small">
              <el-radio-button value="brush">
                <el-icon :size="14"><EditPen /></el-icon>
                <span class="ml-1">画笔</span>
              </el-radio-button>
              <el-radio-button value="eraser">
                <el-icon :size="14"><Eraser /></el-icon>
                <span class="ml-1">橡皮</span>
              </el-radio-button>
            </el-radio-group>
          </div>

          <!-- 清除蒙版 -->
          <button class="btn-secondary" @click="clearMask" :disabled="!hasMask">
            <el-icon :size="16"><RefreshLeft /></el-icon>
            清除蒙版
          </button>

          <!-- 修复半径 -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-text-soft whitespace-nowrap">修复半径</span>
            <el-slider
              v-model="inpaintRadius"
              :min="3"
              :max="50"
              :step="1"
              style="width: 140px"
              show-input
              :input-size="'small'"
            />
            <span class="text-xs text-text-mute">px</span>
          </div>

          <!-- 操作按钮 -->
          <div class="ml-auto flex items-center gap-2">
            <button
              class="btn-primary"
              :disabled="!canUseBackend || processing || !hasMask"
              @click="doInpaint"
            >
              <el-icon v-if="processing" :size="16" class="animate-spin"><Loading /></el-icon>
              <el-icon v-else :size="16"><MagicStick /></el-icon>
              {{ processing ? '修复中…' : '一键修复' }}
            </button>
            <button
              class="btn-secondary"
              :disabled="!resultBlob"
              @click="downloadResult"
            >
              <el-icon :size="16"><Download /></el-icon>
              下载结果
            </button>
          </div>
        </div>
        <div class="mt-2 text-xs text-text-mute">
          <span class="text-warning">提示：</span>
          用红色画笔精确涂抹需要去除的文字、水印、瑕疵等区域；橡皮可擦除错误涂抹；修复半径越大，AI 参考周围区域越广。
        </div>
      </div>

      <!-- 双栏：左=绘画区，右=结果区 -->
      <div class="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- 左侧：绘画画布 -->
        <div class="card p-3">
          <div class="text-xs text-text-mute mb-2 flex items-center justify-between">
            <span>原图（在图片上涂抹要修复的区域）</span>
            <span v-if="hasMask" class="text-primary">已涂抹 {{ brushSize }}px</span>
          </div>
          <div
            ref="canvasWrapRef"
            class="relative mx-auto bg-bg-soft rounded overflow-hidden select-none"
            :style="{ width: '100%', minHeight: '300px' }"
          >
            <div
              class="relative mx-auto"
              :style="{
                width: displayWidth + 'px',
                height: displayHeight + 'px',
                maxWidth: '100%'
              }"
            >
              <canvas
                ref="imageCanvasRef"
                class="absolute inset-0"
                :style="{ width: '100%', height: '100%' }"
              />
              <canvas
                ref="maskCanvasRef"
                class="absolute inset-0 cursor-crosshair touch-none"
                :style="{ width: '100%', height: '100%', opacity: 0.5 }"
                @mousedown="startDraw"
                @mousemove="moveDraw"
                @mouseup="endDraw"
                @mouseleave="endDraw"
                @touchstart="startDraw"
                @touchmove="moveDraw"
                @touchend="endDraw"
                @touchcancel="endDraw"
              />
            </div>
          </div>
        </div>

        <!-- 右侧：结果预览 -->
        <div class="card p-3">
          <div class="text-xs text-text-mute mb-2">修复结果</div>
          <div
            class="relative mx-auto bg-bg-soft rounded overflow-hidden flex items-center justify-center"
            :style="{ width: '100%', minHeight: '300px' }"
          >
            <div
              v-if="resultUrl"
              class="relative mx-auto"
              :style="{
                width: displayWidth ? displayWidth + 'px' : '100%',
                height: displayHeight ? displayHeight + 'px' : 'auto',
                maxWidth: '100%'
              }"
            >
              <img
                :src="resultUrl"
                alt="修复结果"
                class="w-full h-full object-contain"
              />
            </div>
            <div
              v-else-if="processing"
              class="flex flex-col items-center gap-2 py-16 text-text-soft"
            >
              <el-icon :size="32" class="animate-spin text-primary"><Loading /></el-icon>
              <span class="text-sm">AI 正在修复，请稍候…</span>
            </div>
            <div v-else class="flex flex-col items-center gap-2 py-16 text-text-mute">
              <el-icon :size="36"><MagicStick /></el-icon>
              <span class="text-sm">涂抹后点击「一键修复」</span>
            </div>
          </div>

          <div v-if="resultBlob" class="mt-3 flex items-center gap-3">
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium truncate">{{ resultName }}</div>
              <div class="text-xs text-text-mute">
                {{ formatBytes(resultFileSize) }}
              </div>
            </div>
            <button class="btn-primary" :disabled="!resultBlob" @click="downloadResult">
              <el-icon :size="16"><Download /></el-icon>
              下载
            </button>
          </div>
        </div>
      </div>
    </template>

    <div class="mt-4 space-y-1 text-xs text-text-mute leading-relaxed">
      <p><strong>画笔</strong>：涂抹需要去除的文字、水印、污渍、瑕疵等区域</p>
      <p><strong>橡皮</strong>：擦除多余的涂抹区域，精确控制修复范围</p>
      <p><strong>修复半径</strong>：AI 参考周围像素的范围，细小瑕疵用小值，大面积涂抹用大值</p>
      <p class="mt-2 text-warning">注意：该功能需要开启后端加速服务。为保证修复质量，请尽量完整覆盖需要去除的区域，不要超出太多。</p>
    </div>
  </section>
</template>
