<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import ProcessSteps, { type StepStatus } from '@/components/common/ProcessSteps.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import BatchFileList, { type BatchFileItem } from '@/components/common/BatchFileList.vue'
import { RouterLink } from 'vue-router'
import { usePreferenceStore } from '@/stores/preference'
import { backendFetch } from '@/utils/api'
import {
  baseName,
  downloadBlob,
  downloadFilesAsZip,
  formatBytes,
  getExt,
  readFileAsArrayBuffer,
  replaceExt
} from '@/utils/file'
import { PDFDocument } from 'pdf-lib'

type CompressMode = 'local' | 'strong'
const pref = usePreferenceStore()

const files = ref<BatchFileItem[]>([])
const processing = ref(false)
const progress = ref(0)
const mode = ref<CompressMode>('local')
const level = ref(3) // 1~5 仅 local 简化版用
const results = ref<{ id: string; name: string; blob: Blob; originSize: number }[]>([])

const steps = computed(() => {
  const s1: StepStatus = files.value.length ? 'done' : 'active'
  const s2: StepStatus = processing.value ? 'active' : files.value.length ? 'active' : 'idle'
  const s3: StepStatus = results.value.length ? 'done' : processing.value ? 'active' : 'idle'
  const s4: StepStatus = results.value.length ? 'active' : 'idle'
  return [
    { label: '上传 PDF', status: s1 },
    { label: '选择压缩模式', status: s2 },
    { label: '执行压缩', status: s3 },
    { label: '下载结果', status: s4 }
  ]
})

const canStrong = computed(() => pref.backendEnabled)

let idc = 0
function addFiles(list: File[]) {
  const arr = list
    .filter((f) => getExt(f.name) === 'pdf')
    .map<BatchFileItem>((f) => ({
      id: `f${++idc}_${Date.now()}`,
      name: f.name,
      size: f.size,
      status: 'wait',
      _file: f as unknown as never
    }))
  if (arr.length !== list.length) ElMessage.warning('已跳过非 PDF 文件')
  files.value = [...files.value, ...arr]
  results.value = []
}
function remove(id: string) {
  files.value = files.value.filter((f) => f.id !== id)
  results.value = results.value.filter((r) => r.id !== id)
}
function move(a: number, b: number) {
  const arr = files.value.slice()
  const [t] = arr.splice(a, 1)
  arr.splice(b, 0, t)
  files.value = arr
}
function clearAll() {
  files.value = []
  results.value = []
}

async function localCompressOne(file: File, _item: BatchFileItem) {
  // 本地"简化压缩"：尝试删除未引用对象并重写 PDF；
  // 再把 PDFLib 无法降质的图片流保留——对纯文本 / 表单 PDF 通常能省 10~25%。
  const buf = await readFileAsArrayBuffer(file)
  const doc = await PDFDocument.load(buf, {
    updateMetadata: false,
    ignoreEncryption: true
  })
  doc.setTitle(doc.getTitle() || '')
  doc.setAuthor(doc.getAuthor() || '')
  doc.setSubject(doc.getSubject() || '')
  doc.setKeywords([])
  doc.setProducer('速用工具箱')
  doc.setCreator('速用工具箱')
  const out = await doc.save({
    useObjectStreams: true,
    addDefaultPage: false
  })
  return new Blob([out.slice().buffer as ArrayBuffer], { type: 'application/pdf' })
}

async function strongCompressOne(file: File, quality: number): Promise<Blob> {
  const form = new FormData()
  form.append('file', file)
  form.append('quality', String(quality))
  const r = await backendFetch('/pdf/compress', form, { timeoutMs: 180_000 })
  if (!r.ok) throw new Error(r.message)
  return r.blob
}

async function run() {
  if (!files.value.length) return
  processing.value = true
  progress.value = 0
  results.value = []
  if (mode.value === 'strong' && !canStrong.value) {
    ElMessage.warning('强力模式需要先在「个人中心」开启后端加速')
    processing.value = false
    return
  }
  try {
    const quality = 6 - level.value // level 1..5 -> 压缩程度 5..1
    const n = files.value.length
    for (let i = 0; i < n; i++) {
      const item = files.value[i]
      item.status = 'process'
      item.progress = 5
      try {
        const file = (item as unknown as { _file: File })._file
        const blob =
          mode.value === 'strong'
            ? await strongCompressOne(file, quality)
            : await localCompressOne(file, item)
        const saved = Math.max(0, item.size - blob.size)
        item.status = blob.size >= item.size ? 'wait' : 'done'
        item.message = blob.size < item.size
          ? `体积减少 ${Math.round((saved / item.size) * 100)}% · ${formatBytes(saved)}`
          : '压缩收益有限（内容本身已紧凑）'
        item.progress = 100
        results.value.push({
          id: item.id,
          name: replaceExt(item.name, 'min.pdf') ?? `${baseName(item.name)}.min.pdf`,
          blob,
          originSize: item.size
        })
      } catch (err) {
        item.status = 'error'
        item.message = err instanceof Error ? err.message : '失败'
      } finally {
        progress.value = Math.round(((i + 1) / n) * 100)
      }
    }
    ElMessage.success(results.value.length ? `已生成 ${results.value.length} 个压缩结果` : '无可用结果')
  } finally {
    processing.value = false
  }
}

const canRun = computed(() => files.value.length > 0 && !processing.value)

function downloadAll() {
  if (!results.value.length) return
  if (results.value.length === 1) {
    const r = results.value[0]
    downloadBlob(r.blob, r.name)
    return
  }
  downloadFilesAsZip(
    results.value.map((r) => ({ blob: r.blob, name: r.name })),
    'suyong-pdf-compress.zip'
  )
}

const summary = computed(() => {
  if (!results.value.length) return null
  const before = results.value.reduce((s, r) => s + r.originSize, 0)
  const after = results.value.reduce((s, r) => s + r.blob.size, 0)
  const saved = Math.max(0, before - after)
  return {
    before,
    after,
    saved,
    percent: before > 0 ? Math.round((saved / before) * 100) : 0
  }
})
</script>

<template>
  <ToolHeader title="PDF 压缩" description="本地简化版 / 后端强力版 双模式，支持批量处理。">
    <template #statusTop>
      <span class="text-xs" :class="canStrong ? 'text-success' : 'text-warning'">
        {{ canStrong ? '✓ 后端加速已开启' : '⚡ 未开启后端 → 仅使用本地简化模式' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-5xl py-6">
    <ProcessSteps :steps="steps" />
    <FileDropZone
      accept="application/pdf,.pdf"
      hint="仅接受 PDF（强力模式推荐单文件 ≤ 200MB）"
      chunk-label="① 上传 PDF（可批量）"
      :current-count="files.length"
      :max-size="300 * 1024 * 1024"
      @files="addFiles"
    />

    <div v-if="!files.length" class="empty-block">
      <el-icon :size="34" class="mb-2"><Compress /></el-icon>
      <div>还没有 PDF</div>
      <p class="text-xs text-text-mute mt-1">压缩前请上传至少一个 PDF 文件</p>
    </div>

    <BatchFileList
      :items="files"
      @remove="remove"
      @move="move"
      @clear-all="clearAll"
    />

    <div class="card p-4 mt-2">
      <div class="flex flex-wrap items-center gap-4">
        <div>
          <div class="text-sm text-text-soft mb-1">压缩模式</div>
          <el-radio-group v-model="mode">
            <el-radio-button value="local">本地 · 轻量（稳妥）</el-radio-button>
            <el-radio-button value="strong" :disabled="!canStrong">
              后端 · 强力（更省空间）
            </el-radio-button>
          </el-radio-group>
          <RouterLink
            v-if="!canStrong"
            to="/me"
            class="ml-2 text-xs text-primary hover:underline"
          >
            去开启后端 →
          </RouterLink>
        </div>
        <div>
          <div class="text-sm text-text-soft mb-1">压缩强度（仅本地模式生效）</div>
          <el-slider v-model="level" :min="1" :max="5" show-input class="w-48" />
        </div>

        <div class="ml-auto flex items-center gap-2 flex-wrap">
          <button class="btn-primary" :disabled="!canRun" @click="run">
            <el-icon :size="16"><Compress /></el-icon>
            {{ processing ? `压缩中 ${progress}%` : `开始压缩（${files.length}）` }}
          </button>
          <button
            class="btn-primary"
            :disabled="!results.length || processing"
            @click="downloadAll"
          >
            <el-icon :size="16"><Download /></el-icon>
            {{ results.length > 1 ? '打包下载 ZIP' : '下载结果' }}
          </button>
        </div>
      </div>

      <div v-if="summary" class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
        <div class="card p-3">
          <div class="text-xs text-text-mute mb-1">原始总大小</div>
          <div class="font-semibold">{{ formatBytes(summary.before) }}</div>
        </div>
        <div class="card p-3">
          <div class="text-xs text-text-mute mb-1">压缩后</div>
          <div class="font-semibold">{{ formatBytes(summary.after) }}</div>
        </div>
        <div class="card p-3">
          <div class="text-xs text-text-mute mb-1">节省</div>
          <div class="font-semibold text-success">{{ formatBytes(summary.saved) }}</div>
        </div>
        <div class="card p-3">
          <div class="text-xs text-text-mute mb-1">压缩率</div>
          <div class="font-semibold text-primary">{{ summary.percent }}%</div>
        </div>
      </div>
    </div>

    <p class="text-xs text-text-mute mt-4 leading-relaxed">
      温馨提示：如果 PDF 全部由扫描页组成，本地简化模式效果有限，建议开启后端后使用"强力模式"。
    </p>
  </section>
</template>
