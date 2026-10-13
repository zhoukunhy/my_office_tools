<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { formatBytes, downloadFilesAsZip, baseName } from '@/utils/file'
import { loadImage, encodeImage, type ImgFormat } from '@/utils/image'

interface Item {
  file: File
  preview: string
  result: Blob | null
  processing: boolean
}

const items = ref<Item[]>([])
const target = ref<ImgFormat>('webp')
const quality = ref(0.9)
const processingAll = ref(false)

async function onFiles(files: File[]) {
  for (const f of files.filter((x) => x.type.startsWith('image/'))) {
    items.value.push({ file: f, preview: URL.createObjectURL(f), result: null, processing: false })
  }
}
function remove(idx: number) {
  URL.revokeObjectURL(items.value[idx].preview)
  items.value.splice(idx, 1)
}
function clearAll() {
  items.value.forEach((i) => URL.revokeObjectURL(i.preview))
  items.value = []
}

async function convertOne(idx: number) {
  const it = items.value[idx]
  it.processing = true
  try {
    const { img } = await loadImage(it.file)
    const q = target.value === 'png' ? 1 : quality.value
    it.result = await encodeImage(img, target.value, q)
  } catch (e) {
    ElMessage.error('转换失败：' + (e as Error).message)
  } finally {
    it.processing = false
  }
}

async function convertAll() {
  processingAll.value = true
  for (let i = 0; i < items.value.length; i++) await convertOne(i)
  processingAll.value = false
  ElMessage.success('全部转换完成')
}

async function downloadAll() {
  for (let i = 0; i < items.value.length; i++) if (!items.value[i].result) await convertOne(i)
  const outs = items.value
    .filter((i) => i.result)
    .map((i) => ({
      blob: i.result!,
      name: `${baseName(i.file.name)}.${target.value === 'jpeg' ? 'jpg' : target.value}`
    }))
  if (outs.length) await downloadFilesAsZip(outs, '格式转换.zip')
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <FileDropZone accept="image/*" hint="PNG / JPG / WebP 批量互转" @files="onFiles" />

    <div v-if="items.length" class="card p-5 space-y-4">
      <div class="flex flex-col sm:flex-row gap-4 sm:items-end">
        <div>
          <label class="text-sm text-text-soft block mb-1">目标格式</label>
          <el-radio-group v-model="target">
            <el-radio value="png">PNG</el-radio>
            <el-radio value="jpeg">JPG</el-radio>
            <el-radio value="webp">WebP</el-radio>
          </el-radio-group>
        </div>
        <div v-if="target !== 'png'">
          <label class="text-sm text-text-soft block mb-1">质量：{{ quality.toFixed(2) }}</label>
          <el-slider v-model="quality" :min="0.3" :max="1" :step="0.01" />
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" :disabled="processingAll" @click="convertAll">
          <el-icon v-if="processingAll" class="animate-spin"><Loading /></el-icon>
          <el-icon v-else><MagicStick /></el-icon> 全部转换
        </button>
        <button class="btn-ghost !border !border-border" @click="downloadAll">
          <el-icon><Download /></el-icon> 下载全部（ZIP）
        </button>
        <button class="btn-ghost text-text-mute ml-auto" @click="clearAll">清空</button>
      </div>

      <ul class="space-y-2">
        <li
          v-for="(it, i) in items"
          :key="i"
          class="flex items-center gap-3 p-2 rounded-md hover:bg-bg-soft"
        >
          <img :src="it.preview" class="w-12 h-12 object-cover rounded border border-border" alt="" />
          <div class="min-w-0 flex-1">
            <div class="text-sm truncate">{{ it.file.name }}</div>
            <div class="text-xs text-text-mute">{{ formatBytes(it.file.size) }}</div>
          </div>
          <el-icon v-if="it.processing" class="animate-spin text-primary"><Loading /></el-icon>
          <el-icon v-else-if="it.result" class="text-green-500"><CircleCheckFilled /></el-icon>
          <button class="btn-ghost !px-1.5 hover:text-red-500" @click="remove(i)">
            <el-icon><Delete /></el-icon>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
