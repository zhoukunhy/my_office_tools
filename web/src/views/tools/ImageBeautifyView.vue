<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadBlob, baseName } from '@/utils/file'
import { loadImage, convolve, type ImgFormat } from '@/utils/image'

const file = ref<File | null>(null)
const imgEl = ref<HTMLImageElement | null>(null)

// 参数
const radius = ref(12) // 圆角，占短边百分比
const borderWidth = ref(0)
const borderColor = ref('#ffffff')
const pad = ref(24) // 外边距
const bgColor = ref('#f1f5f9')
const shadowBlur = ref(24)
const shadowColor = ref('rgba(0,0,0,0.25)')
const shadowOffsetY = ref(8)
const brightness = ref(100)
const contrast = ref(100)
const saturation = ref(100)
const sharpen = ref(0) // 0-100
const format = ref<ImgFormat>('png')
const quality = ref(0.92)

const previewCanvas = ref<HTMLCanvasElement | null>(null)
const processing = ref(false)

async function onFiles(files: File[]) {
  const f = files[0]
  if (!f) return
  try {
    const { img } = await loadImage(f)
    file.value = f
    imgEl.value = img
    renderPreview()
  } catch {
    ElMessage.error('图片读取失败')
  }
}

function reset() {
  file.value = null
  imgEl.value = null
}

/** 核心：生成美化后的画布（scale=1 全尺寸 / 预览时缩小） */
function render(scale: number): HTMLCanvasElement | null {
  const img = imgEl.value
  if (!img) return null
  const iw = Math.round(img.naturalWidth * scale)
  const ih = Math.round(img.naturalHeight * scale)

  // 1. 调色层（亮度/对比度/饱和度 + 锐化）
  const base = document.createElement('canvas')
  base.width = iw
  base.height = ih
  const bctx = base.getContext('2d')!
  bctx.filter = `brightness(${brightness.value}%) contrast(${contrast.value}%) saturate(${saturation.value}%)`
  bctx.drawImage(img, 0, 0, iw, ih)
  bctx.filter = 'none'
  if (sharpen.value > 0) {
    const sharp = convolve(base, [0, -1, 0, -1, 5, -1, 0, -1, 0])
    const s = sharpen.value / 100
    const srcData = bctx.getImageData(0, 0, iw, ih)
    const sharpData = sharp.getContext('2d')!.getImageData(0, 0, iw, ih)
    const a = srcData.data
    const b = sharpData.data
    for (let i = 0; i < a.length; i += 4) {
      a[i] = a[i] * (1 - s) + b[i] * s
      a[i + 1] = a[i + 1] * (1 - s) + b[i + 1] * s
      a[i + 2] = a[i + 2] * (1 - s) + b[i + 2] * s
    }
    bctx.putImageData(srcData, 0, 0)
  }

  // 2. 圆角层
  const r = Math.round((Math.min(iw, ih) * radius.value) / 100)
  const rounded = document.createElement('canvas')
  rounded.width = iw
  rounded.height = ih
  const rctx = rounded.getContext('2d')!
  if (r > 0) {
    rctx.beginPath()
    rctx.moveTo(r, 0)
    rctx.arcTo(iw, 0, iw, ih, r)
    rctx.arcTo(iw, ih, 0, ih, r)
    rctx.arcTo(0, ih, 0, 0, r)
    rctx.arcTo(0, 0, iw, 0, r)
    rctx.closePath()
    rctx.clip()
  }
  rctx.drawImage(base, 0, 0)

  // 3. 画布层（外边距 + 背景 + 阴影 + 描边）
  const m = Math.round(pad.value * scale)
  const bw = Math.round(borderWidth.value * scale)
  const out = document.createElement('canvas')
  out.width = iw + m * 2
  out.height = ih + m * 2
  const octx = out.getContext('2d')!
  octx.fillStyle = bgColor.value
  octx.fillRect(0, 0, out.width, out.height)
  if (shadowBlur.value > 0) {
    octx.shadowColor = shadowColor.value
    octx.shadowBlur = shadowBlur.value * scale
    octx.shadowOffsetY = shadowOffsetY.value * scale
  }
  octx.drawImage(rounded, m, m)
  octx.shadowColor = 'transparent'
  if (bw > 0) {
    octx.strokeStyle = borderColor.value
    octx.lineWidth = bw * 2
    octx.beginPath()
    if (r > 0) {
      octx.moveTo(m + r, m)
      octx.arcTo(m + iw, m, m + iw, m + ih, r)
      octx.arcTo(m + iw, m + ih, m, m + ih, r)
      octx.arcTo(m, m + ih, m, m, r)
      octx.arcTo(m, m, m + iw, m, r)
    } else {
      octx.rect(m, m, iw, ih)
    }
    octx.closePath()
    octx.stroke()
  }
  return out
}

function renderPreview() {
  if (!imgEl.value || !previewCanvas.value) return
  const img = imgEl.value
  const scale = Math.min(1, 800 / Math.max(img.naturalWidth, img.naturalHeight))
  const out = render(scale)
  if (!out) return
  const p = previewCanvas.value
  p.width = out.width
  p.height = out.height
  p.getContext('2d')!.drawImage(out, 0, 0)
}

async function exportImage() {
  if (!imgEl.value || !file.value) return
  processing.value = true
  try {
    const out = render(1)
    if (!out) return
    const mime = format.value === 'png' ? 'image/png' : `image/${format.value}`
    const q = format.value === 'png' ? 1 : quality.value
    const blob = await new Promise<Blob>((resolve, reject) => {
      out.toBlob((b) => (b ? resolve(b) : reject(new Error('编码失败'))), mime, q)
    })
    const ext = format.value === 'jpeg' ? 'jpg' : format.value
    downloadBlob(blob, `${baseName(file.value.name)}_beautify.${ext}`)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败：' + (e as Error).message)
  } finally {
    processing.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <FileDropZone
      v-if="!file"
      accept="image/*"
      :multiple="false"
      hint="选择一张截图，调整圆角/边框/阴影/色调后导出"
      @files="onFiles"
    />

    <div v-else class="grid lg:grid-cols-5 gap-5">
      <!-- 预览 -->
      <div class="lg:col-span-3 space-y-3">
        <div class="card p-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium">实时预览</span>
            <div class="flex gap-1">
              <button class="btn-ghost" @click="renderPreview">
                <el-icon><Refresh /></el-icon> 刷新
              </button>
              <button class="btn-ghost" @click="reset">换图</button>
            </div>
          </div>
          <canvas ref="previewCanvas" class="w-full rounded border border-border bg-bg-soft"></canvas>
        </div>
        <button class="btn-primary w-full" :disabled="processing" @click="exportImage">
          <el-icon v-if="processing" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><Download /></el-icon>
          {{ processing ? '导出中…' : '导出图片' }}
        </button>
      </div>

      <!-- 参数 -->
      <div class="lg:col-span-2 card p-5 space-y-4 max-h-[70vh] overflow-auto">
        <div>
          <label class="text-sm text-text-soft block mb-1">圆角 {{ radius }}%</label>
          <el-slider v-model="radius" :min="0" :max="50" @input="renderPreview" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <span class="text-sm text-text-mute block mb-1">外边距 {{ pad }}px</span>
            <el-slider v-model="pad" :min="0" :max="120" @input="renderPreview" />
          </div>
          <div>
            <span class="text-sm text-text-mute block mb-1">背景色</span>
            <el-color-picker v-model="bgColor" @change="renderPreview" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <span class="text-sm text-text-mute block mb-1">描边 {{ borderWidth }}px</span>
            <el-slider v-model="borderWidth" :min="0" :max="20" @input="renderPreview" />
          </div>
          <div>
            <span class="text-sm text-text-mute block mb-1">描边颜色</span>
            <el-color-picker v-model="borderColor" @change="renderPreview" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <span class="text-sm text-text-mute block mb-1">阴影模糊 {{ shadowBlur }}px</span>
            <el-slider v-model="shadowBlur" :min="0" :max="60" @input="renderPreview" />
          </div>
          <div>
            <span class="text-sm text-text-mute block mb-1">阴影下移 {{ shadowOffsetY }}px</span>
            <el-slider v-model="shadowOffsetY" :min="-20" :max="30" @input="renderPreview" />
          </div>
        </div>
        <div>
          <span class="text-sm text-text-mute block mb-1">阴影颜色</span>
          <el-color-picker v-model="shadowColor" show-alpha @change="renderPreview" />
        </div>

        <div class="h-px bg-border"></div>

        <div class="grid grid-cols-1 gap-3">
          <div>
            <span class="text-sm text-text-mute block">亮度 {{ brightness }}%</span>
            <el-slider v-model="brightness" :min="50" :max="150" @input="renderPreview" />
          </div>
          <div>
            <span class="text-sm text-text-mute block">对比度 {{ contrast }}%</span>
            <el-slider v-model="contrast" :min="50" :max="150" @input="renderPreview" />
          </div>
          <div>
            <span class="text-sm text-text-mute block">饱和度 {{ saturation }}%</span>
            <el-slider v-model="saturation" :min="0" :max="200" @input="renderPreview" />
          </div>
          <div>
            <span class="text-sm text-text-mute block">锐化 {{ sharpen }}%</span>
            <el-slider v-model="sharpen" :min="0" :max="100" @input="renderPreview" />
          </div>
        </div>

        <div class="h-px bg-border"></div>

        <div>
          <label class="text-sm text-text-soft block mb-1">输出格式</label>
          <el-radio-group v-model="format" @change="renderPreview">
            <el-radio value="png">PNG</el-radio>
            <el-radio value="jpeg">JPG</el-radio>
            <el-radio value="webp">WebP</el-radio>
          </el-radio-group>
          <div v-if="format !== 'png'" class="mt-2">
            <span class="text-sm text-text-mute mr-2">质量 {{ quality.toFixed(2) }}</span>
            <el-slider v-model="quality" :min="0.3" :max="1" :step="0.01" class="w-36 inline-block align-middle" />
          </div>
        </div>
        <p v-if="file" class="text-xs text-text-mute">原图：{{ formatBytes(file.size) }}</p>
      </div>
    </div>
  </div>
</template>
