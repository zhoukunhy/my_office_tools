<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { PDFDocument } from 'pdf-lib'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import ProcessSteps, { type StepStatus } from '@/components/common/ProcessSteps.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import BatchFileList, { type BatchFileItem } from '@/components/common/BatchFileList.vue'
import { downloadBlob, formatBytes, getExt, readFileAsArrayBuffer } from '@/utils/file'

const files = ref<BatchFileItem[]>([])
const processing = ref(false)
const progress = ref(0)
const resultBlob = ref<Blob | null>(null)
const resultSize = ref(0)

const steps = computed(() => {
  const s1: StepStatus = files.value.length ? 'done' : 'active'
  const s2: StepStatus = processing.value ? 'active' : files.value.length ? 'active' : 'idle'
  const s3: StepStatus = resultBlob.value ? 'done' : processing.value ? 'active' : 'idle'
  const s4: StepStatus = resultBlob.value ? 'active' : 'idle'
  return [
    { label: '上传文件', status: s1, icon: 'UploadFilled' },
    { label: '调整顺序', status: s2, icon: 'Rank' },
    { label: '合并处理', status: s3, icon: 'SetUp' },
    { label: '下载结果', status: s4, icon: 'Download' }
  ]
})

let counter = 0
function addFiles(incoming: File[]) {
  const onlyPdf = incoming.filter((f) => getExt(f.name) === 'pdf')
  if (onlyPdf.length !== incoming.length) {
    ElMessage.warning('已自动跳过非 PDF 文件')
  }
  const list = onlyPdf.map<BatchFileItem>((f) => ({
    id: `f${++counter}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name: f.name,
    size: f.size,
    status: 'wait',
    previewUrl: undefined,
    // 保留 File 对象引用，后续处理读 arrayBuffer
    _file: f as unknown as never
  }))
  files.value = [...files.value, ...list]
  resultBlob.value = null
}

function remove(id: string) {
  files.value = files.value.filter((f) => f.id !== id)
}
function move(from: number, to: number) {
  const arr = files.value.slice()
  const [t] = arr.splice(from, 1)
  arr.splice(to, 0, t)
  files.value = arr
}
function clearAll() {
  files.value = []
  resultBlob.value = null
}

const totalSize = computed(() => files.value.reduce((s, x) => s + x.size, 0))

async function processMerge() {
  if (!files.value.length) return
  processing.value = true
  progress.value = 0
  resultBlob.value = null
  try {
    const merged = await PDFDocument.create()
    const n = files.value.length
    for (let i = 0; i < n; i++) {
      const item = files.value[i]
      item.status = 'process'
      item.progress = 0
      const f = (item as unknown as { _file: File })._file
      const buf = await readFileAsArrayBuffer(f)
      const doc = await PDFDocument.load(buf)
      const indices = doc.getPageIndices()
      const pages = await merged.copyPages(doc, indices)
      pages.forEach((p) => merged.addPage(p))
      item.status = 'done'
      item.progress = 100
      progress.value = Math.round(((i + 1) / n) * 100)
    }
    const bytes = await merged.save()
    const blob = new Blob([bytes.slice().buffer as ArrayBuffer], {
      type: 'application/pdf'
    })
    resultBlob.value = blob
    resultSize.value = blob.size
    ElMessage.success(`合并完成，共 ${files.value.length} 个 PDF`)
  } catch (err) {
    files.value.forEach((f) => {
      if (f.status !== 'done') {
        f.status = 'error'
        f.message = err instanceof Error ? err.message : '处理失败'
      }
    })
    ElMessage.error('合并失败：' + (err instanceof Error ? err.message : '未知错误'))
  } finally {
    processing.value = false
  }
}

function download() {
  if (!resultBlob.value) return
  downloadBlob(resultBlob.value, `suyong-合并${files.value.length}个文件.pdf`)
}

const canProcess = computed(() => files.value.length >= 2 && !processing.value)
const canDownload = computed(() => !!resultBlob.value && !processing.value)

onBeforeUnmount(() => {
  files.value.forEach((f) => {
    if (f.previewUrl) URL.revokeObjectURL(f.previewUrl)
  })
})
</script>

<template>
  <ToolHeader title="PDF 合并" description="拖拽 / 选择多个 PDF，调整顺序后一键合并为一个文件，全程本地处理。">
    <template #statusTop>
      <div v-if="files.length" class="text-xs text-text-mute">
        共 {{ files.length }} 个 · {{ formatBytes(totalSize) }}
      </div>
    </template>
  </ToolHeader>

  <section class="container-page max-w-5xl py-6">
    <ProcessSteps :steps="steps" />

    <FileDropZone
      accept="application/pdf,.pdf"
      hint="仅接受 PDF，推荐单文件 ≤ 100MB"
      chunk-label="① 上传 PDF 文件（可多次追加）"
      :current-count="files.length"
      :max-size="150 * 1024 * 1024"
      @files="addFiles"
    />

    <div v-if="!files.length" class="empty-block">
      <el-icon :size="34" class="mb-2"><Files /></el-icon>
      <div>还没有 PDF 文件</div>
      <p class="text-xs mt-1 text-text-mute">需要至少 2 个 PDF 才能进行合并</p>
    </div>

    <BatchFileList
      :items="files"
      @remove="remove"
      @move="move"
      @clear-all="clearAll"
    />

    <div class="card p-4 mt-2">
      <div class="flex flex-wrap items-center gap-3">
        <button
          class="btn-primary"
          :disabled="!canProcess"
          @click="processMerge"
        >
          <el-icon :size="16"><SetUp /></el-icon>
          {{ processing ? `合并中 ${progress}%` : `开始合并（${files.length} 个 PDF）` }}
        </button>
        <button
          v-if="resultBlob"
          class="btn-primary"
          :disabled="!canDownload"
          @click="download"
        >
          <el-icon :size="16"><Download /></el-icon>
          下载结果 PDF
          <span v-if="resultSize" class="ml-1 text-[11px] opacity-80">
            · {{ formatBytes(resultSize) }}
          </span>
        </button>
        <span v-if="resultBlob" class="text-xs text-success ml-2">
          ✓ 处理完成，点击右侧按钮下载
        </span>
      </div>
    </div>

    <p class="text-xs text-text-mute mt-4 leading-relaxed">
      提示：合并前可在上方列表使用上下箭头调整各 PDF 的先后顺序，点击
      <el-icon :size="12"><Close /></el-icon> 可单独删除某一项。
    </p>
  </section>
</template>
