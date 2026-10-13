<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadFilesAsZip, downloadBlob, baseName } from '@/utils/file'
import { loadImage, type ImgFormat } from '@/utils/image'

interface Item {
  file: File
  width: number
  height: number
  result: Blob | null
  preview: string
  processing: boolean
}

const items = ref<Item[]>([])
type WmType = 'text' | 'logo'
const wmType = ref<WmType>('text')
const text = ref('仅供内部使用')
const fontSize = ref(36)
const fontColor = ref('#ffffff')
const logoFile = ref<File | null>(null)
const logoScale = ref(20) // 占图宽百分比
const opacity = ref(0.5)
const position = ref(8) // 九宫格 1-9
const margin = ref(24)
const tile = ref(false)
const tileGap = ref(120)
const rotate = ref(0)
const format = ref<'keep' | ImgFormat>('jpeg')
const quality = ref(0.92)
const processingAll = ref(false)

async function onFiles(files: File[]) {
  for (const f of files.filter((x) => x.type.startsWith('image/'))) {
    try {
      const { width, height } = await loadImage(f)
      items.value.push({
        file: f,
        width,
        height,
        result: null,
        preview: URL.createObjectURL(f),
        processing: false
      })
    } catch {
      ElMessage.error(`读取失败：${f.name}`)
    }
  }
}

async function pickLogo() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = () => {
    if (input.files?.[0]) logoFile.value = input.files[0]
  }
  input.click()
}

function remove(idx: number) {
  URL.revokeObjectURL(items.value[idx].preview)
  items.value.splice(idx, 1)
}
function clearAll() {
  items.value.forEach((i) => URL.revokeObjectURL(i.preview))
  items.value = []
}

/** 九宫格坐标 -> 绘制锚点 */
function posXY(px: number, py: number, pw: number, ph: number) {
  const row = Math.floor((position.value - 1) / 3) // 0 上 1 中 2 下
  const col = (position.value - 1) % 3 // 0 左 1 中 2 右
  let x: number
  if (col === 0) x = margin.value
  else if (col === 1) x = (px - pw) / 2
  else x = px - pw - margin.value
  let y: number
  if (row === 0) y = margin.value
  else if (row === 1) y = (py - ph) / 2
  else y = py - ph - margin.value
  return { x, y }
}

function drawWatermark(canvas: HTMLCanvasElement, logoImg: HTMLImageElement | null) {
  const ctx = canvas.getContext('2d')!
  ctx.globalAlpha = opacity.value
  if (wmType.value === 'text' && text.value.trim()) {
    ctx.font = `${fontSize.value}px sans-serif`
    ctx.fillStyle = fontColor.value
    const m = ctx.measureText(text.value)
    const tw = m.width
    const th = fontSize.value
    if (tile.value) {
      const stepX = tw + tileGap.value
      const stepY = th + tileGap.value
      for (let y = stepY / 2; y < canvas.height + th; y += stepY) {
        for (let x = -tw; x < canvas.width + tw; x += stepX) {
          if (rotate.value) {
            ctx.save()
            ctx.translate(x + tw / 2, y)
            ctx.rotate((rotate.value * Math.PI) / 180)
            ctx.fillText(text.value, -tw / 2, 0)
            ctx.restore()
          } else {
            ctx.fillText(text.value, x, y)
          }
        }
      }
    } else {
      const { x, y } = posXY(canvas.width, canvas.height, tw, th)
      ctx.fillText(text.value, x, y + th)
    }
  } else if (wmType.value === 'logo' && logoImg) {
    const lw = (canvas.width * logoScale.value) / 100
    const lh = (lw * logoImg.naturalHeight) / logoImg.naturalWidth
    if (tile.value) {
      const stepX = lw + tileGap.value
      const stepY = lh + tileGap.value
      for (let y = margin.value; y < canvas.height; y += stepY) {
        for (let x = margin.value; x < canvas.width; x += stepX) {
          if (rotate.value) {
            ctx.save()
            ctx.translate(x + lw / 2, y + lh / 2)
            ctx.rotate((rotate.value * Math.PI) / 180)
            ctx.drawImage(logoImg, -lw / 2, -lh / 2, lw, lh)
            ctx.restore()
          } else {
            ctx.drawImage(logoImg, x, y, lw, lh)
          }
        }
      }
    } else {
      const { x, y } = posXY(canvas.width, canvas.height, lw, lh)
      ctx.drawImage(logoImg, x, y, lw, lh)
    }
  }
  ctx.globalAlpha = 1
}

const previewCanvas = ref<HTMLCanvasElement | null>(null)

async function renderPreview() {
  if (!items.value.length || !previewCanvas.value) return
  try {
    const it = items.value[0]
    const { img } = await loadImage(it.file)
    // 预览用缩小图提升性能
    const scale = Math.min(1, 720 / Math.max(it.width, it.height))
    const canvas = previewCanvas.value
    canvas.width = Math.round(it.width * scale)
    canvas.height = Math.round(it.height * scale)
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    let logoImg: HTMLImageElement | null = null
    if (wmType.value === 'logo' && logoFile.value) {
      logoImg = (await loadImage(logoFile.value)).img
    }
    // 预览时按比例缩放字体/间距
    const savedFs = fontSize.value
    const savedGap = tileGap.value
    const savedMargin = margin.value
    fontSize.value = Math.round(fontSize.value * scale)
    tileGap.value = Math.round(tileGap.value * scale)
    margin.value = Math.round(margin.value * scale)
    drawWatermark(canvas, logoImg)
    fontSize.value = savedFs
    tileGap.value = savedGap
    margin.value = savedMargin
  } catch {
    /* 预览失败忽略 */
  }
}

async function ensureLogo(): Promise<HTMLImageElement | null> {
  if (wmType.value === 'logo') {
    if (!logoFile.value) {
      ElMessage.warning('请先选择 Logo 图片')
      return null
    }
    return (await loadImage(logoFile.value)).img
  }
  if (!text.value.trim()) {
    ElMessage.warning('请输入水印文字')
    return null
  }
  return null
}

function outputMime() {
  const fmt = format.value === 'keep' ? 'jpeg' : format.value
  return `image/${fmt === 'jpeg' ? 'jpeg' : fmt}`
}
const outExt = computed(() => (format.value === 'keep' || format.value === 'jpeg' ? 'jpg' : format.value))

async function processOne(idx: number, logoImg: HTMLImageElement | null) {
  const it = items.value[idx]
  it.processing = true
  try {
    const { img } = await loadImage(it.file)
    const canvas = document.createElement('canvas')
    canvas.width = it.width
    canvas.height = it.height
    const ctx = canvas.getContext('2d')!
    if (outputMime() === 'image/jpeg') {
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
    }
    ctx.drawImage(img, 0, 0)
    drawWatermark(canvas, logoImg)
    it.result = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('编码失败'))), outputMime(), quality.value)
    })
  } catch (e) {
    ElMessage.error(`处理失败 ${it.file.name}：` + (e as Error).message)
  } finally {
    it.processing = false
  }
}

async function processAll() {
  const logoImg = await ensureLogo()
  if (wmType.value === 'logo' && !logoImg) return
  if (wmType.value === 'text' && !text.value.trim()) return
  processingAll.value = true
  for (let i = 0; i < items.value.length; i++) await processOne(i, logoImg)
  processingAll.value = false
  ElMessage.success('全部加印完成')
}

function downloadOne(idx: number) {
  const it = items.value[idx]
  if (it.result) downloadBlob(it.result, `${baseName(it.file.name)}_wm.${outExt.value}`)
}

async function downloadAll() {
  const logoImg = await ensureLogo()
  if (wmType.value === 'text' && !text.value.trim()) return
  if (wmType.value === 'logo' && !logoImg) return
  processingAll.value = true
  for (let i = 0; i < items.value.length; i++) if (!items.value[i].result) await processOne(i, logoImg)
  processingAll.value = false
  const outs = items.value
    .filter((i) => i.result)
    .map((i) => ({ blob: i.result!, name: `${baseName(i.file.name)}_wm.${outExt.value}` }))
  if (outs.length) await downloadFilesAsZip(outs, '图片水印.zip')
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <FileDropZone accept="image/*" hint="支持批量添加水印" @files="onFiles" />

    <div v-if="items.length" class="grid md:grid-cols-5 gap-5">
      <!-- 左侧参数 -->
      <div class="md:col-span-3 card p-5 space-y-4">
        <div>
          <label class="text-sm text-text-soft block mb-1">水印类型</label>
          <el-radio-group v-model="wmType">
            <el-radio value="text">文字水印</el-radio>
            <el-radio value="logo">Logo 图片</el-radio>
          </el-radio-group>
        </div>

        <div v-if="wmType === 'text'" class="space-y-3">
          <el-input v-model="text" placeholder="水印文字内容" maxlength="50" show-word-limit />
          <div class="flex flex-wrap items-center gap-4">
            <div>
              <span class="text-sm text-text-mute mr-2">字号</span>
              <el-input-number v-model="fontSize" :min="8" :max="300" />
            </div>
            <div>
              <span class="text-sm text-text-mute mr-2">颜色</span>
              <el-color-picker v-model="fontColor" />
            </div>
          </div>
        </div>
        <div v-else class="space-y-3">
          <button class="btn-ghost !border !border-border" @click="pickLogo">
            <el-icon><Upload /></el-icon> {{ logoFile ? logoFile.name : '选择 Logo 图片' }}
          </button>
          <div>
            <span class="text-sm text-text-mute mr-2">Logo 宽度占图 {{ logoScale }}%</span>
            <el-slider v-model="logoScale" :min="2" :max="100" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-text-soft block mb-1">透明度 {{ opacity.toFixed(2) }}</label>
            <el-slider v-model="opacity" :min="0.05" :max="1" :step="0.05" />
          </div>
          <div>
            <label class="text-sm text-text-soft block mb-1">旋转角度 {{ rotate }}°</label>
            <el-slider v-model="rotate" :min="-90" :max="90" :step="15" />
          </div>
        </div>

        <div>
          <label class="text-sm text-text-soft block mb-2">位置</label>
          <div class="grid grid-cols-3 gap-1 w-40">
            <button
              v-for="p in 9"
              :key="p"
              class="h-9 rounded border transition-all"
              :class="
                position === p
                  ? 'bg-primary text-white border-primary'
                  : 'border-border hover:border-primary'
              "
              @click="position = p"
            ></button>
          </div>
          <div class="mt-2">
            <span class="text-sm text-text-mute mr-2">边距</span>
            <el-input-number v-model="margin" :min="0" :max="500" />
          </div>
        </div>

        <div>
          <el-checkbox v-model="tile">平铺模式</el-checkbox>
          <span v-if="tile" class="text-sm text-text-mute ml-2 mr-2">间隔</span>
          <el-input-number v-if="tile" v-model="tileGap" :min="20" :max="600" />
        </div>

        <div class="h-px bg-border"></div>

        <div>
          <label class="text-sm text-text-soft block mb-1">输出格式</label>
          <el-radio-group v-model="format">
            <el-radio value="keep">保持原格式</el-radio>
            <el-radio value="jpeg">JPG</el-radio>
            <el-radio value="png">PNG</el-radio>
            <el-radio value="webp">WebP</el-radio>
          </el-radio-group>
          <div v-if="format !== 'keep' && format !== 'png'" class="mt-2">
            <span class="text-sm text-text-mute mr-2">质量 {{ quality.toFixed(2) }}</span>
            <el-slider v-model="quality" :min="0.3" :max="1" :step="0.01" class="w-40 inline-block align-middle" />
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
          <button class="btn-primary" :disabled="processingAll" @click="processAll">
            <el-icon v-if="processingAll" class="animate-spin"><Loading /></el-icon>
            <el-icon v-else><MagicStick /></el-icon> 全部加印
          </button>
          <button class="btn-ghost !border !border-border" @click="downloadAll">
            <el-icon><Download /></el-icon> 下载全部（ZIP）
          </button>
          <button class="btn-ghost text-text-mute ml-auto" @click="clearAll">清空</button>
        </div>
      </div>

      <!-- 右侧预览 -->
      <div class="md:col-span-2 space-y-3">
        <div class="card p-3">
          <div class="text-sm font-medium mb-2 flex items-center gap-1">
            <el-icon><View /></el-icon> 实时预览（第 1 张）
          </div>
          <canvas ref="previewCanvas" class="w-full rounded border border-border bg-bg-soft"></canvas>
          <button class="btn-ghost w-full mt-2 justify-center" @click="renderPreview">
            <el-icon><Refresh /></el-icon> 刷新预览
          </button>
        </div>
        <ul class="card divide-y divide-border-soft max-h-48 overflow-auto">
          <li v-for="(it, i) in items" :key="i" class="flex items-center gap-2 p-2 text-sm">
            <span class="truncate flex-1">{{ it.file.name }}</span>
            <span class="text-xs text-text-mute">{{ formatBytes(it.file.size) }}</span>
            <el-icon v-if="it.processing" class="animate-spin text-primary"><Loading /></el-icon>
            <el-icon v-else-if="it.result" class="text-green-500"><CircleCheckFilled /></el-icon>
            <button v-if="it.result" class="btn-ghost !px-1" @click="downloadOne(i)">
              <el-icon><Download /></el-icon>
            </button>
            <button class="btn-ghost !px-1 hover:text-red-500" @click="remove(i)">
              <el-icon><Delete /></el-icon>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
