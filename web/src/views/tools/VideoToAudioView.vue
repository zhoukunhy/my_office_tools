<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import BatchFileList, { type BatchFileItem } from '@/components/common/BatchFileList.vue'
import ProcessSteps, { type StepStatus } from '@/components/common/ProcessSteps.vue'
import { usePreferenceStore } from '@/stores/preference'
import { backendFetch } from '@/utils/api'
import { baseName, downloadBlob, downloadFilesAsZip, formatBytes } from '@/utils/file'

type ExtractMode = 'backend' | 'local'
type AudioFormat = 'mp3' | 'aac' | 'wav' | 'webm'

const pref = usePreferenceStore()

const mode = ref<ExtractMode>('backend')
const audioFormat = ref<AudioFormat>('mp3')

const files = ref<BatchFileItem[]>([])
const results = ref<{ id: string; name: string; blob: Blob }[]>([])
const processing = ref(false)
const progress = ref(0)

const canBackend = computed(() => pref.backendEnabled)

const steps = computed(() => {
  const s1: StepStatus = files.value.length ? 'done' : 'active'
  const s2: StepStatus = files.value.length ? 'active' : 'idle'
  const s3: StepStatus = processing.value ? 'active' : results.value.length ? 'done' : 'idle'
  const s4: StepStatus = results.value.length ? 'active' : 'idle'
  return [
    { label: '上传视频', status: s1 },
    { label: '选择提取方式', status: s2 },
    { label: '提取音频', status: s3 },
    { label: '下载结果', status: s4 }
  ]
})

/** 本地模式是否支持 captureStream / MediaRecorder */
const supportLocal = computed(() => {
  try {
    const HTMLVideo = (window as unknown as { HTMLVideoElement?: unknown }).HTMLVideoElement
    if (!HTMLVideo) return false
    const tmp = document.createElement('video')
    const canCS = typeof (tmp as unknown as { captureStream?: () => unknown }).captureStream === 'function'
    const canMR = typeof (window as unknown as { MediaRecorder?: unknown }).MediaRecorder === 'function'
    return canCS && canMR
  } catch {
    return false
  }
})

let idc = 0
function addFiles(list: File[]) {
  const arr = list
    .filter((f) => f.type.startsWith('video/'))
    .map<BatchFileItem>((f) => ({
      id: `a${++idc}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      name: f.name,
      size: f.size,
      status: 'wait',
      progress: 0,
      _file: f as unknown as never
    }))
  if (arr.length !== list.length) ElMessage.warning('已跳过非视频文件')
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

const formatExt: Record<AudioFormat, string> = {
  mp3: 'mp3',
  aac: 'm4a',
  wav: 'wav',
  webm: 'webm'
}

async function extractBackend(file: File, item: BatchFileItem): Promise<Blob> {
  const form = new FormData()
  form.append('file', file)
  form.append('format', mode.value === 'backend' ? audioFormat.value : 'webm')
  item.progress = 10
  const r = await backendFetch('/video/extract-audio', form, { timeoutMs: 600_000 })
  if (!r.ok) throw new Error(r.message)
  item.progress = 95
  return r.blob
}

/** 前端纯本地实现：HTMLVideo + captureStream + MediaRecorder */
async function extractLocal(file: File, item: BatchFileItem): Promise<Blob> {
  const url = URL.createObjectURL(file)
  try {
    const video = document.createElement('video')
    video.src = url
    video.muted = true
    video.playsInline = true
    video.crossOrigin = 'anonymous'
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve()
      video.onerror = () => reject(new Error('无法加载视频元数据'))
    })
    if (!video.duration || isNaN(video.duration)) {
      throw new Error('无法获取视频时长')
    }

    const stream = (video as unknown as { captureStream(): MediaStream }).captureStream()
    // 仅保留音频轨道
    const audioTracks = stream.getAudioTracks()
    if (!audioTracks.length) {
      throw new Error('视频中没有可提取的音频轨道')
    }
    const audioStream = new MediaStream(audioTracks)

    // 选择支持的 mime
    const MR = (window as unknown as { MediaRecorder: typeof MediaRecorder }).MediaRecorder
    const mimeCandidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg']
    let mime = ''
    for (const m of mimeCandidates) {
      if (typeof (MR as unknown as { isTypeSupported?: (s: string) => boolean }).isTypeSupported === 'function') {
        if ((MR as unknown as { isTypeSupported: (s: string) => boolean }).isTypeSupported(m)) {
          mime = m
          break
        }
      }
    }
    const recorder = new MR(audioStream, mime ? { mimeType: mime } : undefined)
    const chunks: BlobPart[] = []
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data)
    }

    const durationMs = video.duration * 1000
    const startTs = performance.now()

    return await new Promise<Blob>((resolve, reject) => {
      let timer: number | undefined
      const cleanup = () => {
        if (timer !== undefined) window.clearInterval(timer)
      }
      recorder.onstop = () => {
        cleanup()
        try {
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
          resolve(blob)
        } catch (e) {
          reject(e instanceof Error ? e : new Error('录制失败'))
        }
      }
      recorder.onerror = () => {
        cleanup()
        reject(new Error('MediaRecorder 录制出错'))
      }

      try {
        recorder.start(250)
        const playP = video.play()
        if (playP && typeof playP.catch === 'function') {
          playP.catch((e) => reject(new Error('视频自动播放被阻止：' + (e as Error).message)))
        }
        item.progress = 5
        // 按播放进度更新
        timer = window.setInterval(() => {
          const el = performance.now() - startTs
          const p = Math.min(95, Math.round((el / durationMs) * 100))
          item.progress = Math.max(item.progress ?? 0, p)
        }, 250)
        video.onended = () => {
          if (recorder.state !== 'inactive') recorder.stop()
          audioTracks.forEach((t) => t.stop())
        }
        // 兜底：超过 duration 仍未结束则强制停止
        window.setTimeout(() => {
          if (recorder.state === 'recording') {
            try {
              video.pause()
              recorder.stop()
              audioTracks.forEach((t) => t.stop())
            } catch {
              /* ignore */
            }
          }
        }, durationMs + 5000)
      } catch (e) {
        cleanup()
        reject(e instanceof Error ? e : new Error('启动录制失败'))
      }
    })
  } finally {
    URL.revokeObjectURL(url)
  }
}

async function run() {
  if (!files.value.length) return
  if (mode.value === 'backend' && !canBackend.value) {
    ElMessage.warning('后端模式需先在「个人中心」开启后端加速')
    return
  }
  if (mode.value === 'local' && !supportLocal.value) {
    ElMessage.warning('当前浏览器不支持 captureStream + MediaRecorder，请改用后端模式')
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
      item.progress = 3
      item.message = ''
      try {
        const file = (item as unknown as { _file: File })._file
        const blob =
          mode.value === 'backend' ? await extractBackend(file, item) : await extractLocal(file, item)

        const ext =
          mode.value === 'backend'
            ? formatExt[audioFormat.value]
            : 'webm'
        results.value.push({
          id: item.id,
          name: `${baseName(item.name)}.${ext}`,
          blob
        })
        item.status = 'done'
        item.message = `成功，音频大小 ${formatBytes(blob.size)}`
        item.progress = 100
      } catch (err) {
        item.status = 'error'
        item.message = err instanceof Error ? err.message : '提取失败'
      } finally {
        progress.value = Math.round(((i + 1) / n) * 100)
      }
    }
    ElMessage.success(results.value.length ? `已提取 ${results.value.length} 个音频` : '无可用结果')
  } finally {
    processing.value = false
  }
}

const canRun = computed(() => {
  if (!files.value.length || processing.value) return false
  if (mode.value === 'backend') return canBackend.value
  return supportLocal.value
})

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
    '提取音频结果.zip'
  )
}
</script>

<template>
  <ToolHeader title="视频提取音频" description="从视频文件中提取 MP3 / WAV / AAC 音频">
    <template #statusTop>
      <span class="text-xs" :class="canBackend ? 'text-success' : 'text-warning'">
        {{ canBackend ? '✓ 后端提取已开启（推荐）' : '⚡ 未开启后端 → 可用本地模式，仅输出 WebM' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-5xl py-6 space-y-4">
    <ProcessSteps :steps="steps" />

    <!-- 模式与设置 -->
    <div class="card p-4">
      <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
        <el-icon :size="16" class="text-primary"><Setting /></el-icon>
        提取方式
      </h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <div class="text-sm text-text-soft mb-1">处理模式</div>
          <el-radio-group v-model="mode" class="flex flex-wrap gap-2">
            <el-radio-button value="backend" :disabled="!canBackend">后端提取（推荐 · 多格式）</el-radio-button>
            <el-radio-button value="local" :disabled="!supportLocal">前端纯本地（WebM）</el-radio-button>
          </el-radio-group>
        </div>
        <div>
          <div class="text-sm text-text-soft mb-1">
            输出格式
            <span v-if="mode === 'local'" class="text-text-mute">（本地模式固定 WebM）</span>
          </div>
          <el-select v-model="audioFormat" class="w-full" :disabled="mode === 'local'">
            <el-option label="MP3（通用）" value="mp3" />
            <el-option label="AAC / M4A（体积更小）" value="aac" />
            <el-option label="WAV（无损）" value="wav" />
            <el-option label="WebM（Opus）" value="webm" />
          </el-select>
        </div>
      </div>
      <el-alert
        v-if="mode === 'local'"
        class="mt-3"
        type="warning"
        :closable="false"
        show-icon
        title="前端本地模式说明"
        description="本地模式通过浏览器播放视频并用 MediaRecorder 录制音频轨道，结果只能是 WebM 音频，音质取决于浏览器编码。如追求高质量或需要 MP3 / AAC / WAV，请启用后端模式。"
      />
      <el-alert
        v-else
        class="mt-3"
        type="info"
        :closable="false"
        show-icon
        title="后端模式说明"
        description="通过后端 ffmpeg 精确解封装 / 转码，可输出 MP3 / AAC / WAV / WebM，速度和音质均有保障。"
      />
    </div>

    <!-- 上传 -->
    <FileDropZone
      accept="video/*"
      hint="支持 MP4 / WebM / MOV / MKV / FLV 等常见视频"
      chunk-label="① 上传视频（支持批量）"
      :current-count="files.length"
      :max-size="4 * 1024 * 1024 * 1024"
      @files="addFiles"
    />

    <div v-if="!files.length" class="empty-block">
      <el-icon :size="34" class="mb-2 text-primary"><Headset /></el-icon>
      <div>还没有视频文件</div>
      <p class="text-xs text-text-mute mt-1">上传包含音频轨道的视频即可提取</p>
    </div>

    <BatchFileList :items="files" @remove="remove" @move="move" @clear-all="clearAll" />

    <!-- 操作栏 -->
    <div class="card p-4">
      <div class="flex flex-wrap items-center gap-2">
        <button class="btn-primary" :disabled="!canRun" @click="run">
          <el-icon v-if="processing" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon>
          {{ processing ? `提取中 ${progress}%` : `开始提取（${files.length}）` }}
        </button>
        <button
          class="btn-ghost !border !border-border"
          :disabled="!results.length || processing"
          @click="downloadAll"
        >
          <el-icon><Download /></el-icon>
          {{ results.length > 1 ? '打包下载 ZIP' : '下载结果' }}
        </button>
      </div>

      <!-- 结果列表 -->
      <ul v-if="results.length" class="mt-4 space-y-2">
        <li
          v-for="r in results"
          :key="r.id"
          class="flex items-center gap-3 p-2 rounded-md hover:bg-bg-soft"
        >
          <div class="w-10 h-10 shrink-0 rounded bg-bg-soft flex items-center justify-center border border-border">
            <el-icon class="text-text-mute"><Headset /></el-icon>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm truncate">{{ r.name }}</div>
            <div class="text-xs text-text-mute">{{ formatBytes(r.blob.size) }}</div>
          </div>
          <button class="btn-ghost" @click="downloadSingle(r.id)">
            <el-icon><Download /></el-icon>
            <span class="ml-1">下载</span>
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>
