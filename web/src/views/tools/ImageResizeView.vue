<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadFilesAsZip, baseName, downloadBlob } from '@/utils/file'
import { loadImage, fitSize, type ImgFormat } from '@/utils/image'

interface Item {
  file: File
  width: number
  height: number
  targetW: number
  targetH: number
  result: Blob | null
  newName: string
  processing: boolean
}

const items = ref<Item[]>([])
type Mode = 'percent' | 'width' | 'height' | 'exact'
const mode = ref<Mode>('percent')
const percent = ref(50)
const pxValue = ref(1920)
const pxValue2 = ref(1080)
const keepRatio = ref(true)
type RenameMode = 'keep' | 'prefix' | 'suffix' | 'sequence'
const renameMode = ref<RenameMode>('keep')
const prefixText = ref('img_')
const seqStart = ref(1)
const format = ref<'keep' | ImgFormat>('keep')
const quality = ref(0.92)
const processingAll = ref(false)

function targetSize(w: number, h: number) {
  return fitSize(
    w,
    h,
    mode.value,
    mode.value === 'percent' ? percent.value : pxValue.value,
    pxValue2.value,
    keepRatio.value
  )
}

async function onFiles(files: File[]) {
  for (const f of files.filter((x) => x.type.startsWith('image/'))) {
    try {
      const { width, height } = await loadImage(f)
      const t = targetSize(width, height)
      items.value.push({
        file: f,
        width,
        height,
        targetW: t.w,
        targetH: t.h,
        result: null,
        newName: '',
        processing: false
      })
    } catch {
      ElMessage.error(`读取失败：${f.name}`)
    }
  }
}

// 参数变化时重算目标尺寸
function recompute() {
  items.value.forEach((it) => {
    const t = targetSize(it.width, it.height)
    it.targetW = t.w
    it.targetH = t.h
  })
}

function outputExt(it: Item) {
  if (format.value === 'keep') {
    const m = it.file.type.replace('image/', '')
    return m === 'jpeg' ? 'jpg' : m || 'png'
  }
  return format.value === 'jpeg' ? 'jpg' : format.value
}

function buildName(it: Item, idx: number) {
  const ext = outputExt(it)
  const base = baseName(it.file.name)
  if (renameMode.value === 'prefix') return `${prefixText.value}${base}.${ext}`
  if (renameMode.value === 'suffix') return `${base}${prefixText.value}.${ext}`
  if (renameMode.value === 'sequence')
    return `${prefixText.value || 'img_'}${String(seqStart.value + idx).padStart(3, '0')}.${ext}`
  return `${base}.${ext}`
}

function remove(idx: number) {
  items.value.splice(idx, 1)
}
function clearAll() {
  items.value = []
}

async function processOne(idx: number) {
  const it = items.value[idx]
  it.processing = true
  try {
    const { img } = await loadImage(it.file)
    const fmt: ImgFormat = format.value === 'keep' ? (guessFormat(it.file.type) as ImgFormat) : format.value
    const q = fmt === 'png' ? 1 : quality.value
    const canvas = document.createElement('canvas')
    canvas.width = it.targetW
    canvas.height = it.targetH
    const ctx = canvas.getContext('2d')!
    ctx.imageSmoothingQuality = 'high'
    if (fmt === 'jpeg') {
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
    }
    ctx.drawImage(img, 0, 0, it.targetW, it.targetH)
    it.result = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('编码失败'))), `image/${fmt === 'jpeg' ? 'jpeg' : fmt}`, q)
    })
  } catch (e) {
    ElMessage.error('处理失败：' + (e as Error).message)
  } finally {
    it.processing = false
  }
}

function guessFormat(mime: string): ImgFormat {
  if (mime === 'image/webp') return 'webp'
  if (mime === 'image/jpeg') return 'jpeg'
  return 'png'
}

async function processAll() {
  processingAll.value = true
  for (let i = 0; i < items.value.length; i++) await processOne(i)
  processingAll.value = false
  ElMessage.success('全部处理完成')
}

async function downloadOne(idx: number) {
  const it = items.value[idx]
  if (!it.result) await processOne(idx)
  if (it.result) downloadBlob(it.result, buildName(it, idx))
}

async function downloadAll() {
  for (let i = 0; i < items.value.length; i++) if (!items.value[i].result) await processOne(i)
  const outs = items.value.map((it, i) => ({ blob: it.result!, name: buildName(it, i) }))
  if (outs.length) await downloadFilesAsZip(outs, '图片改尺寸.zip')
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <FileDropZone accept="image/*" hint="支持批量，先设置尺寸参数再上传也可" @files="onFiles" />

    <div v-if="items.length" class="card p-5 space-y-4">
      <!-- 尺寸设置 -->
      <div class="space-y-3">
        <label class="text-sm text-text-soft block">尺寸模式</label>
        <el-radio-group v-model="mode" @change="recompute">
          <el-radio value="percent">按百分比</el-radio>
          <el-radio value="width">按宽度</el-radio>
          <el-radio value="height">按高度</el-radio>
          <el-radio value="exact">指定宽高</el-radio>
        </el-radio-group>
        <div class="flex flex-wrap items-center gap-4">
          <div v-if="mode === 'percent'">
            <span class="text-sm text-text-mute mr-2">缩放</span>
            <el-input-number v-model="percent" :min="1" :max="500" @change="recompute" />
            <span class="text-sm text-text-mute ml-1">%</span>
          </div>
          <div v-else-if="mode === 'width'">
            <span class="text-sm text-text-mute mr-2">目标宽度</span>
            <el-input-number v-model="pxValue" :min="1" :max="10000" @change="recompute" />
            <span class="text-sm text-text-mute ml-1">px</span>
          </div>
          <div v-else-if="mode === 'height'">
            <span class="text-sm text-text-mute mr-2">目标高度</span>
            <el-input-number v-model="pxValue" :min="1" :max="10000" @change="recompute" />
            <span class="text-sm text-text-mute ml-1">px</span>
          </div>
          <template v-else>
            <div>
              <span class="text-sm text-text-mute mr-2">宽</span>
              <el-input-number v-model="pxValue" :min="1" :max="10000" @change="recompute" />
            </div>
            <div>
              <span class="text-sm text-text-mute mr-2">高</span>
              <el-input-number v-model="pxValue2" :min="1" :max="10000" @change="recompute" />
            </div>
            <el-checkbox v-model="keepRatio" @change="recompute">保持宽高比</el-checkbox>
          </template>
        </div>
      </div>

      <div class="h-px bg-border"></div>

      <!-- 重命名 / 输出格式 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-text-soft block mb-1">重命名规则</label>
          <div class="flex gap-2">
            <el-select v-model="renameMode" class="w-32">
              <el-option label="保留原名" value="keep" />
              <el-option label="加前缀" value="prefix" />
              <el-option label="加后缀" value="suffix" />
              <el-option label="序号命名" value="sequence" />
            </el-select>
            <el-input
              v-if="renameMode !== 'keep'"
              v-model="prefixText"
              :placeholder="renameMode === 'sequence' ? '序号前缀 img_' : '输入前/后缀'"
            />
            <el-input-number
              v-if="renameMode === 'sequence'"
              v-model="seqStart"
              :min="0"
              title="起始序号"
            />
          </div>
        </div>
        <div>
          <label class="text-sm text-text-soft block mb-1">输出格式</label>
          <el-radio-group v-model="format">
            <el-radio value="keep">保持原格式</el-radio>
            <el-radio value="jpeg">JPG</el-radio>
            <el-radio value="png">PNG</el-radio>
            <el-radio value="webp">WebP</el-radio>
          </el-radio-group>
          <div v-if="format !== 'keep' && format !== 'png'" class="mt-2">
            <span class="text-sm text-text-mute mr-2">质量 {{ quality.toFixed(2) }}</span>
            <el-slider v-model="quality" :min="0.3" :max="1" :step="0.01" class="w-40 inline-block align-middle" />
          </div>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" :disabled="processingAll" @click="processAll">
          <el-icon v-if="processingAll" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon> 全部处理
        </button>
        <button class="btn-ghost !border !border-border" @click="downloadAll">
          <el-icon><Download /></el-icon> 下载全部（ZIP）
        </button>
        <button class="btn-ghost text-text-mute ml-auto" @click="clearAll">清空</button>
      </div>

      <!-- 列表 -->
      <ul class="space-y-2">
        <li
          v-for="(it, i) in items"
          :key="i"
          class="flex items-center gap-3 p-2 rounded-md hover:bg-bg-soft"
        >
          <el-icon class="text-text-mute"><Picture /></el-icon>
          <div class="min-w-0 flex-1">
            <div class="text-sm truncate">{{ it.file.name }}</div>
            <div class="text-xs text-text-mute">
              {{ it.width }}×{{ it.height }} → {{ it.targetW }}×{{ it.targetH }} ·
              {{ formatBytes(it.file.size) }}
              <span v-if="it.result"> → {{ formatBytes(it.result.size) }}</span>
            </div>
            <div class="text-xs text-primary truncate">
              新文件名：{{ buildName(it, i) }}
            </div>
          </div>
          <el-icon v-if="it.processing" class="animate-spin text-primary"><Loading /></el-icon>
          <el-icon v-else-if="it.result" class="text-green-500"><CircleCheckFilled /></el-icon>
          <button class="btn-ghost" title="下载" @click="downloadOne(i)">
            <el-icon><Download /></el-icon>
          </button>
          <button class="btn-ghost !px-1.5 hover:text-red-500" @click="remove(i)">
            <el-icon><Delete /></el-icon>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
