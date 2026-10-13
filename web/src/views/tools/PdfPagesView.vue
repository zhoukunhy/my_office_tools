<script setup lang="ts">
import { computed, ref } from 'vue'
import { degrees, PDFDocument } from 'pdf-lib'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { downloadBlob, bytesToBlob } from '@/utils/file'
import { loadPdf, renderPageToCanvas, type PdfDoc } from '@/utils/pdf'

interface PageThumb {
  index: number // 0-based
  dataUrl: string
  deleted: boolean
  rotation: number // 相对旋转 0/90/180/270
  baseRotation: number // 原始旋转（来自 pdf-lib）
}

const file = ref<File | null>(null)
const pages = ref<PageThumb[]>([])
const processing = ref(false)
const loading = ref(false)
const renderDoc = ref<PdfDoc | null>(null)

async function onFiles(files: File[]) {
  const f = files[0]
  if (!f) return
  loading.value = true
  try {
    const buf = await f.arrayBuffer()
    const render = await loadPdf(buf.slice(0))
    renderDoc.value = render
    const src = await PDFDocument.load(buf, { ignoreEncryption: true })
    const total = src.getPageCount()
    const list: PageThumb[] = []
    for (let i = 0; i < total; i++) {
      const baseRotation = src.getPage(i).getRotation().angle
      const canvas = await renderPageToCanvas(render, i + 1, 0.5)
      list.push({
        index: i,
        dataUrl: canvas.toDataURL('image/jpeg', 0.7),
        deleted: false,
        rotation: 0,
        baseRotation
      })
    }
    file.value = f
    pages.value = list
  } catch (e) {
    ElMessage.error('加载失败：' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

function rotate(i: number, delta: number) {
  pages.value[i].rotation = (pages.value[i].rotation + delta + 360) % 360
}
function toggleDelete(i: number) {
  pages.value[i].deleted = !pages.value[i].deleted
}

const activePages = computed(() => pages.value.filter((p) => !p.deleted).length)

function reset() {
  renderDoc.value?.destroy()
  renderDoc.value = null
  file.value = null
  pages.value = []
}

async function exportPdf() {
  if (!file.value) return
  const keep = pages.value.filter((p) => !p.deleted)
  if (!keep.length) {
    ElMessage.warning('请至少保留一页')
    return
  }
  processing.value = true
  try {
    const buf = await file.value.arrayBuffer()
    const src = await PDFDocument.load(buf, { ignoreEncryption: true })
    const out = await PDFDocument.create()
    const copied = await out.copyPages(src, keep.map((p) => p.index))
    copied.forEach((page, i) => {
      const meta = keep[i]
      page.setRotation(degrees((meta.baseRotation + meta.rotation) % 360))
      out.addPage(page)
    })
    const bytes = await out.save()
    downloadBlob(bytesToBlob(bytes, 'application/pdf'), `${file.value.name.replace(/\.pdf$/i, '')}_编辑.pdf`)
    ElMessage.success(`导出完成，共 ${keep.length} 页`)
  } catch (e) {
    ElMessage.error('导出失败：' + (e as Error).message)
  } finally {
    processing.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <FileDropZone
      v-if="!file"
      accept="application/pdf"
      :multiple="false"
      hint="选择 PDF，可删除页面、旋转方向后导出"
      @files="onFiles"
    />

    <div v-else class="space-y-4">
      <div class="card p-4 flex items-center gap-3">
        <el-icon class="text-text-mute"><Document /></el-icon>
        <div class="min-w-0 flex-1">
          <div class="font-medium truncate">{{ file.name }}</div>
          <div class="text-xs text-text-mute">
            共 {{ pages.length }} 页，保留 {{ activePages }} 页
          </div>
        </div>
        <button class="btn-ghost" @click="reset">重新选择</button>
        <button class="btn-primary" :disabled="processing || loading" @click="exportPdf">
          <el-icon v-if="processing" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><Download /></el-icon>
          {{ processing ? '导出中…' : '导出 PDF' }}
        </button>
      </div>

      <div v-if="loading" class="card p-12 text-center text-text-mute">
        <el-icon class="animate-spin" :size="24"><Loading /></el-icon>
        <p class="mt-2">正在生成页面预览…</p>
      </div>

      <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <div
          v-for="(p, i) in pages"
          :key="i"
          class="card overflow-hidden"
          :class="{ 'opacity-40 ring-2 ring-red-400': p.deleted }"
        >
          <div class="aspect-[3/4] bg-bg-soft flex items-center justify-center overflow-hidden">
            <img
              :src="p.dataUrl"
              :style="{ transform: `rotate(${p.rotation}deg)` }"
              class="max-w-full max-h-full transition-transform duration-300"
              :class="{ 'grayscale': p.deleted }"
              alt="page"
            />
          </div>
          <div class="p-2">
            <div class="text-xs text-center text-text-mute mb-2">第 {{ i + 1 }} 页</div>
            <div class="flex items-center justify-center gap-1">
              <button
                class="btn-ghost !px-1.5"
                title="向左旋转"
                @click="rotate(i, -90)"
              >
                <el-icon><RefreshLeft /></el-icon>
              </button>
              <button
                class="btn-ghost !px-1.5"
                title="向右旋转"
                @click="rotate(i, 90)"
              >
                <el-icon><RefreshRight /></el-icon>
              </button>
              <button
                class="btn-ghost !px-1.5"
                :class="p.deleted ? 'text-red-500' : 'hover:text-red-500'"
                :title="p.deleted ? '恢复' : '删除'"
                @click="toggleDelete(i)"
              >
                <el-icon><component :is="p.deleted ? 'RefreshLeft' : 'Delete'" /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
