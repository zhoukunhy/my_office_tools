<script setup lang="ts">
import { computed, ref } from 'vue'
import { PDFDocument } from 'pdf-lib'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadFilesAsZip, bytesToBlob } from '@/utils/file'

type Mode = 'ranges' | 'every'

const file = ref<File | null>(null)
const pageCount = ref(0)
const fileSize = ref(0)
const mode = ref<Mode>('ranges')
const rangeInput = ref('1-1')
const everyN = ref(1)
const processing = ref(false)
const loading = ref(false)

async function onFiles(files: File[]) {
  const f = files[0]
  if (!f) return
  loading.value = true
  try {
    const buf = await f.arrayBuffer()
    const doc = await PDFDocument.load(buf, { ignoreEncryption: true })
    file.value = f
    pageCount.value = doc.getPageCount()
    fileSize.value = f.size
    rangeInput.value = `1-${pageCount.value}`
  } catch {
    ElMessage.error('PDF 加载失败，文件可能损坏或加密')
  } finally {
    loading.value = false
  }
}

function reset() {
  file.value = null
  pageCount.value = 0
}

/** 解析 "1-3,4,5-7" 为页码组（1 基，含两端） */
function parseRanges(input: string, max: number): number[][] {
  const groups: number[][] = []
  for (const part of input.split(/[,，]/)) {
    const trimmed = part.trim()
    if (!trimmed) continue
    const m = trimmed.match(/^(\d+)\s*[-~]\s*(\d+)$/)
    if (m) {
      let a = parseInt(m[1], 10)
      let b = parseInt(m[2], 10)
      if (a > b) [a, b] = [b, a]
      a = Math.max(1, a)
      b = Math.min(max, b)
      if (a <= b) groups.push(rangeArr(a, b))
    } else if (/^\d+$/.test(trimmed)) {
      const n = parseInt(trimmed, 10)
      if (n >= 1 && n <= max) groups.push([n])
    } else {
      throw new Error(`无法识别的页码：${trimmed}`)
    }
  }
  return groups
}
function rangeArr(a: number, b: number) {
  const r: number[] = []
  for (let i = a; i <= b; i++) r.push(i)
  return r
}

const expectedFiles = computed(() => {
  if (!pageCount.value) return 0
  if (mode.value === 'ranges') {
    try {
      return parseRanges(rangeInput.value, pageCount.value).length
    } catch {
      return 0
    }
  }
  return Math.ceil(pageCount.value / Math.max(1, everyN.value))
})

async function split() {
  if (!file.value) return
  processing.value = true
  try {
    const buf = await file.value.arrayBuffer()
    const src = await PDFDocument.load(buf, { ignoreEncryption: true })
    const total = src.getPageCount()
    const groups: number[][] =
      mode.value === 'ranges'
        ? parseRanges(rangeInput.value, total)
        : everyGroups(total, Math.max(1, everyN.value))

    if (!groups.length) {
      ElMessage.warning('未生成有效拆分范围')
      return
    }

    const outs: { blob: Blob; name: string }[] = []
    for (let i = 0; i < groups.length; i++) {
      const out = await PDFDocument.create()
      const pages = await out.copyPages(src, groups[i].map((n) => n - 1))
      pages.forEach((p) => out.addPage(p))
      const bytes = await out.save()
      outs.push({
        blob: bytesToBlob(bytes, 'application/pdf'),
        name: `拆分_${i + 1}_页${groups[i][0]}-${groups[i][groups[i].length - 1]}.pdf`
      })
    }
    await downloadFilesAsZip(outs, `${file.value.name.replace(/\.pdf$/i, '')}_拆分.zip`)
    ElMessage.success(`拆分完成，共生成 ${outs.length} 个文件`)
  } catch (e) {
    ElMessage.error('拆分失败：' + (e as Error).message)
  } finally {
    processing.value = false
  }
}

function everyGroups(total: number, n: number) {
  const groups: number[][] = []
  for (let i = 1; i <= total; i += n) {
    groups.push(rangeArr(i, Math.min(i + n - 1, total)))
  }
  return groups
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <FileDropZone
      v-if="!file"
      accept="application/pdf"
      :multiple="false"
      hint="选择单个 PDF 文件进行拆分"
      @files="onFiles"
    />

    <div v-else class="card p-5 space-y-5">
      <div class="flex items-center gap-3">
        <el-icon class="text-text-mute"><Document /></el-icon>
        <div class="min-w-0 flex-1">
          <div class="font-medium truncate">{{ file.name }}</div>
          <div class="text-xs text-text-mute">
            {{ pageCount }} 页 · {{ formatBytes(fileSize) }}
          </div>
        </div>
        <button class="btn-ghost" @click="reset">重新选择</button>
      </div>

      <el-radio-group v-model="mode">
        <el-radio-button value="ranges">按页码范围拆分</el-radio-button>
        <el-radio-button value="every">每 N 页一个文件</el-radio-button>
      </el-radio-group>

      <div v-if="mode === 'ranges'">
        <label class="text-sm text-text-soft block mb-1">页码范围（用逗号分隔，如 1-3,4,5-7）</label>
        <el-input v-model="rangeInput" placeholder="1-3,4,5-7" />
        <p class="text-xs text-text-mute mt-1">每个范围输出一个 PDF；总页数 {{ pageCount }}</p>
      </div>
      <div v-else>
        <label class="text-sm text-text-soft block mb-1">每 N 页切分为一个文件</label>
        <el-input-number v-model="everyN" :min="1" :max="pageCount" />
      </div>

      <div class="text-sm text-text-soft">预计生成 {{ expectedFiles }} 个文件</div>

      <button class="btn-primary w-full" :disabled="processing || loading" @click="split">
        <el-icon v-if="processing" class="animate-spin"><Loading /></el-icon>
        <el-icon v-else><Download /></el-icon>
        {{ processing ? '正在拆分…' : '拆分并下载（ZIP）' }}
      </button>
    </div>
  </div>
</template>
