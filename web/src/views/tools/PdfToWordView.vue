<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RouterLink } from 'vue-router'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import ProcessSteps, { type StepStatus } from '@/components/common/ProcessSteps.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import BatchFileList, { type BatchFileItem } from '@/components/common/BatchFileList.vue'
import { backendFetch, getBackendStatus } from '@/utils/api'
import {
  downloadBlob,
  downloadFilesAsZip,
  formatBytes,
  getExt,
  replaceExt
} from '@/utils/file'

const backend = computed(() => getBackendStatus())

const files = ref<BatchFileItem[]>([])
const processing = ref(false)
const progress = ref(0)
const results = ref<{ id: string; name: string; blob: Blob }[]>([])

const steps = computed(() => {
  const s1: StepStatus = files.value.length ? 'done' : 'active'
  const s2: StepStatus = processing.value ? 'active' : files.value.length ? 'active' : 'idle'
  const s3: StepStatus = results.value.length ? 'done' : processing.value ? 'active' : 'idle'
  const s4: StepStatus = results.value.length ? 'active' : 'idle'
  return [
    { label: '上传 PDF', status: s1 },
    { label: '启动后端转换', status: s2 },
    { label: '转换', status: s3 },
    { label: '下载 Word', status: s4 }
  ]
})

let idc = 0
function addFiles(list: File[]) {
  const ok = list.filter((f) => getExt(f.name) === 'pdf')
  if (ok.length !== list.length) ElMessage.warning('已跳过非 PDF 文件')
  files.value = [
    ...files.value,
    ...ok.map<BatchFileItem>((f) => ({
      id: `f${++idc}_${Date.now()}`,
      name: f.name,
      size: f.size,
      status: 'wait',
      _file: f
    }))
  ]
  results.value = []
}
function remove(id: string) {
  files.value = files.value.filter((f) => f.id !== id)
  results.value = results.value.filter((r) => r.id !== id)
}
function clearAll() {
  files.value = []
  results.value = []
}
function move(a: number, b: number) {
  const arr = files.value.slice()
  const [t] = arr.splice(a, 1)
  arr.splice(b, 0, t)
  files.value = arr
}

async function run() {
  if (!backend.value.enabled) {
    ElMessage.warning('请先在「个人中心」开启后端加速')
    return
  }
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
        const fd = new FormData()
        fd.append('file', file)
        const r = await backendFetch('/convert/pdf-to-word', fd, { timeoutMs: 300_000 })
        if (!r.ok) throw new Error(r.message)
        item.status = 'done'
        item.progress = 100
        results.value.push({
          id: item.id,
          name: r.filename || (replaceExt(item.name, 'docx') ?? `${item.name}.docx`),
          blob: r.blob
        })
      } catch (err) {
        item.status = 'error'
        item.message = err instanceof Error ? err.message : '转换失败'
      } finally {
        progress.value = Math.round(((i + 1) / n) * 100)
      }
    }
    ElMessage.success(results.value.length ? `成功转换 ${results.value.length} 个` : '无可用结果')
  } finally {
    processing.value = false
  }
}

function download() {
  if (!results.value.length) return
  if (results.value.length === 1) {
    downloadBlob(results.value[0].blob, results.value[0].name)
    return
  }
  downloadFilesAsZip(
    results.value.map((r) => ({ blob: r.blob, name: r.name })),
    'pdf-to-word.zip'
  )
}

const totalIn = computed(() => formatBytes(files.value.reduce((s, x) => s + x.size, 0)))
</script>

<template>
  <ToolHeader
    title="PDF 转 Word"
    description="批量将 PDF 转换为可编辑 DOCX（需后端加速能力）"
  >
    <template #statusTop>
      <span class="text-xs" :class="backend.enabled ? 'text-success' : 'text-warning'">
        {{ backend.enabled ? '✓ 后端加速已开启' : '⚡ 未开启后端，本功能无法执行' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-5xl py-6">
    <ProcessSteps :steps="steps" />

    <div v-if="!backend.enabled" class="card p-4 mb-4"
      style="border-color: var(--c-warning); background: color-mix(in srgb, var(--c-warning) 8%, var(--c-card))">
      <div class="font-semibold mb-1">本功能需要后端加速才能运行</div>
      <p class="text-xs text-text-soft mb-2 leading-relaxed">
        PDF → Word 纯前端还原效果有限，需要后端 LibreOffice / OCR 组合处理更稳定。
      </p>
      <RouterLink to="/me" class="btn-primary">去开启后端加速</RouterLink>
    </div>

    <FileDropZone
      accept="application/pdf,.pdf"
      hint="仅接受 PDF"
      chunk-label="① 上传 PDF 文件"
      :current-count="files.length"
      :max-size="150 * 1024 * 1024"
      @files="addFiles"
    />
    <div v-if="!files.length" class="empty-block">
      <el-icon :size="34" class="mb-2"><Document /></el-icon>
      <div>还没有 PDF</div>
      <p class="text-xs text-text-mute mt-1">请上传 PDF 以转换为 Word</p>
    </div>

    <BatchFileList
      :items="files"
      @remove="remove"
      @move="move"
      @clear-all="clearAll"
    />

    <div class="card p-4 mt-2">
      <div class="flex flex-wrap items-center gap-2">
        <button
          class="btn-primary"
          :disabled="!files.length || processing || !backend.enabled"
          @click="run"
        >
          <el-icon :size="16"><Promotion /></el-icon>
          {{ processing ? `转换中 ${progress}%` : `开始转换（${files.length} 个 · ${totalIn}）` }}
        </button>
        <button
          class="btn-primary"
          :disabled="!results.length || processing"
          @click="download"
        >
          <el-icon :size="16"><Download /></el-icon>
          {{ results.length > 1 ? '打包下载 ZIP' : '下载 Word' }}
        </button>
        <span v-if="results.length" class="text-xs text-success ml-2">✓ {{ results.length }} 个已完成</span>
      </div>
    </div>
  </section>
</template>
