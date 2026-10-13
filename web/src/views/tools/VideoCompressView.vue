<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import BatchFileList, { type BatchFileItem } from '@/components/common/BatchFileList.vue'
import { usePreferenceStore } from '@/stores/preference'
import { backendFetch } from '@/utils/api'
import {
  baseName,
  downloadBlob,
  downloadFilesAsZip,
  formatBytes,
  getExt
} from '@/utils/file'

type OutputFormat = 'keep' | 'mp4' | 'webm'

const pref = usePreferenceStore()

const files = ref<BatchFileItem[]>([])
const results = ref<{ id: string; name: string; blob: Blob; originSize: number }[]>([])
const processing = ref(false)
const progress = ref(0)

/** 压缩质量 1-5：1 近似无损（CRF 18），5 体积极小（CRF 28） */
const quality = ref(3)
/** 输出格式 */
const outputFormat = ref<OutputFormat>('keep')

const canBackend = computed(() => pref.backendEnabled)

const qualityTip = computed(() => {
  const map: Record<number, string> = {
    1: '画质优先（体积最大）',
    2: '高画质',
    3: '均衡推荐',
    4: '体积优先',
    5: '极致压缩（画质降低明显）'
  }
  return map[quality.value] || ''
})

const crfMap: Record<number, number> = { 1: 18, 2: 21, 3: 24, 4: 26, 5: 28 }

let idc = 0
function addFiles(list: File[]) {
  const arr = list
    .filter((f) => f.type.startsWith('video/'))
    .map<BatchFileItem>((f) => ({
      id: `v${++idc}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      name: f.name,
      size: f.size,
      status: 'wait',
      progress: 0,
      _file: f as unknown as never
    }))
  if (arr.length !== list.length) {
    ElMessage.warning('已跳过非视频文件')
  }
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

function decideOutName(originalName: string, format: OutputFormat, blob: Blob): string {
  const ext =
    format === 'keep'
      ? getExt(originalName) || 'mp4'
      : format === 'mp4'
        ? 'mp4'
        : 'webm'
  // 若后端返回了更合适的内容类型，以其后缀为准（防止 keep 但后端转封装）
  const hinted =
    blob.type === 'video/webm'
      ? 'webm'
      : blob.type === 'video/mp4'
        ? 'mp4'
        : ext
  return `${baseName(originalName)}.min.${hinted || ext}`
}

async function compressOneBackend(file: File, item: BatchFileItem): Promise<Blob> {
  const form = new FormData()
  form.append('file', file)
  form.append('quality', String(crfMap[quality.value] ?? 24))
  form.append('format', outputFormat.value)
  item.progress = 15
  const r = await backendFetch('/video/compress', form, { timeoutMs: 600_000 })
  if (!r.ok) throw new Error(r.message)
  return r.blob
}

async function run() {
  if (!files.value.length) return
  if (!canBackend.value) {
    ElMessage.warning('视频压缩依赖后端 ffmpeg 能力，请先在「个人中心」开启后端加速')
    return
  }
  processing.value = true
  progress.value = 0
  results.value = []
  try {
    const n = files.value.length
    for (let i = 0; i < n; i++) {
      const item = files.value[i]
      item.status = 'process'
      item.progress = 5
      item.message = ''
      try {
        const file = (item as unknown as { _file: File })._file
        const blob = await compressOneBackend(file, item)
        const saved = Math.max(0, item.size - blob.size)
        if (blob.size >= item.size) {
          item.status = 'done'
          item.message = '体积未减小（已处于高压缩状态）'
        } else {
          item.status = 'done'
          item.message = `压缩 ${Math.round((saved / item.size) * 100)}% · 节省 ${formatBytes(saved)}`
        }
        item.progress = 100
        results.value.push({
          id: item.id,
          name: decideOutName(item.name, outputFormat.value, blob),
          blob,
          originSize: item.size
        })
      } catch (err) {
        item.status = 'error'
        item.message = err instanceof Error ? err.message : '压缩失败'
      } finally {
        progress.value = Math.round(((i + 1) / n) * 100)
      }
    }
    ElMessage.success(results.value.length ? `已完成 ${results.value.length} 个视频` : '无可用结果')
  } finally {
    processing.value = false
  }
}

const canRun = computed(() => files.value.length > 0 && !processing.value && canBackend.value)

function downloadSingle(id: string) {
  const r = results.value.find((x) => x.id === id)
  if (r) downloadBlob(r.blob, r.name)
}

function downloadAll() {
  if (!results.value.length) return
  if (results.value.length === 1) {
    const r = results.value[0]
    downloadBlob(r.blob, r.name)
    return
  }
  downloadFilesAsZip(
    results.value.map((r) => ({ blob: r.blob, name: r.name })),
    '视频压缩结果.zip'
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
  <ToolHeader title="视频压缩" description="减小视频体积（需后端 ffmpeg 能力）">
    <template #statusTop>
      <span class="text-xs" :class="canBackend ? 'text-success' : 'text-warning'">
        {{ canBackend ? '✓ 后端 ffmpeg 已就绪' : '⚡ 未开启后端 → 纯前端无法真正 H.264 编码' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-5xl py-6 space-y-4">
    <!-- 设置卡片 -->
    <div class="card p-4">
      <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
        <el-icon :size="16" class="text-primary"><Setting /></el-icon>
        压缩设置
      </h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <div class="flex items-center justify-between text-sm text-text-soft mb-1">
            <label>压缩质量（1 - 5）</label>
            <span class="text-xs text-text-mute">{{ qualityTip }}</span>
          </div>
          <el-slider v-model="quality" :min="1" :max="5" :marks="{ 1: '画质', 3: '均衡', 5: '体积极小' }" show-stops />
        </div>
        <div>
          <div class="text-sm text-text-soft mb-1">输出格式</div>
          <el-select v-model="outputFormat" class="w-full">
            <el-option label="保持原格式（keep）" value="keep" />
            <el-option label="MP4（兼容性好）" value="mp4" />
            <el-option label="WebM（体积更小）" value="webm" />
          </el-select>
        </div>
      </div>
      <el-alert
        class="mt-3"
        type="info"
        :closable="false"
        show-icon
        title="关于前端压缩"
        description="纯前端浏览器环境无法真正做 H.264/H.265 高质量编码；本工具默认通过后端 ffmpeg 进行 CRF 压缩。若你暂时未开启后端，可先在「个人中心」中配置后端地址。"
      />
    </div>

    <!-- 上传区 -->
    <FileDropZone
      accept="video/*"
      hint="支持 MP4 / WebM / MOV / MKV 等视频，推荐单文件 ≤ 2GB"
      chunk-label="① 上传视频（可批量追加）"
      :current-count="files.length"
      :max-size="4 * 1024 * 1024 * 1024"
      @files="addFiles"
    />

    <div v-if="!files.length" class="empty-block">
      <el-icon :size="34" class="mb-2 text-primary"><VideoCamera /></el-icon>
      <div>还没有视频文件</div>
      <p class="text-xs text-text-mute mt-1">上传至少一个视频后即可开始压缩</p>
    </div>

    <!-- 批量列表 -->
    <BatchFileList :items="files" @remove="remove" @move="move" @clear-all="clearAll" />

    <!-- 操作栏 -->
    <div class="card p-4">
      <div class="flex flex-wrap items-center gap-2">
        <button class="btn-primary" :disabled="!canRun" @click="run">
          <el-icon v-if="processing" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><Compress /></el-icon>
          {{ processing ? `压缩中 ${progress}%` : `开始压缩（${files.length}）` }}
        </button>
        <button class="btn-ghost !border !border-border" :disabled="!results.length || processing" @click="downloadAll">
          <el-icon><Download /></el-icon>
          {{ results.length > 1 ? '打包下载 ZIP' : '下载结果' }}
        </button>
      </div>

      <!-- 统计 -->
      <div v-if="summary" class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
        <div class="card p-3 !shadow-none">
          <div class="text-xs text-text-mute mb-1">原始总大小</div>
          <div class="font-semibold">{{ formatBytes(summary.before) }}</div>
        </div>
        <div class="card p-3 !shadow-none">
          <div class="text-xs text-text-mute mb-1">压缩后</div>
          <div class="font-semibold">{{ formatBytes(summary.after) }}</div>
        </div>
        <div class="card p-3 !shadow-none">
          <div class="text-xs text-text-mute mb-1">节省空间</div>
          <div class="font-semibold text-success">{{ formatBytes(summary.saved) }}</div>
        </div>
        <div class="card p-3 !shadow-none">
          <div class="text-xs text-text-mute mb-1">压缩率</div>
          <div class="font-semibold text-primary">{{ summary.percent }}%</div>
        </div>
      </div>

      <!-- 结果单独下载 -->
      <ul v-if="results.length" class="mt-4 space-y-2">
        <li
          v-for="r in results"
          :key="r.id"
          class="flex items-center gap-3 p-2 rounded-md hover:bg-bg-soft"
        >
          <div class="w-10 h-10 shrink-0 rounded bg-bg-soft flex items-center justify-center border border-border">
            <el-icon class="text-text-mute"><VideoCamera /></el-icon>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm truncate">{{ r.name }}</div>
            <div class="text-xs text-text-mute">
              {{ formatBytes(r.originSize) }}
              <span> → {{ formatBytes(r.blob.size) }}</span>
              <span v-if="r.blob.size < r.originSize" class="ml-1 text-success">
                省 {{ Math.round(((r.originSize - r.blob.size) / r.originSize) * 100) }}%
              </span>
            </div>
          </div>
          <button class="btn-ghost" @click="downloadSingle(r.id)">
            <el-icon><Download /></el-icon>
            <span class="ml-1">下载</span>
          </button>
        </li>
      </ul>
    </div>

    <p class="text-xs text-text-mute leading-relaxed">
      提示：较大的视频压缩需要较长时间，建议分批处理；后端启用后请求会通过 ffmpeg 执行，本地不会上传至任何第三方云端。
    </p>
  </section>
</template>
