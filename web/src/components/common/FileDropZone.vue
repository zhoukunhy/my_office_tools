<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { formatBytes } from '@/utils/file'

const props = withDefaults(
  defineProps<{
    accept?: string
    multiple?: boolean
    hint?: string
    title?: string
    /** 单文件大小上限（字节），0 表示不限 */
    maxSize?: number
    chunkLabel?: string
    /** 已上传文件（外部统计显示用） */
    currentCount?: number
  }>(),
  {
    accept: '',
    multiple: true,
    hint: '',
    title: '',
    maxSize: 0,
    chunkLabel: '',
    currentCount: 0
  }
)

const emit = defineEmits<{
  (e: 'files', files: File[]): void
}>()

const dragOver = ref(false)
const inputRef = ref<HTMLInputElement>()

function handleFiles(list: FileList | null) {
  if (!list || list.length === 0) return
  let files = Array.from(list)
  if (!props.multiple) files = files.slice(0, 1)

  if (props.maxSize > 0) {
    const over = files.filter((f) => f.size > props.maxSize)
    if (over.length) {
      ElMessage.error(`有 ${over.length} 个文件超过单文件上限 ${formatBytes(props.maxSize)}，已跳过`)
      files = files.filter((f) => f.size <= props.maxSize)
    }
  }
  if (files.length) emit('files', files)
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files) handleFiles(e.dataTransfer.files)
}

function onPick() {
  inputRef.value?.click()
}

function onInput(e: Event) {
  handleFiles((e.target as HTMLInputElement).files)
  // 允许重复选择同一文件
  if (inputRef.value) inputRef.value.value = ''
}

const labelTitle = computed(
  () => props.title || (props.multiple ? '拖拽 / 选择文件（支持批量追加）' : '拖拽 / 选择文件')
)
</script>

<template>
  <div class="mb-4">
    <div class="flex items-center justify-between mb-2">
      <h4 class="text-sm font-semibold">
        {{ chunkLabel ? chunkLabel : (multiple ? '① 上传文件' : '① 上传文件') }}
      </h4>
      <span v-if="currentCount" class="text-xs text-text-mute">
        已添加 <span class="text-primary font-medium">{{ currentCount }}</span> 个
      </span>
    </div>
    <div
      class="drop-chunk-block cursor-pointer"
      :class="{ 'is-over': dragOver }"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="onDrop"
      @click="onPick"
    >
      <input
        ref="inputRef"
        type="file"
        class="hidden"
        :accept="accept"
        :multiple="multiple"
        @change="onInput"
      />
      <el-icon :size="30" class="text-primary mb-1"><UploadFilled /></el-icon>
      <p class="font-medium text-sm">{{ labelTitle }}</p>
      <p class="text-xs text-text-mute mt-1">
        {{ hint || (multiple ? '支持批量追加，处理前可单独删除 / 排序' : '点击选择一个文件') }}
      </p>
    </div>
  </div>
</template>
