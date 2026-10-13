<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadFilesAsZip, downloadBlob, baseName } from '@/utils/file'

interface Item {
  file: File
  preview: string
  result: Blob | null
  resultPreview: string
  status: 'idle' | 'processing' | 'done' | 'error'
  progress: number
}

const items = ref<Item[]>([])
const model = ref<'isnet_fp16' | 'isnet' | 'isnet_quint8'>('isnet_fp16')
const processingAll = ref(false)
const currentProgress = ref(0)
const modelLoaded = ref(false)

const MODEL_TIP: Record<string, string> = {
  isnet_fp16: '均衡（推荐，约 44MB）',
  isnet: '高质量（约 88MB）',
  isnet_quint8: '轻量快速（约 22MB，精度略低）'
}

async function onFiles(files: File[]) {
  for (const f of files.filter((x) => x.type.startsWith('image/'))) {
    items.value.push({
      file: f,
      preview: URL.createObjectURL(f),
      result: null,
      resultPreview: '',
      status: 'idle',
      progress: 0
    })
  }
}

function remove(idx: number) {
  URL.revokeObjectURL(items.value[idx].preview)
  if (items.value[idx].resultPreview) URL.revokeObjectURL(items.value[idx].resultPreview)
  items.value.splice(idx, 1)
}
function clearAll() {
  items.value.forEach((i) => {
    URL.revokeObjectURL(i.preview)
    if (i.resultPreview) URL.revokeObjectURL(i.resultPreview)
  })
  items.value = []
}

async function processOne(idx: number) {
  const it = items.value[idx]
  if (it.status === 'done') return
  it.status = 'processing'
  it.progress = 0
  currentProgress.value = 0
  try {
    // 动态加载，避免拖慢首屏
    const { removeBackground } = await import('@imgly/background-removal')
    const blob = await removeBackground(it.file, {
      model: model.value,
      device: 'cpu',
      output: { format: 'image/png', quality: 1 },
      progress: (_key, current, total) => {
        const p = total > 0 ? Math.round((current / total) * 100) : 0
        it.progress = p
        currentProgress.value = p
      }
    })
    modelLoaded.value = true
    it.result = blob
    it.resultPreview = URL.createObjectURL(blob)
    it.status = 'done'
  } catch (e) {
    it.status = 'error'
    ElMessage.error(`处理失败 ${it.file.name}：` + (e as Error).message)
  } finally {
    currentProgress.value = 0
  }
}

async function processAll() {
  processingAll.value = true
  try {
    for (let i = 0; i < items.value.length; i++) {
      if (items.value[i].status !== 'done') await processOne(i)
    }
    if (items.value.some((i) => i.status === 'done')) ElMessage.success('抠图完成')
  } finally {
    processingAll.value = false
  }
}

function downloadOne(idx: number) {
  const it = items.value[idx]
  if (it.result) downloadBlob(it.result, `${baseName(it.file.name)}_nobg.png`)
}

async function downloadAll() {
  const outs = items.value
    .filter((i) => i.result)
    .map((i) => ({ blob: i.result!, name: `${baseName(i.file.name)}_nobg.png` }))
  if (!outs.length) {
    ElMessage.warning('暂无已完成的结果，请先处理')
    return
  }
  await downloadFilesAsZip(outs, 'AI抠图.zip')
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- 模型提示 -->
    <div class="card p-4 flex items-start gap-3 text-sm">
      <el-icon class="text-primary mt-0.5"><InfoFilled /></el-icon>
      <div class="flex-1">
        <p class="leading-relaxed">
          抠图由 AI 模型在<span class="text-primary font-medium">浏览器本地</span>完成，图片不会上传。
          <span class="text-text-mute">首次使用需从 CDN 下载模型（{{ MODEL_TIP[model] }}），完成后浏览器缓存，可离线使用；移动端设备较吃力，建议 PC 使用。</span>
        </p>
      </div>
      <el-select v-model="model" class="w-44 shrink-0">
        <el-option label="均衡 isnet_fp16" value="isnet_fp16" />
        <el-option label="高质量 isnet" value="isnet" />
        <el-option label="轻量 quint8" value="isnet_quint8" />
      </el-select>
    </div>

    <FileDropZone accept="image/*" hint="支持批量抠图，逐张自动处理" @files="onFiles" />

    <div v-if="items.length" class="space-y-4">
      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" :disabled="processingAll" @click="processAll">
          <el-icon v-if="processingAll" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon>
          {{ processingAll ? '处理中…' : modelLoaded ? '开始抠图' : '下载模型并抠图' }}
        </button>
        <button class="btn-ghost !border !border-border" @click="downloadAll">
          <el-icon><Download /></el-icon> 下载全部（ZIP）
        </button>
        <button class="btn-ghost text-text-mute ml-auto" @click="clearAll">清空</button>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div v-for="(it, i) in items" :key="i" class="card overflow-hidden">
          <div class="relative aspect-square bg-bg-soft">
            <!-- 棋盘格底纹衬托透明 -->
            <div
              v-if="it.resultPreview"
              class="absolute inset-0 checker"
            ></div>
            <img
              :src="it.resultPreview || it.preview"
              class="absolute inset-0 w-full h-full object-contain"
              alt=""
            />
            <div
              v-if="it.status === 'processing'"
              class="absolute inset-0 bg-black/40 flex flex-col items-center justify-center gap-2 text-white"
            >
              <el-icon class="animate-spin" :size="24"><Loading /></el-icon>
              <span class="text-xs">{{ it.progress ? `${it.progress}%` : '准备中…' }}</span>
            </div>
            <div
              v-if="it.status === 'error'"
              class="absolute inset-0 bg-red-500/80 flex items-center justify-center text-white"
            >
              <span class="text-sm">失败，请重试</span>
            </div>
          </div>
          <div class="p-2 flex items-center gap-1">
            <div class="min-w-0 flex-1">
              <div class="text-xs truncate">{{ it.file.name }}</div>
              <div class="text-[10px] text-text-mute">
                {{ formatBytes(it.file.size) }}
                <span v-if="it.result"> → {{ formatBytes(it.result.size) }}</span>
              </div>
            </div>
            <button class="btn-ghost !px-1" title="重新处理" @click="((it.status = 'idle'), processOne(i))">
              <el-icon><RefreshRight /></el-icon>
            </button>
            <button v-if="it.result" class="btn-ghost !px-1" title="下载" @click="downloadOne(i)">
              <el-icon><Download /></el-icon>
            </button>
            <button class="btn-ghost !px-1 hover:text-red-500" title="移除" @click="remove(i)">
              <el-icon><Delete /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.checker {
  background-image:
    linear-gradient(45deg, #d8dbe2 25%, transparent 25%),
    linear-gradient(-45deg, #d8dbe2 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #d8dbe2 75%),
    linear-gradient(-45deg, transparent 75%, #d8dbe2 75%);
  background-size: 16px 16px;
  background-position: 0 0, 0 8px, 8px -8px, -8px 0px;
  background-color: #fff;
}
</style>
