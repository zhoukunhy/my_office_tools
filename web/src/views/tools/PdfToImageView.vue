<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadFilesAsZip, baseName } from '@/utils/file'
import { loadPdf, renderPageToBlob, type PdfDoc } from '@/utils/pdf'

interface PdfFile {
  file: File
  pages: number
  doc?: PdfDoc
}

const files = ref<PdfFile[]>([])
const format = ref<'png' | 'jpeg'>('png')
const scale = ref(2)
const quality = ref(0.92)
const processing = ref(false)
const progress = ref(0)

async function onFiles(list: File[]) {
  for (const f of list.filter((x) => x.type === 'application/pdf' || x.name.endsWith('.pdf'))) {
    try {
      const buf = await f.arrayBuffer()
      const doc = await loadPdf(buf)
      files.value.push({ file: f, pages: doc.numPages, doc })
    } catch {
      ElMessage.error(`加载失败：${f.name}`)
    }
  }
}

function remove(idx: number) {
  files.value.splice(idx, 1)
}
function clearAll() {
  files.value.forEach((f) => f.doc?.destroy())
  files.value = []
}

const totalPages = () => files.value.reduce((s, f) => s + f.pages, 0)

async function convert() {
  if (!files.value.length) return
  processing.value = true
  progress.value = 0
  try {
    const outs: { blob: Blob; name: string }[] = []
    const total = totalPages()
    let done = 0
    for (const pf of files.value) {
      if (!pf.doc) continue
      const doc = pf.doc
      const base = baseName(pf.file.name)
      for (let p = 1; p <= pf.pages; p++) {
        const blob = await renderPageToBlob(
          doc,
          p,
          format.value === 'png' ? 'image/png' : 'image/jpeg',
          scale.value,
          quality.value
        )
        const ext = format.value === 'png' ? 'png' : 'jpg'
        outs.push({ blob, name: `${base}_p${String(p).padStart(2, '0')}.${ext}` })
        done++
        progress.value = Math.round((done / total) * 100)
      }
    }
    await downloadFilesAsZip(outs, 'pdf转图片.zip')
    ElMessage.success(`转换完成，共导出 ${outs.length} 张图片`)
  } catch (e) {
    ElMessage.error('转换失败：' + (e as Error).message)
  } finally {
    processing.value = false
    progress.value = 0
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <FileDropZone accept="application/pdf" hint="支持多 PDF 批量转换" @files="onFiles" />

    <div v-if="files.length" class="card p-5 space-y-4">
      <div class="flex items-center justify-between">
        <span class="font-medium">已加载 {{ files.length }} 个 PDF，共 {{ totalPages() }} 页</span>
        <button class="btn-ghost text-text-mute" @click="clearAll">清空</button>
      </div>
      <ul class="space-y-1 max-h-40 overflow-auto">
        <li v-for="(f, i) in files" :key="i" class="flex items-center gap-2 text-sm py-1">
          <el-icon class="text-text-mute"><Document /></el-icon>
          <span class="truncate flex-1">{{ f.file.name }}</span>
          <span class="text-xs text-text-mute">{{ f.pages }} 页 · {{ formatBytes(f.file.size) }}</span>
          <button class="btn-ghost !px-1 hover:text-red-500" @click="remove(i)">
            <el-icon><Delete /></el-icon>
          </button>
        </li>
      </ul>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label class="text-sm text-text-soft block mb-1">输出格式</label>
          <el-radio-group v-model="format">
            <el-radio value="png">PNG</el-radio>
            <el-radio value="jpeg">JPG</el-radio>
          </el-radio-group>
        </div>
        <div>
          <label class="text-sm text-text-soft block mb-1">清晰度（缩放倍率）</label>
          <el-input-number v-model="scale" :min="1" :max="4" :step="0.5" />
        </div>
        <div v-if="format === 'jpeg'">
          <label class="text-sm text-text-soft block mb-1">JPG 质量</label>
          <el-slider v-model="quality" :min="0.5" :max="1" :step="0.01" />
        </div>
      </div>

      <div v-if="processing" class="text-center text-sm text-text-soft">
        <el-progress :percentage="progress" :stroke-width="6" />
        <span class="block mt-2">正在渲染页面…{{ progress }}%</span>
      </div>

      <button class="btn-primary w-full" :disabled="processing" @click="convert">
        <el-icon v-if="processing" class="animate-spin"><Loading /></el-icon>
        <el-icon v-else><Download /></el-icon>
        {{ processing ? '正在转换…' : '转换并下载（ZIP）' }}
      </button>
    </div>

    <p class="text-xs text-text-mute text-center">
      提示：清晰度越高图片越清晰、文件越大；建议 2 倍清晰度兼顾质量与体积。
    </p>
  </div>
</template>
