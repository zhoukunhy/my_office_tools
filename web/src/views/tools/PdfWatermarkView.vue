<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import ProcessSteps, { type StepStatus } from '@/components/common/ProcessSteps.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { RouterLink } from 'vue-router'
import { usePreferenceStore } from '@/stores/preference'
import { resolveApiUrl, backendFetch } from '@/utils/api'
import { downloadBlob, formatBytes, baseName } from '@/utils/file'

type RemoveMode = 'all' | 'text' | 'image' | 'keyword'

interface WatermarkItem {
  id: string
  type: string
  text?: string
  page?: number
  pages?: number[]
  count?: number
  color?: string
  rect?: number[]
  xref?: number
  area_ratio?: number
  position?: number[]
}

const pref = usePreferenceStore()
const file = ref<File | null>(null)
const detecting = ref(false)
const removing = ref(false)
const progress = ref(0)
const detected = ref<{
  total: number
  textWatermarks: WatermarkItem[]
  imageWatermarks: WatermarkItem[]
} | null>(null)
const removeMode = ref<RemoveMode>('all')
const keywords = ref('')
const resultBlob = ref<Blob | null>(null)
const resultName = ref('')

const canUseBackend = computed(() => pref.backendEnabled)

const steps = computed<StepStatus[]>(() => {
  const s1: StepStatus = file.value ? 'done' : 'active'
  const s2: StepStatus = detecting.value ? 'active' : file.value ? 'active' : 'idle'
  const s3: StepStatus = removing.value ? 'active' : detected.value ? 'done' : 'idle'
  const s4: StepStatus = resultBlob.value ? 'done' : 'idle'
  return [
    { label: '上传 PDF', status: s1 },
    { label: '检测水印', status: s2 },
    { label: '移除水印', status: s3 },
    { label: '下载结果', status: s4 }
  ]
})

function onFiles(list: File[]) {
  const pdf = list.find((f) => f.name.toLowerCase().endsWith('.pdf'))
  if (!pdf) {
    ElMessage.warning('请上传 PDF 文件')
    return
  }
  file.value = pdf
  detected.value = null
  resultBlob.value = null
}

function clearFile() {
  file.value = null
  detected.value = null
  resultBlob.value = null
  keywords.value = ''
}

async function detect() {
  if (!file.value || !canUseBackend.value) return
  detecting.value = true
  progress.value = 10
  try {
    const url = resolveApiUrl('/pdf/watermark-detect')
    if (!url) {
      ElMessage.warning('请先在「个人中心」开启后端加速')
      return
    }
    const form = new FormData()
    form.append('file', file.value)
    progress.value = 50
    const resp = await fetch(url, { method: 'POST', body: form })
    progress.value = 80
    if (!resp.ok) {
      const msg = await resp.text().catch(() => '')
      throw new Error(`HTTP ${resp.status}${msg ? '：' + msg.slice(0, 200) : ''}`)
    }
    const data = await resp.json()
    detected.value = data
    progress.value = 100
    if (data.total === 0) {
      ElMessage.info('未检测到明显水印')
    } else {
      ElMessage.success(`检测到 ${data.total} 处可疑水印`)
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '检测失败')
  } finally {
    detecting.value = false
  }
}

async function removeWatermarks() {
  if (!file.value || !canUseBackend.value) return
  removing.value = true
  progress.value = 10
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('mode', removeMode.value)
    if (removeMode.value === 'keyword' && keywords.value) {
      form.append('keywords', keywords.value)
    }
    progress.value = 30
    const r = await backendFetch('/pdf/watermark-remove', form, { timeoutMs: 180_000 })
    progress.value = 80
    if (!r.ok) {
      throw new Error(r.message)
    }
    resultBlob.value = r.blob
    resultName.value = r.filename || `${baseName(file.value.name)}_no_watermark.pdf`
    progress.value = 100
    ElMessage.success('水印移除完成')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '移除失败')
  } finally {
    removing.value = false
  }
}

function download() {
  if (!resultBlob.value) return
  downloadBlob(resultBlob.value, resultName.value)
}

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    annotation: '注释水印',
    text: '灰色文字',
    text_repeat: '重复文本',
    image: '小图片',
    image_repeat: '重复图片'
  }
  return map[type] || type
}

function typeTag(type: string): string {
  const map: Record<string, string> = {
    annotation: 'warning',
    text: 'info',
    text_repeat: 'danger',
    image: 'success',
    image_repeat: 'primary'
  }
  return map[type] || ''
}

const allWatermarks = computed(() => {
  if (!detected.value) return []
  return [...detected.value.textWatermarks, ...detected.value.imageWatermarks]
})

const canRemove = computed(() => file.value && !removing.value)

async function confirmRemove() {
  if (removeMode.value === 'text') {
    await ElMessageBox.confirm(
      '「全部文本」模式会移除所有文字内容，仅保留图片和布局。确定继续？',
      '风险提示',
      { type: 'warning', confirmButtonText: '继续移除', cancelButtonText: '取消' }
    )
  }
  await removeWatermarks()
}
</script>

<template>
  <ToolHeader title="PDF 水印移除" description="检测并移除 PDF 中的文本水印、注释水印、图片水印。">
    <template #statusTop>
      <span class="text-xs" :class="canUseBackend ? 'text-success' : 'text-warning'">
        {{ canUseBackend ? '✓ 后端加速已开启' : '⚠ 需要后端加速' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-5xl py-6">
    <ProcessSteps :steps="steps" />

    <FileDropZone
      accept="application/pdf,.pdf"
      hint="仅接受 PDF 文件（推荐 ≤ 200MB）"
      chunk-label="① 上传 PDF"
      :current-count="file ? 1 : 0"
      :max-size="200 * 1024 * 1024"
      @files="onFiles"
    />

    <div v-if="!file" class="empty-block">
      <el-icon :size="34" class="mb-2"><Stamp /></el-icon>
      <div>还没有上传 PDF</div>
      <p class="text-xs text-text-mute mt-1">上传 PDF 后自动检测水印</p>
    </div>

    <div v-else class="card p-4 mt-2">
      <div class="flex items-center gap-4 flex-wrap">
        <div class="flex-1 min-w-0">
          <div class="text-sm font-medium truncate">{{ file.name }}</div>
          <div class="text-xs text-text-mute">{{ formatBytes(file.size) }}</div>
        </div>
        <button class="btn-primary" :disabled="detecting || !canUseBackend" @click="detect">
          <el-icon :size="16"><Search /></el-icon>
          {{ detecting ? `检测中 ${progress}%` : '检测水印' }}
        </button>
        <button class="btn-secondary" @click="clearFile">清除</button>
      </div>

      <RouterLink
        v-if="!canUseBackend"
        to="/me"
        class="text-xs text-primary hover:underline mt-2 inline-block"
      >
        → 去开启后端加速
      </RouterLink>
    </div>

    <div v-if="detected" class="card p-4 mt-2">
      <div class="flex items-center justify-between mb-3">
        <div class="text-sm font-medium">
          检测结果：共 {{ detected.total }} 处可疑水印
        </div>
      </div>

      <el-table v-if="allWatermarks.length" :data="allWatermarks" max-height="320" size="small">
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)" size="small">{{ typeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内容 / 位置" min-width="200">
          <template #default="{ row }">
            <span v-if="row.text" class="text-xs">{{ row.text.slice(0, 60) }}{{ row.text.length > 60 ? '...' : '' }}</span>
            <span v-else-if="row.pages" class="text-xs">出现于 {{ row.count }} 页（{{ row.pages.slice(0, 5).join(', ') }}{{ row.pages.length > 5 ? '...' : '' }}）</span>
            <span v-else-if="row.page" class="text-xs">第 {{ row.page }} 页</span>
            <span v-else class="text-xs text-text-mute">-</span>
          </template>
        </el-table-column>
        <el-table-column label="颜色" width="80">
          <template #default="{ row }">
            <div v-if="row.color" class="flex items-center gap-1">
              <span class="w-3 h-3 rounded border" :style="{ background: row.color }"></span>
              <span class="text-xs">{{ row.color }}</span>
            </div>
            <span v-else class="text-xs text-text-mute">-</span>
          </template>
        </el-table-column>
        <el-table-column label="面积占比" width="100">
          <template #default="{ row }">
            <span v-if="row.area_ratio" class="text-xs">{{ (row.area_ratio * 100).toFixed(1) }}%</span>
            <span v-else class="text-xs text-text-mute">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="text-center py-6 text-text-mute text-sm">
        未检测到明显水印，PDF 可能很干净
      </div>
    </div>

    <div v-if="file" class="card p-4 mt-2">
      <div class="flex flex-wrap items-center gap-4">
        <div>
          <div class="text-sm text-text-soft mb-1">移除模式</div>
          <el-radio-group v-model="removeMode">
            <el-radio-button value="all">智能移除（推荐）</el-radio-button>
            <el-radio-button value="text">仅文本</el-radio-button>
            <el-radio-button value="image">仅图片</el-radio-button>
            <el-radio-button value="keyword">按关键词</el-radio-button>
          </el-radio-group>
        </div>

        <div v-if="removeMode === 'keyword'">
          <div class="text-sm text-text-soft mb-1">水印关键词（逗号分隔）</div>
          <el-input
            v-model="keywords"
            placeholder="如：机密,CONFIDENTIAL,DRAFT"
            style="width: 280px"
          />
        </div>

        <div class="ml-auto flex items-center gap-2">
          <button class="btn-primary" :disabled="!canRemove || !canUseBackend" @click="confirmRemove">
            <el-icon :size="16"><Stamp /></el-icon>
            {{ removing ? `移除中 ${progress}%` : '移除水印' }}
          </button>
          <button
            class="btn-primary"
            :disabled="!resultBlob || removing"
            @click="download"
          >
            <el-icon :size="16"><Download /></el-icon>
            下载结果
          </button>
        </div>
      </div>
    </div>

    <div v-if="resultBlob" class="card p-4 mt-2">
      <div class="flex items-center gap-4">
        <el-icon :size="24" class="text-success"><SuccessFilled /></el-icon>
        <div class="flex-1">
          <div class="text-sm font-medium">{{ resultName }}</div>
          <div class="text-xs text-text-mute">{{ formatBytes(resultBlob.size) }}</div>
        </div>
        <button class="btn-primary" @click="download">
          <el-icon :size="16"><Download /></el-icon>
          下载
        </button>
      </div>
    </div>

    <div class="mt-4 space-y-1 text-xs text-text-mute leading-relaxed">
      <p><strong>智能移除</strong>：自动识别灰色文字、注释层水印、小图片水印并移除</p>
      <p><strong>仅文本</strong>：移除所有文字内容（慎用，仅保留图片和布局）</p>
      <p><strong>仅图片</strong>：移除页面上的小图片对象</p>
      <p><strong>按关键词</strong>：仅移除包含指定关键词的文本</p>
      <p class="mt-2 text-warning">注意：水印移除可能会影响 PDF 中的正常内容，请先检测预览后再操作。</p>
    </div>
  </section>
</template>
