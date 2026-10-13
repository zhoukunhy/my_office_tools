<script setup lang="ts">
import { computed } from 'vue'
import { formatBytes } from '@/utils/file'

export interface BatchFileItem {
  id: string
  name: string
  size: number
  /** 'wait' | 'process' | 'done' | 'error' */
  status?: 'wait' | 'process' | 'done' | 'error'
  progress?: number // 0..100
  message?: string
  previewUrl?: string
  /** 原始 File 对象（页面内部使用，不强绑定为必填） */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

const props = withDefaults(
  defineProps<{
    items: BatchFileItem[]
    removable?: boolean
    deletable?: boolean // 单独删除
    /** 开启后点击缩略图可预览大图（需页面监听 @preview 事件） */
    previewable?: boolean
  }>(),
  { removable: true, deletable: true, previewable: false }
)

const emit = defineEmits<{
  (e: 'remove', id: string): void
  (e: 'move', from: number, to: number): void
  (e: 'clearAll'): void
  (e: 'preview', item: BatchFileItem): void
}>()

const totalSize = computed(() => props.items.reduce((s, x) => s + x.size, 0))
</script>

<template>
  <div v-if="items.length" class="mb-4">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm text-text-soft">
        共 <span class="font-medium text-text">{{ items.length }}</span> 个文件 · 总大小
        <span class="font-medium text-text">{{ formatBytes(totalSize) }}</span>
      </div>
      <button
        v-if="removable"
        class="btn-ghost btn-ghost-danger !py-1 text-xs"
        @click="emit('clearAll')"
      >
        <el-icon :size="14"><Delete /></el-icon> 清空列表
      </button>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
      <div
        v-for="(it, idx) in items"
        :key="it.id"
        class="card !shadow-xs p-2.5 flex items-center gap-2.5 relative overflow-hidden"
      >
        <!-- 进度背景条 -->
        <div
          v-if="it.status === 'process' && it.progress !== undefined"
          class="absolute left-0 top-0 bottom-0 z-0"
          :style="{
            width: `${it.progress}%`,
            background: 'var(--c-primary-soft)'
          }"
        />
        <div
          class="relative z-10 w-10 h-10 rounded-md overflow-hidden shrink-0 border border-border bg-bg-soft flex items-center justify-center"
          :class="{ 'cursor-zoom-in': previewable && it.previewUrl }"
          :title="previewable && it.previewUrl ? '点击预览大图' : undefined"
          @click="previewable && it.previewUrl && emit('preview', it)"
        >
          <img
            v-if="it.previewUrl"
            :src="it.previewUrl"
            :alt="it.name"
            class="w-full h-full object-cover"
          />
          <el-icon v-else :size="18" class="text-text-mute"><Document /></el-icon>
        </div>
        <div class="relative z-10 min-w-0 flex-1">
          <div class="truncate text-sm font-medium">{{ it.name }}</div>
          <div class="flex items-center gap-2 text-[11px] text-text-mute">
            <span>{{ formatBytes(it.size) }}</span>
            <span v-if="it.status === 'process'" class="text-primary">
              处理中 {{ Math.round(it.progress ?? 0) }}%
            </span>
            <span v-else-if="it.status === 'done'" class="text-success">已完成</span>
            <span v-else-if="it.status === 'error'" class="text-danger">{{ it.message || '出错' }}</span>
          </div>
        </div>
        <div class="relative z-10 flex items-center gap-1">
          <button
            v-if="idx > 0"
            class="btn-ghost !py-1 !px-1.5"
            title="上移"
            @click="emit('move', idx, idx - 1)"
          >
            <el-icon :size="14"><ArrowUp /></el-icon>
          </button>
          <button
            v-if="idx < items.length - 1"
            class="btn-ghost !py-1 !px-1.5"
            title="下移"
            @click="emit('move', idx, idx + 1)"
          >
            <el-icon :size="14"><ArrowDown /></el-icon>
          </button>
          <button
            v-if="deletable"
            class="btn-ghost btn-ghost-danger !py-1 !px-1.5"
            title="删除"
            @click="emit('remove', it.id)"
          >
            <el-icon :size="14"><Close /></el-icon>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
