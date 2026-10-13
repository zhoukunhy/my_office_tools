<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RouterLink } from 'vue-router'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import ProcessSteps, { type StepStatus } from '@/components/common/ProcessSteps.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import BatchFileList, { type BatchFileItem } from '@/components/common/BatchFileList.vue'
import { backendFetch, getBackendStatus } from '@/utils/api'
import { formatBytes, getExt } from '@/utils/file'

const backend = computed(() => getBackendStatus())

const files = ref<BatchFileItem[]>([])
const results = ref<{ id: string; name: string; text: string }[]>([])
const processing = ref(false)
const progress = ref(0)
const combinedText = ref('')

const steps = computed(() => {
  const s1: StepStatus = files.value.length ? 'done' : 'active'
  const s2: StepStatus = processing.value ? 'active' : files.value.length ? 'active' : 'idle'
  const s3: StepStatus = results.value.length ? 'done' : processing.value ? 'active' : 'idle'
  const s4: StepStatus = results.value.length ? 'active' : 'idle'
  return [
    { label: '上传图片', status: s1 },
    {
      label: backend.value.enabled ? '后端识别（高精度）' : '本地识别（基础）',
      status: s2
    },
    { label: '提取文字', status: s3 },
    { label: '复制 / 导出', status: s4 }
  ]
})

let idc = 0
function addFiles(list: File[]) {
  const ok = list.filter((f) =>
    ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif'].includes(getExt(f.name))
  )
  if (ok.length !== list.length) ElMessage.warning('已跳过非图片文件')
  files.value = [
    ...files.value,
    ...ok.map<BatchFileItem>((f) => ({
      id: `f${++idc}_${Date.now()}`,
      name: f.name,
      size: f.size,
      status: 'wait',
      previewUrl: URL.createObjectURL(f),
      _file: f
    }))
  ]
  results.value = []
  combinedText.value = ''
}
function remove(id: string) {
  files.value = files.value.filter((f) => {
    if (f.id === id && f.previewUrl) URL.revokeObjectURL(f.previewUrl)
    return f.id !== id
  })
  results.value = results.value.filter((r) => r.id !== id)
  rebuildCombined()
}
function clearAll() {
  files.value.forEach((f) => f.previewUrl && URL.revokeObjectURL(f.previewUrl))
  files.value = []
  results.value = []
  combinedText.value = ''
}
function move(a: number, b: number) {
  const arr = files.value.slice()
  const [t] = arr.splice(a, 1)
  arr.splice(b, 0, t)
  files.value = arr
}

function rebuildCombined() {
  combinedText.value = results.value
    .slice()
    .sort((a, b) => {
      const ia = files.value.findIndex((x) => x.id === a.id)
      const ib = files.value.findIndex((x) => x.id === b.id)
      return ia - ib
    })
    .map((r) => `# ${r.name}\n${r.text}`)
    .join('\n\n')
}

/** 结果分段按左侧列表顺序展示 */
const sortedResults = computed(() =>
  results.value.slice().sort((a, b) => {
    const ia = files.value.findIndex((x) => x.id === a.id)
    const ib = files.value.findIndex((x) => x.id === b.id)
    return ia - ib
  })
)

/** 点击缩略图 / 分段小图，全屏预览大图（可多图切换） */
const viewerVisible = ref(false)
const viewerIndex = ref(0)
const viewerUrls = computed(() =>
  files.value.filter((f) => f.previewUrl).map((f) => f.previewUrl as string)
)
function openPreview(item: BatchFileItem) {
  const idx = viewerUrls.value.indexOf(item.previewUrl as string)
  if (idx >= 0) {
    viewerIndex.value = idx
    viewerVisible.value = true
  }
}
function openPreviewById(id: string) {
  const item = files.value.find((f) => f.id === id)
  if (item) openPreview(item)
}
function previewOf(id: string): string | undefined {
  return files.value.find((f) => f.id === id)?.previewUrl
}

async function copyOne(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制本段文字')
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

/** 本地 fallback：简单的"不可识别"占位——真正可用的纯前端 OCR 需要 tesseract.js，本实现刻意不接入避免 10MB+ 依赖。 */
async function localOcr(file: File): Promise<string> {
  void file
  return '[本地未启用 OCR 引擎]\n请在「个人中心 → 后端加速」开启后端，以获得稳定的多语言识别结果。'
}

async function run() {
  if (!files.value.length) return
  processing.value = true
  progress.value = 0
  results.value = []
  try {
    const n = files.value.length
    for (let i = 0; i < n; i++) {
      const item = files.value[i]
      item.status = 'process'
      item.progress = 10
      try {
        const file = (item as unknown as { _file: File })._file
        let text: string
        if (backend.value.enabled) {
          const fd = new FormData()
          fd.append('file', file)
          fd.append('lang', 'chi_sim+eng')
          const r = await backendFetch('/ocr', fd, { timeoutMs: 180_000 })
          if (!r.ok) throw new Error(r.message)
          text = await r.blob.text()
        } else {
          text = await localOcr(file)
        }
        item.status = 'done'
        item.progress = 100
        results.value.push({ id: item.id, name: item.name, text })
      } catch (err) {
        item.status = 'error'
        item.message = err instanceof Error ? err.message : '失败'
      } finally {
        progress.value = Math.round(((i + 1) / n) * 100)
      }
    }
    rebuildCombined()
    ElMessage.success(results.value.length ? `已识别 ${results.value.length} 张` : '无可用结果')
  } finally {
    processing.value = false
  }
}

async function copyAll() {
  if (!combinedText.value) return
  await navigator.clipboard.writeText(combinedText.value)
  ElMessage.success('已复制全部文字')
}

onBeforeUnmount(() => {
  files.value.forEach((f) => f.previewUrl && URL.revokeObjectURL(f.previewUrl))
})
</script>

<template>
  <ToolHeader title="OCR 文字识别" description="上传图片 / 截图，提取里面的文字（推荐开启后端获得更高精度、支持手写/中英混排）。">
    <template #statusTop>
      <span class="text-xs" :class="backend.enabled ? 'text-success' : 'text-warning'">
        {{ backend.enabled ? '✓ 后端高精度模式' : '⚠ 本地基础降级模式（占位说明）' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-6xl py-6">
    <ProcessSteps :steps="steps" />

    <div v-if="!backend.enabled" class="card p-4 mb-4"
      style="border-color: var(--c-warning); background: color-mix(in srgb, var(--c-warning) 8%, var(--c-card))">
      <div class="font-semibold mb-1">当前使用降级模式</div>
      <p class="text-xs text-text-soft mb-2 leading-relaxed">
        为避免引入数十 MB 的 OCR 模型文件，本地降级模式仅输出提示。推荐开启后端，获得多语言 + 高精度识别。
      </p>
      <RouterLink to="/me" class="btn-primary">去开启后端加速</RouterLink>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div>
        <FileDropZone
          accept="image/*"
          hint="支持 PNG / JPG / WebP / BMP / GIF，可批量"
          chunk-label="① 上传图片"
          :current-count="files.length"
          :max-size="40 * 1024 * 1024"
          @files="addFiles"
        />
        <div v-if="!files.length" class="empty-block">
          <el-icon :size="34" class="mb-2"><Picture /></el-icon>
          <div>还没有图片</div>
          <p class="text-xs text-text-mute mt-1">上传要识别的图片或截图</p>
        </div>
        <BatchFileList
          :items="files"
          previewable
          @remove="remove"
          @move="move"
          @clear-all="clearAll"
          @preview="openPreview"
        />
        <div class="card p-4 mt-2">
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="btn-primary"
              :disabled="!files.length || processing"
              @click="run"
            >
              <el-icon :size="16"><Reading /></el-icon>
              {{ processing ? `识别中 ${progress}%` : `开始识别（${files.length} 张 · ${formatBytes(files.reduce((s, x) => s + x.size, 0))}）` }}
            </button>
            <button
              class="btn-primary"
              :disabled="!combinedText || processing"
              @click="copyAll"
            >
              <el-icon :size="16"><CopyDocument /></el-icon>
              复制全部文字
            </button>
          </div>
        </div>
      </div>

      <div>
        <div class="text-sm font-semibold mb-2">识别结果</div>

        <div v-if="!sortedResults.length" class="empty-block">
          <el-icon :size="34" class="mb-2"><Reading /></el-icon>
          <div>还没有识别结果</div>
          <p class="text-xs text-text-mute mt-1">上传图片后点击「开始识别」，每张图的文字将分段展示</p>
        </div>

        <!-- 分段编排：每张图一段，可独立编辑 / 复制，缩略图可点击放大对照 -->
        <div v-else class="space-y-3">
          <div v-for="r in sortedResults" :key="r.id" class="card p-3">
            <div class="flex items-center gap-2 mb-2">
              <img
                v-if="previewOf(r.id)"
                :src="previewOf(r.id)"
                :alt="r.name"
                class="w-8 h-8 rounded-md object-cover border border-border cursor-zoom-in shrink-0"
                title="点击预览原图"
                @click="openPreviewById(r.id)"
              />
              <el-icon v-else :size="16" class="text-text-mute shrink-0"><Picture /></el-icon>
              <span class="text-sm font-medium truncate flex-1" :title="r.name">{{ r.name }}</span>
              <button
                class="btn-ghost !py-1 !px-1.5 text-xs shrink-0"
                title="复制本段"
                :disabled="!r.text"
                @click="copyOne(r.text)"
              >
                <el-icon :size="14"><CopyDocument /></el-icon>
              </button>
            </div>
            <el-input
              v-model="r.text"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 12 }"
              placeholder="本段识别文字，可直接编辑。"
              @input="rebuildCombined"
            />
          </div>

          <!-- 合并全文：由分段实时拼接，可继续整体编辑 -->
          <div class="card p-2">
            <div class="text-xs text-text-soft font-medium px-1 mb-1">
              合并全文（按列表顺序自动拼接，可继续整体编辑）
            </div>
            <el-input
              v-model="combinedText"
              type="textarea"
              :autosize="{ minRows: 5, maxRows: 10 }"
              placeholder="所有分段文字将自动合并到此处。"
            />
          </div>
        </div>

        <p class="text-xs text-text-mute mt-2 leading-relaxed">
          点击左侧缩略图可放大预览原图；分段文字可直接编辑并同步到合并全文；左侧列表 ↑↓ 调整顺序后自动重新拼接。
        </p>
      </div>
    </div>

    <!-- 全屏大图预览 -->
    <el-image-viewer
      v-if="viewerVisible"
      :url-list="viewerUrls"
      :initial-index="viewerIndex"
      teleported
      @close="viewerVisible = false"
    />
  </section>
</template>
