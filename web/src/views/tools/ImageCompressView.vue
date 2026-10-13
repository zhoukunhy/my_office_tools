<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadBlob, downloadFilesAsZip, baseName } from '@/utils/file'
import { loadImage, encodeImage, quantizeCanvas, type ImgFormat } from '@/utils/image'

interface Item {
  file: File
  originSize: number
  result: Blob | null
  resultSize: number
  preview: string
  processing: boolean
}

const items = ref<Item[]>([])
const quality = ref(0.8)
const maxWidth = ref(0) // 0 = 不限
const format = ref<ImgFormat>('jpeg') // PNG 重编码，JPG/WebP 可调质量
const pngQuantize = ref(false) // PNG 智能量化
const pngColors = ref(256)
const pngDither = ref<'floyd-steinberg' | 'none'>('floyd-steinberg')
const processingAll = ref(false)

async function onFiles(files: File[]) {
  for (const f of files.filter((x) => x.type.startsWith('image/'))) {
    items.value.push({
      file: f,
      originSize: f.size,
      result: null,
      resultSize: 0,
      preview: URL.createObjectURL(f),
      processing: false
    })
  }
}

function remove(idx: number) {
  URL.revokeObjectURL(items.value[idx].preview)
  items.value.splice(idx, 1)
}
function clearAll() {
  items.value.forEach((i) => URL.revokeObjectURL(i.preview))
  items.value = []
}

function savings(it: Item) {
  if (!it.resultSize || !it.originSize) return 0
  return Math.round(((it.originSize - it.resultSize) / it.originSize) * 100)
}

async function compressOne(idx: number) {
  const it = items.value[idx]
  it.processing = true
  try {
    const { img } = await loadImage(it.file)
    const fmt = format.value
    if (fmt === 'png' && pngQuantize.value) {
      // PNG 智能量化：先绘制（可选限宽），再降色量化
      const scale =
        maxWidth.value && img.naturalWidth > maxWidth.value
          ? maxWidth.value / img.naturalWidth
          : 1
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.naturalWidth * scale)
      canvas.height = Math.round(img.naturalHeight * scale)
      const ctx = canvas.getContext('2d')!
      ctx.imageSmoothingQuality = 'high'
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      const quantized = await quantizeCanvas(canvas, pngColors.value, pngDither.value)
      it.result = await new Promise<Blob>((resolve, reject) => {
        quantized.toBlob((b) => (b ? resolve(b) : reject(new Error('编码失败'))), 'image/png')
      })
    } else {
      const q = fmt === 'png' ? 1 : quality.value
      const blob = await encodeImage(img, fmt, q, maxWidth.value || undefined, undefined)
      it.result = blob
    }
    it.resultSize = it.result.size
  } catch (e) {
    ElMessage.error('压缩失败：' + (e as Error).message)
  } finally {
    it.processing = false
  }
}

async function compressAll() {
  processingAll.value = true
  for (let i = 0; i < items.value.length; i++) {
    if (!items.value[i].result) await compressOne(i)
  }
  processingAll.value = false
  ElMessage.success('全部压缩完成')
}

async function downloadOne(idx: number) {
  const it = items.value[idx]
  if (!it.result) {
    await compressOne(idx)
  }
  if (it.result) {
    const ext = format.value === 'jpeg' ? 'jpg' : format.value
    downloadBlob(it.result, `${baseName(it.file.name)}.${ext}`)
  }
}

async function downloadAll() {
  const outs = []
  for (let i = 0; i < items.value.length; i++) {
    const it = items.value[i]
    if (!it.result) await compressOne(i)
    if (it.result) {
      const ext = format.value === 'jpeg' ? 'jpg' : format.value
      outs.push({ blob: it.result, name: `${baseName(it.file.name)}.${ext}` })
    }
  }
  if (outs.length) await downloadFilesAsZip(outs, '图片压缩.zip')
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <FileDropZone accept="image/*" hint="支持 PNG / JPG / WebP 批量压缩" @files="onFiles" />

    <div v-if="items.length" class="card p-5 space-y-4">
      <div class="flex flex-col sm:flex-row gap-4 sm:items-end">
        <div class="flex-1">
          <label class="text-sm text-text-soft block mb-1">输出格式</label>
          <el-radio-group v-model="format">
            <el-radio value="jpeg">JPG（可调质量）</el-radio>
            <el-radio value="webp">WebP（可调质量）</el-radio>
            <el-radio value="png">PNG（无损重编码）</el-radio>
          </el-radio-group>
        </div>
        <div v-if="format !== 'png'">
          <label class="text-sm text-text-soft block mb-1">质量：{{ quality.toFixed(2) }}</label>
          <el-slider v-model="quality" :min="0.3" :max="1" :step="0.01" />
        </div>
        <div v-else class="sm:col-span-3 space-y-2">
          <el-checkbox v-model="pngQuantize">智能量化（降色至 {{ pngColors }} 色，体积更小，视觉几乎无差）</el-checkbox>
          <div v-if="pngQuantize" class="flex items-center gap-4">
            <div>
              <span class="text-sm text-text-mute mr-2">颜色数</span>
              <el-select v-model="pngColors" class="w-28">
                <el-option label="256 色" :value="256" />
                <el-option label="128 色" :value="128" />
                <el-option label="64 色" :value="64" />
                <el-option label="32 色" :value="32" />
              </el-select>
            </div>
            <div>
              <span class="text-sm text-text-mute mr-2">抖动</span>
              <el-radio-group v-model="pngDither">
                <el-radio value="floyd-steinberg">开（过渡更自然）</el-radio>
                <el-radio value="none">关（色块更纯净）</el-radio>
              </el-radio-group>
            </div>
          </div>
        </div>
        <div class="flex-1">
          <label class="text-sm text-text-soft block mb-1">最大宽度（0 = 不限）</label>
          <el-input-number v-model="maxWidth" :min="0" :step="100" />
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" :disabled="processingAll" @click="compressAll">
          <el-icon v-if="processingAll" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon>
          全部压缩
        </button>
        <button class="btn-ghost !border !border-border" @click="downloadAll">
          <el-icon><Download /></el-icon> 全部下载（ZIP）
        </button>
        <button class="btn-ghost text-text-mute ml-auto" @click="clearAll">清空</button>
      </div>

      <ul class="space-y-2">
        <li
          v-for="(it, i) in items"
          :key="i"
          class="flex items-center gap-3 p-2 rounded-md hover:bg-bg-soft"
        >
          <img :src="it.preview" class="w-14 h-14 object-cover rounded border border-border" alt="" />
          <div class="min-w-0 flex-1">
            <div class="text-sm truncate">{{ it.file.name }}</div>
            <div class="text-xs text-text-mute">
              {{ formatBytes(it.originSize) }}
              <span v-if="it.resultSize"> → {{ formatBytes(it.resultSize) }}</span>
              <span v-if="it.resultSize" class="ml-1 text-primary">省 {{ savings(it) }}%</span>
            </div>
            <el-progress
              v-if="it.processing"
              :percentage="100"
              :status="'success'"
              :show-text="false"
              :stroke-width="3"
            />
          </div>
          <button class="btn-ghost" @click="compressOne(i)">压缩</button>
          <button class="btn-ghost" @click="downloadOne(i)" title="下载">
            <el-icon><Download /></el-icon>
          </button>
          <button class="btn-ghost !px-1.5 hover:text-red-500" @click="remove(i)">
            <el-icon><Delete /></el-icon>
          </button>
        </li>
      </ul>
    </div>

    <p class="text-xs text-text-mute text-center">
      提示：JPG/WebP 降质量可大幅减小体积；PNG 为无损重编码，仅去除元数据，体积下降有限。
    </p>
  </div>
</template>
