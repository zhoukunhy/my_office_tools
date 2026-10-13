<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadBlob } from '@/utils/file'
import { loadImage, type ImgFormat } from '@/utils/image'

interface Item {
  file: File
  img: HTMLImageElement
  width: number
  height: number
}

const items = ref<Item[]>([])
const direction = ref<'vertical' | 'horizontal'>('vertical')
const gap = ref(0)
const bgColor = ref('#ffffff')
type Align = 'start' | 'center' | 'end'
const align = ref<Align>('center')
const normalize = ref(true) // 统一宽度/高度
const format = ref<ImgFormat>('png')
const quality = ref(0.92)
const rendering = ref(false)

async function onFiles(files: File[]) {
  for (const f of files.filter((x) => x.type.startsWith('image/'))) {
    try {
      const { img, width, height } = await loadImage(f)
      items.value.push({ file: f, img, width, height })
    } catch {
      ElMessage.error(`读取失败：${f.name}`)
    }
  }
}

function remove(idx: number) {
  items.value.splice(idx, 1)
}
function move(idx: number, dir: -1 | 1) {
  const t = idx + dir
  if (t < 0 || t >= items.value.length) return
  ;[items.value[idx], items.value[t]] = [items.value[t], items.value[idx]]
}

/** 计算画布尺寸与每图布局 */
function layout() {
  const list = items.value
  if (!list.length) return null
  if (direction.value === 'vertical') {
    const targetW = normalize.value ? Math.max(...list.map((i) => i.width)) : 0
    let totalH = 0
    const slots: { x: number; y: number; w: number; h: number }[] = []
    let y = 0
    for (const it of list) {
      const w = normalize.value ? targetW : it.width
      const h = normalize.value ? Math.round((it.height * w) / it.width) : it.height
      const x =
        align.value === 'start'
          ? 0
          : align.value === 'end'
            ? maxW(list, w) - w
            : Math.round((maxW(list, w) - w) / 2)
      slots.push({ x, y, w, h })
      y += h + gap.value
    }
    totalH = y - (list.length ? gap.value : 0)
    return { width: maxW(list, normalize.value ? targetW : 0), height: totalH, slots }
  } else {
    const targetH = normalize.value ? Math.max(...list.map((i) => i.height)) : 0
    let x = 0
    const slots: { x: number; y: number; w: number; h: number }[] = []
    for (const it of list) {
      const h = normalize.value ? targetH : it.height
      const w = normalize.value ? Math.round((it.width * h) / it.height) : it.width
      const y =
        align.value === 'start' ? 0 : align.value === 'end' ? maxH(list, h) - h : Math.round((maxH(list, h) - h) / 2)
      slots.push({ x, y, w, h })
      x += w + gap.value
    }
    const totalW = x - (list.length ? gap.value : 0)
    return { width: totalW, height: maxH(list, normalize.value ? targetH : 0), slots }
  }
}

function maxW(list: Item[], fallback: number) {
  if (normalize.value) return fallback || Math.max(...list.map((i) => i.width))
  return Math.max(...list.map((i) => i.width))
}
function maxH(list: Item[], fallback: number) {
  if (normalize.value) return fallback || Math.max(...list.map((i) => i.height))
  return Math.max(...list.map((i) => i.height))
}

const outSize = computed(() => {
  const l = layout()
  return l ? `${l.width} × ${l.height}px` : '—'
})

async function stitch() {
  if (items.value.length < 2) {
    ElMessage.warning('至少需要 2 张图片')
    return
  }
  rendering.value = true
  try {
    const l = layout()!
    const canvas = document.createElement('canvas')
    canvas.width = l.width
    canvas.height = l.height
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = bgColor.value
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    l.slots.forEach((s, i) => {
      ctx.drawImage(items.value[i].img, s.x, s.y, s.w, s.h)
    })
    const mime = format.value === 'png' ? 'image/png' : `image/${format.value}`
    const q = format.value === 'png' ? 1 : quality.value
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('编码失败'))), mime, q)
    })
    const ext = format.value === 'jpeg' ? 'jpg' : format.value
    downloadBlob(blob, `拼接长图.${ext}`)
    ElMessage.success(`拼接完成：${canvas.width}×${canvas.height}`)
  } catch (e) {
    ElMessage.error('拼接失败：' + (e as Error).message)
  } finally {
    rendering.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <FileDropZone accept="image/*" hint="按列表顺序拼接，可调整顺序" @files="onFiles" />

    <div v-if="items.length" class="grid md:grid-cols-5 gap-5">
      <!-- 参数 -->
      <div class="md:col-span-2 card p-5 space-y-4">
        <div>
          <label class="text-sm text-text-soft block mb-1">拼接方向</label>
          <el-radio-group v-model="direction">
            <el-radio value="vertical">纵向（长图）</el-radio>
            <el-radio value="horizontal">横向</el-radio>
          </el-radio-group>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <span class="text-sm text-text-mute block mb-1">间距 {{ gap }}px</span>
            <el-slider v-model="gap" :min="0" :max="200" />
          </div>
          <div>
            <span class="text-sm text-text-mute block mb-1">背景色</span>
            <el-color-picker v-model="bgColor" />
          </div>
        </div>

        <div>
          <label class="text-sm text-text-soft block mb-1">对齐方式</label>
          <el-radio-group v-model="align">
            <el-radio value="start">{{ direction === 'vertical' ? '靠左' : '靠上' }}</el-radio>
            <el-radio value="center">居中</el-radio>
            <el-radio value="end">{{ direction === 'vertical' ? '靠右' : '靠下' }}</el-radio>
          </el-radio-group>
        </div>

        <div>
          <el-checkbox v-model="normalize">
            统一{{ direction === 'vertical' ? '宽度' : '高度' }}（等比缩放对齐）
          </el-checkbox>
        </div>

        <div>
          <label class="text-sm text-text-soft block mb-1">输出格式</label>
          <el-radio-group v-model="format">
            <el-radio value="png">PNG</el-radio>
            <el-radio value="jpeg">JPG</el-radio>
            <el-radio value="webp">WebP</el-radio>
          </el-radio-group>
          <div v-if="format !== 'png'" class="mt-2">
            <span class="text-sm text-text-mute mr-2">质量 {{ quality.toFixed(2) }}</span>
            <el-slider v-model="quality" :min="0.3" :max="1" :step="0.01" class="w-36 inline-block align-middle" />
          </div>
        </div>

        <div class="text-sm text-text-soft">输出尺寸：{{ outSize }}</div>

        <button class="btn-primary w-full" :disabled="rendering" @click="stitch">
          <el-icon v-if="rendering" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><Download /></el-icon>
          {{ rendering ? '拼接中…' : '拼接并下载' }}
        </button>
      </div>

      <!-- 顺序列表 -->
      <div class="md:col-span-3 card p-4">
        <div class="text-sm font-medium mb-3">图片顺序（自上而下 / 自左而右）</div>
        <ul class="space-y-2">
          <li
            v-for="(it, i) in items"
            :key="i"
            class="flex items-center gap-3 p-2 rounded-md hover:bg-bg-soft"
          >
            <span
              class="w-6 h-6 rounded bg-primary-soft text-primary text-xs flex items-center justify-center shrink-0"
              >{{ i + 1 }}</span
            >
            <img :src="it.img.src" class="w-12 h-12 object-cover rounded border border-border" alt="" />
            <div class="min-w-0 flex-1">
              <div class="text-sm truncate">{{ it.file.name }}</div>
              <div class="text-xs text-text-mute">
                {{ it.width }}×{{ it.height }} · {{ formatBytes(it.file.size) }}
              </div>
            </div>
            <button class="btn-ghost !px-1.5" :disabled="i === 0" @click="move(i, -1)">
              <el-icon><ArrowUp /></el-icon>
            </button>
            <button class="btn-ghost !px-1.5" :disabled="i === items.length - 1" @click="move(i, 1)">
              <el-icon><ArrowDown /></el-icon>
            </button>
            <button class="btn-ghost !px-1.5 hover:text-red-500" @click="remove(i)">
              <el-icon><Delete /></el-icon>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
