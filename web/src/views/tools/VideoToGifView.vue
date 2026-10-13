<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { baseName, downloadBlob, formatBytes } from '@/utils/file'

// ---------- 视频转 GIF：纯前端 ----------

const videoFile = ref<File | null>(null)
const videoUrl = ref<string | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)

const totalDuration = ref(0) // 秒
const startTime = ref(0) // 秒
const endTime = ref(0) // 秒
const fps = ref(10)
const width = ref(480)

const generating = ref(false)
const genProgress = ref(0) // 0..100

const resultBlob = ref<Blob | null>(null)
const resultUrl = ref<string | null>(null)
const stats = ref<{ frames: number; duration: number; size: number } | null>(null)

let prevObjectUrl: string | null = null

watch(videoFile, (f) => {
  if (prevObjectUrl) {
    URL.revokeObjectURL(prevObjectUrl)
    prevObjectUrl = null
  }
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
    resultBlob.value = null
  }
  stats.value = null
  if (!f) {
    videoUrl.value = null
    totalDuration.value = 0
    startTime.value = 0
    endTime.value = 0
    return
  }
  videoUrl.value = URL.createObjectURL(f)
  prevObjectUrl = videoUrl.value
})

onBeforeUnmount(() => {
  if (prevObjectUrl) URL.revokeObjectURL(prevObjectUrl)
  if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
})

function onFiles(list: File[]) {
  const v = list.find((f) => f.type.startsWith('video/'))
  if (!v) {
    ElMessage.warning('请选择视频文件')
    return
  }
  videoFile.value = v
}

function onVideoLoaded() {
  const v = videoEl.value
  if (!v) return
  totalDuration.value = v.duration || 0
  if (!endTime.value || endTime.value > totalDuration.value) {
    endTime.value = Math.min(5, totalDuration.value) // 默认取前 5 秒
  }
  startTime.value = 0
}

/** 限制裁剪范围：start < end，最多 15 秒避免浏览器卡死 */
const clipDuration = computed(() => Math.max(0, endTime.value - startTime.value))
const totalFrames = computed(() => Math.max(1, Math.ceil(clipDuration.value * fps.value)))

function playPreview() {
  const v = videoEl.value
  if (!v) return
  v.pause()
  v.currentTime = Math.min(startTime.value, Math.max(0, totalDuration.value - 0.1))
  // eslint-disable-next-line @typescript-eslint/no-floating-promises
  v.play().catch(() => {
    // ignore autoplay policy — 允许用户手动点
  })
}

// 循环预览剪辑片段
function onVideoTimeUpdate() {
  const v = videoEl.value
  if (!v) return
  if (v.currentTime >= endTime.value && endTime.value > 0) {
    v.pause()
    v.currentTime = startTime.value
  }
}

function onStartChange() {
  if (startTime.value >= endTime.value) {
    endTime.value = Math.min(totalDuration.value, startTime.value + 0.5)
  }
  if (startTime.value < 0) startTime.value = 0
}
function onEndChange() {
  if (endTime.value <= startTime.value) {
    startTime.value = Math.max(0, endTime.value - 0.5)
  }
  if (endTime.value > totalDuration.value) endTime.value = totalDuration.value
}

function fmt(t: number) {
  if (!isFinite(t)) return '0.0s'
  const s = Math.max(0, t)
  return `${s.toFixed(2)}s`
}

// ============================================================
//  GIF 编码器（GIF 89a，256 色全局调色板 + 每帧 GCE + LZW）
// ============================================================

/** 写多位字节流的辅助类 */
class ByteWriter {
  chunks: Uint8Array[] = []
  pos = 0
  writeByte(b: number) {
    this.chunks.push(new Uint8Array([b & 0xff]))
    this.pos += 1
  }
  writeBytes(arr: ArrayLike<number>) {
    const u = new Uint8Array(arr.length)
    for (let i = 0; i < arr.length; i++) u[i] = arr[i] & 0xff
    this.chunks.push(u)
    this.pos += u.length
  }
  writeUint16LE(v: number) {
    this.chunks.push(new Uint8Array([v & 0xff, (v >>> 8) & 0xff]))
    this.pos += 2
  }
  writeASCII(s: string) {
    const u = new Uint8Array(s.length)
    for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 0xff
    this.chunks.push(u)
    this.pos += u.length
  }
  /** 以 GIF sub-block 格式写数据：每个块长度字节 0x01..0xff 后跟数据，末尾 0x00 */
  writeSubBlocks(data: Uint8Array) {
    let off = 0
    while (off < data.length) {
      const chunk = Math.min(255, data.length - off)
      this.writeByte(chunk)
      this.writeBytes(data.subarray(off, off + chunk))
      off += chunk
    }
    this.writeByte(0) // block terminator
  }
  toBlob(type = 'image/gif'): Blob {
    const total = this.chunks.reduce((s, c) => s + c.length, 0)
    const out = new Uint8Array(total)
    let p = 0
    for (const c of this.chunks) {
      out.set(c, p)
      p += c.length
    }
    return new Blob([out.buffer as ArrayBuffer], { type })
  }
}

/**
 * 量化：对所有帧收集到的 RGB 像素，使用简易中位切分得到 256 色调色板。
 * 如果帧数太多，会进行采样（最多采样 MAX_SAMPLE_PER_FRAME * frames 个像素）。
 */
interface RGB {
  r: number
  g: number
  b: number
}
interface Box {
  pixels: RGB[]
  rmin: number; rmax: number
  gmin: number; gmax: number
  bmin: number; bmax: number
}
function boxFromPixels(pixels: RGB[]): Box {
  let rmin = 255, rmax = 0, gmin = 255, gmax = 0, bmin = 255, bmax = 0
  for (const p of pixels) {
    if (p.r < rmin) rmin = p.r
    if (p.r > rmax) rmax = p.r
    if (p.g < gmin) gmin = p.g
    if (p.g > gmax) gmax = p.g
    if (p.b < bmin) bmin = p.b
    if (p.b > bmax) bmax = p.b
  }
  return { pixels, rmin, rmax, gmin, gmax, bmin, bmax }
}
function boxLongestDim(b: Box): 'r' | 'g' | 'b' {
  const dr = b.rmax - b.rmin
  const dg = b.gmax - b.gmin
  const db = b.bmax - b.bmin
  if (dr >= dg && dr >= db) return 'r'
  if (dg >= db) return 'g'
  return 'b'
}
function medianCut(sample: RGB[], maxColors: number): RGB[] {
  if (!sample.length) {
    const empty: RGB[] = []
    for (let i = 0; i < maxColors; i++) empty.push({ r: 0, g: 0, b: 0 })
    return empty
  }
  const boxes: Box[] = [boxFromPixels(sample)]
  while (boxes.length < maxColors) {
    // 找最长边且像素 > 1 的盒子
    let idx = -1
    let bestLen = -1
    for (let i = 0; i < boxes.length; i++) {
      const b = boxes[i]
      if (b.pixels.length < 2) continue
      const dim = boxLongestDim(b)
      const len =
        dim === 'r' ? b.rmax - b.rmin : dim === 'g' ? b.gmax - b.gmin : b.bmax - b.bmin
      if (len > bestLen) {
        bestLen = len
        idx = i
      }
    }
    if (idx < 0) break
    const parent = boxes.splice(idx, 1)[0]
    const dim = boxLongestDim(parent)
    const sorted = parent.pixels.slice()
    if (dim === 'r') sorted.sort((a, b) => a.r - b.r)
    else if (dim === 'g') sorted.sort((a, b) => a.g - b.g)
    else sorted.sort((a, b) => a.b - b.b)
    const mid = Math.floor(sorted.length / 2)
    const left = sorted.slice(0, mid)
    const right = sorted.slice(mid)
    if (left.length) boxes.push(boxFromPixels(left))
    if (right.length) boxes.push(boxFromPixels(right))
    else boxes.push(boxFromPixels(left.slice(-1))) // 保证至少两个
  }
  // 每个盒子取平均色
  const pal: RGB[] = boxes.map((b) => {
    if (!b.pixels.length) return { r: 0, g: 0, b: 0 }
    let sr = 0, sg = 0, sb = 0
    for (const p of b.pixels) {
      sr += p.r
      sg += p.g
      sb += p.b
    }
    const n = b.pixels.length
    return {
      r: Math.round(sr / n),
      g: Math.round(sg / n),
      b: Math.round(sb / n)
    }
  })
  while (pal.length < maxColors) pal.push({ r: 0, g: 0, b: 0 })
  return pal.slice(0, maxColors)
}

/** 将单个 RGB 映射到调色板中最近的颜色索引（欧氏距离近似） */
function nearestIndex(r: number, g: number, b: number, pal: RGB[]): number {
  let best = 0
  let bestD = 1e9
  for (let i = 0; i < pal.length; i++) {
    const p = pal[i]
    const dr = r - p.r
    const dg = g - p.g
    const db = b - p.b
    const d = dr * dr + dg * dg + db * db
    if (d < bestD) {
      bestD = d
      best = i
    }
  }
  return best
}

/**
 * LZW 编码（GIF 版本）：最小码长 minCodeSize（通常 8），
 * 输出码流按 bit-packing 存入字节序列，返回不含"初始码长字节"的原始码流字节。
 */
function lzwEncode(indexStream: Uint8Array, minCodeSize: number): Uint8Array {
  const clearCode = 1 << minCodeSize
  const eoiCode = clearCode + 1
  let nextCode = eoiCode + 1
  let codeSize = minCodeSize + 1 // 初始码长：minCodeSize + 1 bit
  const MAX_CODE = 4095
  const dict = new Map<number, number>() // key = prefix<<12 | suffix，value = code
  function dictKey(prefix: number, suffix: number) {
    return (prefix << 12) | (suffix & 0xfff)
  }
  const resetDict = () => {
    dict.clear()
    for (let i = 0; i < clearCode; i++) dict.set(dictKey(-1, i), i)
    nextCode = eoiCode + 1
    codeSize = minCodeSize + 1
  }

  const out: number[] = []
  let bitBuf = 0
  let bitLen = 0
  const emit = (code: number) => {
    bitBuf |= code << bitLen
    bitLen += codeSize
    while (bitLen >= 8) {
      out.push(bitBuf & 0xff)
      bitBuf >>>= 8
      bitLen -= 8
    }
  }

  resetDict()
  emit(clearCode)

  if (indexStream.length === 0) {
    emit(eoiCode)
    if (bitLen > 0) out.push(bitBuf & 0xff)
    return new Uint8Array(out)
  }

  let prefix = indexStream[0] & 0xff
  for (let i = 1; i < indexStream.length; i++) {
    const suffix = indexStream[i] & 0xff
    const k = dictKey(prefix, suffix)
    if (dict.has(k)) {
      prefix = dict.get(k)!
    } else {
      emit(prefix)
      if (nextCode <= MAX_CODE) {
        dict.set(k, nextCode++)
        // 码长进位
        if (nextCode - 1 === (1 << codeSize) && codeSize < 12) {
          codeSize++
        } else if (nextCode - 1 === MAX_CODE) {
          // 满了后下一次输出 clear 重置
        }
      } else {
        // 达到 4095，发送 clear 重置字典
        emit(clearCode)
        resetDict()
      }
      prefix = suffix
    }
  }
  emit(prefix)
  emit(eoiCode)
  if (bitLen > 0) out.push(bitBuf & 0xff)
  return new Uint8Array(out)
}

/**
 * 通过当前 video 元素（已 seek 到指定时间）的当前帧，绘制到离屏 canvas，
 * 返回 ImageData（按目标宽高）。
 */
function drawFrame(video: HTMLVideoElement, w: number, h: number, _canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D): ImageData {
  ctx.clearRect(0, 0, w, h)
  // 保持宽高比居中 + 填黑底（模仿视频播放器）
  const vw = video.videoWidth || w
  const vh = video.videoHeight || h
  const scale = Math.min(w / vw, h / vh)
  const dw = Math.round(vw * scale)
  const dh = Math.round(vh * scale)
  const dx = Math.floor((w - dw) / 2)
  const dy = Math.floor((h - dh) / 2)
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, w, h)
  ctx.drawImage(video, dx, dy, dw, dh)
  return ctx.getImageData(0, 0, w, h)
}

/** 等待 video seek 完成 */
function seekVideo(video: HTMLVideoElement, t: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const onSeeked = () => {
      video.removeEventListener('seeked', onSeeked)
      video.removeEventListener('error', onError)
      resolve()
    }
    const onError = () => {
      video.removeEventListener('seeked', onSeeked)
      video.removeEventListener('error', onError)
      reject(new Error('视频 seek 失败'))
    }
    video.addEventListener('seeked', onSeeked, { once: false })
    video.addEventListener('error', onError, { once: false })
    try {
      video.currentTime = t
    } catch (e) {
      reject(e instanceof Error ? e : new Error('seek 错误'))
    }
  })
}

/** 让 UI 有机会刷新：把每帧处理切成微任务块 */
function yieldUI(): Promise<void> {
  return new Promise((r) => setTimeout(r, 0))
}

/** 主流程：采集帧 → 建调色板 → 逐帧编码写 GIF */
async function generate() {
  const video = videoEl.value
  if (!video || !videoFile.value) {
    ElMessage.warning('请先上传视频')
    return
  }
  if (totalDuration.value <= 0) {
    ElMessage.warning('视频还未就绪，请稍后重试')
    return
  }
  if (clipDuration.value <= 0.05) {
    ElMessage.warning('请选择至少 0.05 秒的片段')
    return
  }
  if (clipDuration.value > 30) {
    ElMessage.warning('为避免浏览器卡顿，剪辑时长建议 ≤ 30 秒')
    return
  }

  generating.value = true
  genProgress.value = 0
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
  }
  resultBlob.value = null
  stats.value = null

  try {
    // 1. 尺寸：按视频原始比例算高度
    const targetW = Math.max(80, Math.min(1200, Math.floor(width.value)))
    const ratio = (video.videoWidth && video.videoHeight) ? video.videoHeight / video.videoWidth : 9 / 16
    const targetH = Math.max(1, Math.round(targetW * ratio))

    const framesCount = Math.max(1, Math.ceil(clipDuration.value * fps.value))
    const frameDelay = 1 / fps.value // 秒
    // 为了避免最后一帧和视频结尾对齐问题，使用均匀分布
    const frameTimes: number[] = []
    for (let i = 0; i < framesCount; i++) {
      const t = startTime.value + i * frameDelay
      frameTimes.push(Math.min(Math.max(0, t), Math.max(0, totalDuration.value - 0.001)))
    }

    // 2. 离屏画布
    const canvas = document.createElement('canvas')
    canvas.width = targetW
    canvas.height = targetH
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) throw new Error('无法创建 2D 画布上下文')
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'

    // 3. 逐帧采集 ImageData，同时收集采样像素建调色板
    const frameDataList: ImageData[] = []
    const sample: RGB[] = []
    // 为控制调色板大小：每帧最多采样约 w*h / 60 个像素
    const sampleStride = Math.max(1, Math.floor((targetW * targetH) / 2000))

    for (let i = 0; i < frameTimes.length; i++) {
      await seekVideo(video, frameTimes[i])
      const img = drawFrame(video, targetW, targetH, canvas, ctx)
      frameDataList.push(new ImageData(new Uint8ClampedArray(img.data), img.width, img.height))
      const d = img.data
      for (let p = 0; p < d.length; p += 4 * sampleStride) {
        sample.push({ r: d[p], g: d[p + 1], b: d[p + 2] })
      }
      genProgress.value = Math.round(10 + (i / frameTimes.length) * 40) // 10..50
      // 每 4 帧让一次 UI
      if ((i & 3) === 0) await yieldUI()
    }

    // 4. 中位切分生成 256 色全局调色板
    const pal = medianCut(sample, 256)
    // 计算调色板 size（N 取 8 => 256 色 => packed field 0x80 | 0x07 = 0x87? GCT 位: 3 bits of (log2N - 1)）
    // 全局色表大小字段 = 2^(N+1)，我们 256 = 2^8，所以 N = 7
    const colorTableSize = 7

    genProgress.value = 55

    // 5. 写 GIF 结构
    const w = new ByteWriter()
    // Header: GIF89a
    w.writeASCII('GIF89a')
    // Logical Screen Descriptor: width(2) height(2) packed(1) bgIndex(1) pixelAspect(1)
    w.writeUint16LE(targetW)
    w.writeUint16LE(targetH)
    // packed: 全局色表存在 1 | 色分辨率 111(8bit) | 排序 0 | GCT size 111(=7)
    w.writeByte(0xf0 | colorTableSize)
    w.writeByte(0) // bg index
    w.writeByte(0) // aspect ratio 0=1:1

    // Global Color Table (3 * 256)
    for (const c of pal) {
      w.writeByte(c.r)
      w.writeByte(c.g)
      w.writeByte(c.b)
    }
    // 补齐到 2^(N+1) 条（N=7 => 256 条刚好）
    // 若 pal.length < 256, medianCut 已填充黑色，无需额外

    // Application Extension: NETSCAPE 2.0, loop 0 = 无限循环
    w.writeByte(0x21) // extension introducer
    w.writeByte(0xff) // application extension label
    w.writeByte(11) // block size
    w.writeASCII('NETSCAPE2.0')
    // sub-block: 3 bytes
    w.writeByte(3)
    w.writeByte(1)
    w.writeUint16LE(0) // loop count: 0=infinite
    w.writeByte(0) // block terminator

    const delayCs = Math.max(2, Math.round(100 / fps.value)) // 百分之一秒，最低 2

    // 逐帧：GCE + Image Descriptor + LZW
    for (let i = 0; i < frameDataList.length; i++) {
      const img = frameDataList[i]
      // Graphics Control Extension
      w.writeByte(0x21)
      w.writeByte(0xf9)
      w.writeByte(4) // block size
      // packed: disposal=2(restore bg), userInput=0, transparent=0
      w.writeByte(0b00001000)
      w.writeUint16LE(delayCs) // delay centiseconds
      w.writeByte(0) // transparent color index
      w.writeByte(0) // block terminator

      // Image Descriptor
      w.writeByte(0x2c) // image separator
      w.writeUint16LE(0) // left
      w.writeUint16LE(0) // top
      w.writeUint16LE(targetW)
      w.writeUint16LE(targetH)
      // packed: 无本地色表 0, interlace 0, sort 0, reserved 00, LCT size 000
      w.writeByte(0x00)

      // LZW encode
      const pixels = img.data
      const count = targetW * targetH
      const indexStream = new Uint8Array(count)
      // 量化每个像素到调色板索引
      for (let p = 0, q = 0; p < pixels.length; p += 4, q++) {
        indexStream[q] = nearestIndex(pixels[p], pixels[p + 1], pixels[p + 2], pal)
      }
      const minCodeSize = 8
      const lzwBytes = lzwEncode(indexStream, minCodeSize)
      w.writeByte(minCodeSize)
      w.writeSubBlocks(lzwBytes)

      genProgress.value = Math.round(58 + ((i + 1) / frameDataList.length) * 40) // 58..98
      // 每 2 帧让一次 UI
      if ((i & 1) === 0) await yieldUI()
    }

    // Trailer
    w.writeByte(0x3b)

    const blob = w.toBlob('image/gif')
    resultBlob.value = blob
    resultUrl.value = URL.createObjectURL(blob)
    stats.value = {
      frames: frameDataList.length,
      duration: frameDataList.length / fps.value,
      size: blob.size
    }
    genProgress.value = 100
    ElMessage.success('GIF 生成成功')
  } catch (e) {
    ElMessage.error('生成失败：' + (e instanceof Error ? e.message : String(e)))
  } finally {
    generating.value = false
  }
}

function downloadResult() {
  if (!resultBlob.value || !videoFile.value) return
  const name = `${baseName(videoFile.value.name)}.gif`
  downloadBlob(resultBlob.value, name)
}

function clearAll() {
  videoFile.value = null
  startTime.value = 0
  endTime.value = 0
  totalDuration.value = 0
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
  }
  resultBlob.value = null
  stats.value = null
}

const canGenerate = computed(() =>
  !!videoFile.value &&
  clipDuration.value >= 0.05 &&
  clipDuration.value <= 30 &&
  totalDuration.value > 0 &&
  !generating.value
)
</script>

<template>
  <ToolHeader title="视频转 GIF" description="截取视频片段，转换为高清 GIF 动图（纯前端处理）" />

  <section class="container-page max-w-5xl py-6 space-y-4">
    <!-- 设置 -->
    <div class="card p-4">
      <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
        <el-icon :size="16" class="text-primary"><Setting /></el-icon>
        GIF 参数
      </h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div class="sm:col-span-2">
          <div class="flex items-center justify-between text-sm text-text-soft mb-1">
            <span>裁剪时间范围（共 {{ fmt(totalDuration) }}）</span>
            <span class="text-xs text-text-mute">
              {{ fmt(startTime) }} ~ {{ fmt(endTime) }} · 长度
              <span class="text-primary">{{ fmt(clipDuration) }}</span>
              <span class="ml-1">· 约 {{ totalFrames }} 帧</span>
            </span>
          </div>
          <div class="space-y-2">
            <el-slider
              :model-value="startTime"
              :min="0"
              :max="totalDuration || 1"
              :step="0.05"
              @update:model-value="(v: number) => { startTime = v; onStartChange() }"
            />
            <el-slider
              :model-value="endTime"
              :min="0"
              :max="totalDuration || 1"
              :step="0.05"
              @update:model-value="(v: number) => { endTime = v; onEndChange() }"
            />
          </div>
        </div>
        <div>
          <div class="text-sm text-text-soft mb-1">帧率（FPS）：{{ fps }}</div>
          <el-slider v-model="fps" :min="5" :max="30" :marks="{ 5: '5', 10: '10', 15: '15', 24: '24', 30: '30' }" show-stops />
        </div>
        <div>
          <div class="text-sm text-text-soft mb-1">输出宽度（按比例缩放）：{{ width }}px</div>
          <el-slider v-model="width" :min="120" :max="960" :step="10" :marks="{ 240: '240', 480: '480', 720: '720' }" />
        </div>
      </div>
    </div>

    <!-- 上传 -->
    <FileDropZone
      accept="video/*"
      :multiple="false"
      hint="单个视频即可；建议剪辑片段 ≤ 15 秒，避免浏览器内存压力"
      chunk-label="① 上传视频"
      @files="onFiles"
    />

    <!-- 视频预览 -->
    <div v-if="videoUrl" class="card p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold flex items-center gap-2">
          <el-icon :size="16" class="text-primary"><VideoCamera /></el-icon>
          视频预览（仅 {{ fmt(startTime) }} ~ {{ fmt(endTime) }} 区间）
        </h3>
        <div class="flex items-center gap-2">
          <button class="btn-ghost !border !border-border" @click="playPreview" :disabled="generating">
            <el-icon><VideoPlay /></el-icon>
            <span class="ml-1">预览片段</span>
          </button>
          <button class="btn-ghost btn-ghost-danger" :disabled="generating" @click="clearAll">
            <el-icon><Delete /></el-icon>
            <span class="ml-1">移除</span>
          </button>
        </div>
      </div>

      <div class="bg-black rounded-md overflow-hidden mx-auto" :style="{ maxWidth: width + 'px' }">
        <video
          ref="videoEl"
          :src="videoUrl"
          muted
          playsinline
          controls
          class="w-full block"
          @loadedmetadata="onVideoLoaded"
          @timeupdate="onVideoTimeUpdate"
        />
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <button class="btn-primary" :disabled="!canGenerate" @click="generate">
          <el-icon v-if="generating" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon>
          <span class="ml-1">
            {{ generating ? `生成中 ${genProgress}%` : `生成 GIF（约 ${totalFrames} 帧）` }}
          </span>
        </button>
        <button
          class="btn-ghost !border !border-border"
          :disabled="!resultBlob || generating"
          @click="downloadResult"
        >
          <el-icon><Download /></el-icon>
          <span class="ml-1">下载 GIF</span>
        </button>
        <div v-if="generating" class="ml-2 w-48">
          <el-progress :percentage="genProgress" :stroke-width="6" />
        </div>
      </div>
    </div>

    <!-- 空态 -->
    <div v-if="!videoUrl" class="empty-block">
      <el-icon :size="34" class="mb-2 text-primary"><Film /></el-icon>
      <div>请先上传一个视频</div>
      <p class="text-xs text-text-mute mt-1">上传后可设定时间范围、帧率和宽度，然后一键生成 GIF</p>
    </div>

    <!-- 结果预览 -->
    <div v-if="resultUrl" class="card p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold flex items-center gap-2">
          <el-icon :size="16" class="text-success"><Finished /></el-icon>
          生成结果
        </h3>
        <button class="btn-ghost !border !border-border" :disabled="generating" @click="downloadResult">
          <el-icon><Download /></el-icon>
          <span class="ml-1">下载 GIF</span>
        </button>
      </div>
      <div class="flex flex-col sm:flex-row gap-4">
        <div class="flex-1 min-w-0 bg-bg-soft rounded-md overflow-hidden border border-border flex items-center justify-center p-2">
          <img :src="resultUrl" alt="GIF" class="max-w-full max-h-[480px] object-contain block" />
        </div>
        <div class="sm:w-56 shrink-0 space-y-2 text-sm">
          <div class="card p-3 !shadow-none">
            <div class="text-xs text-text-mute mb-1">总帧数</div>
            <div class="font-semibold">{{ stats?.frames ?? 0 }} 帧</div>
          </div>
          <div class="card p-3 !shadow-none">
            <div class="text-xs text-text-mute mb-1">持续时长</div>
            <div class="font-semibold">{{ (stats?.duration ?? 0).toFixed(2) }} 秒</div>
          </div>
          <div class="card p-3 !shadow-none">
            <div class="text-xs text-text-mute mb-1">文件大小</div>
            <div class="font-semibold text-primary">{{ formatBytes(stats?.size ?? 0) }}</div>
          </div>
          <div class="card p-3 !shadow-none">
            <div class="text-xs text-text-mute mb-1">估计参数</div>
            <div class="font-semibold">{{ width }}px · {{ fps }} FPS</div>
          </div>
        </div>
      </div>
    </div>

    <p class="text-xs text-text-mute leading-relaxed">
      提示：GIF 为 256 色无损索引格式，视频转 GIF 会有一定色彩损失。建议优先选择对比度明显、场景变化不剧烈的片段。
      单文件体积较大，可降低宽度 / 帧率 / 时长以进一步压缩。
    </p>
  </section>
</template>
