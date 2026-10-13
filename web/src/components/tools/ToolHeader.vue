<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { categories, getToolBySlug, type ToolMeta } from '@/config/tools'
import { usePreferenceStore } from '@/stores/preference'

const props = withDefaults(
  defineProps<{
    /** 工具 slug：当 ToolRunner 通用壳里用时自动带入 */
    slug?: string
    /** 当直接在具体 View 内作为简单页头使用时，可直接给 title/description，不用 slug 查询 */
    title?: string
    description?: string
  }>(),
  { slug: undefined, title: undefined, description: undefined }
)

const router = useRouter()
const pref = usePreferenceStore()

const tool = computed<ToolMeta | null>(() => (props.slug ? getToolBySlug(props.slug) ?? null : null))
const cat = computed(() => categories.find((c) => c.id === tool.value?.categoryId))
const isFav = computed(() => (tool.value ? pref.isFavorite(tool.value.slug) : false))

/** 显示模式：true=工具详情模式(走 slug 查询)；false=通用模式(title/description 直接传) */
const toolMode = computed(() => !!tool.value)
const t = computed(() => tool.value as ToolMeta)

const showTitle = computed(() => props.title ?? tool.value?.name ?? '')
const showDesc = computed(() => props.description ?? tool.value?.description ?? '')
</script>

<template>
  <div class="mb-6">
    <!-- 面包屑：当存在 tool slug 时展示完整链路；否则只给简短头部 -->
    <nav v-if="toolMode" class="text-sm text-text-mute flex items-center gap-1 mb-3">
      <RouterLink to="/" class="hover:text-primary">首页</RouterLink>
      <span>/</span>
      <RouterLink to="/tools" class="hover:text-primary">工具大全</RouterLink>
      <span>/</span>
      <button class="hover:text-primary" @click="router.push(`/tools?cat=${cat?.id}`)">
        {{ cat?.name }}
      </button>
      <span>/</span>
      <span class="text-text-soft">{{ t.name }}</span>
    </nav>

    <div class="flex items-start gap-4">
      <div
        v-if="toolMode"
        class="shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-sm"
        :style="{ background: `linear-gradient(135deg, ${cat?.color}, ${cat?.color}cc)` }"
      >
        <el-icon :size="24"><component :is="t.icon" /></el-icon>
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-3 flex-wrap">
          <h1 class="text-xl sm:text-2xl font-bold tracking-tight">{{ showTitle }}</h1>
          <span
            v-if="toolMode"
            class="tag"
            :class="t.status === 'online' ? 'text-primary' : ''"
            :style="t.status === 'online' ? 'background: var(--c-primary-soft)' : ''"
          >
            {{ t.status === 'online' ? '可用' : '即将上线' }}
          </span>
          <!-- 状态顶部插槽：例如 PDF 压缩提示"后端加速已开启" -->
          <slot name="statusTop" />
        </div>
        <p v-if="showDesc" class="text-text-soft mt-1">{{ showDesc }}</p>
      </div>
      <button
        v-if="toolMode && t.status === 'online'"
        class="btn-ghost"
        :class="{ 'text-primary': isFav }"
        title="收藏"
        @click="pref.toggleFavorite(t.slug)"
      >
        <el-icon :size="20"><component :is="isFav ? 'StarFilled' : 'Star'" /></el-icon>
        <span class="hidden sm:inline">{{ isFav ? '已收藏' : '收藏' }}</span>
      </button>
    </div>
  </div>
</template>
