<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ToolCard from '@/components/common/ToolCard.vue'
import { categories, tools, type ToolMeta } from '@/config/tools'
import { usePreferenceStore } from '@/stores/preference'

const route = useRoute()
const router = useRouter()
const pref = usePreferenceStore()

const activeCat = ref<string>((route.query.cat as string) || 'all')
const keyword = ref<string>((route.query.q as string) || '')
const onlyFavorites = ref(route.query.filter === 'favorites')

// URL <-> state 同步
watch(
  () => [route.query.cat, route.query.q, route.query.filter],
  ([cat, q, filter]) => {
    activeCat.value = (cat as string) || 'all'
    keyword.value = (q as string) || ''
    onlyFavorites.value = filter === 'favorites'
  }
)

function syncQuery() {
  const query: Record<string, string> = {}
  if (activeCat.value !== 'all') query.cat = activeCat.value
  if (keyword.value.trim()) query.q = keyword.value.trim()
  if (onlyFavorites.value) query.filter = 'favorites'
  router.replace({ path: '/tools', query })
}

function setCat(id: string) {
  activeCat.value = id
  syncQuery()
}

let searchTimer: number | undefined
function onSearchInput() {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(syncQuery, 300)
}

function toggleFavFilter() {
  onlyFavorites.value = !onlyFavorites.value
  syncQuery()
}

const filtered = computed<ToolMeta[]>(() => {
  let list = tools
  if (onlyFavorites.value) list = list.filter((t) => pref.isFavorite(t.slug))
  if (activeCat.value !== 'all') list = list.filter((t) => t.categoryId === activeCat.value)
  const kw = keyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (t) =>
        t.name.toLowerCase().includes(kw) ||
        t.description.toLowerCase().includes(kw) ||
        t.keywords.some((k) => k.toLowerCase().includes(kw))
    )
  }
  // online 优先，再按 priority
  const order = { P0: 0, P1: 1, P2: 2 }
  return [...list].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'online' ? -1 : 1
    return order[a.priority] - order[b.priority]
  })
})
</script>

<template>
  <div class="container-page py-8">
    <div class="mb-6">
      <h1 class="text-2xl font-bold">工具大全</h1>
      <p class="text-text-soft mt-1">全部分类工具一览，支持搜索与筛选</p>
    </div>

    <div class="flex flex-col lg:flex-row gap-6">
      <!-- 侧边分类 -->
      <aside class="lg:w-56 shrink-0">
        <div class="card p-3 lg:sticky lg:top-20">
          <button
            class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between"
            :class="activeCat === 'all' ? 'bg-primary-soft text-primary font-medium' : 'hover:bg-bg-soft'"
            @click="setCat('all')"
          >
            <span class="flex items-center gap-2"><el-icon><Menu /></el-icon> 全部工具</span>
            <span class="text-xs text-text-mute">{{ tools.length }}</span>
          </button>
          <div class="h-px bg-border my-2"></div>
          <button
            v-for="c in categories"
            :key="c.id"
            class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between"
            :class="activeCat === c.id ? 'bg-primary-soft text-primary font-medium' : 'hover:bg-bg-soft'"
            @click="setCat(c.id)"
          >
            <span class="flex items-center gap-2">
              <el-icon :style="{ color: c.color }"><component :is="c.icon" /></el-icon>
              {{ c.name }}
            </span>
            <span class="text-xs text-text-mute">
              {{ tools.filter((t) => t.categoryId === c.id).length }}
            </span>
          </button>
          <div class="h-px bg-border my-2"></div>
          <button
            class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between"
            :class="onlyFavorites ? 'bg-primary-soft text-primary font-medium' : 'hover:bg-bg-soft'"
            @click="toggleFavFilter"
          >
            <span class="flex items-center gap-2"><el-icon><StarFilled /></el-icon> 我的收藏</span>
            <span class="text-xs text-text-mute">{{ pref.favorites.length }}</span>
          </button>
        </div>
      </aside>

      <!-- 主区域 -->
      <div class="flex-1 min-w-0">
        <el-input
          v-model="keyword"
          placeholder="搜索工具名称、关键词…"
          :prefix-icon="'Search'"
          clearable
          size="large"
          class="mb-4"
          @input="onSearchInput"
          @clear="syncQuery"
        />

        <div class="flex items-center justify-between mb-4">
          <p class="text-sm text-text-mute">共 {{ filtered.length }} 个工具</p>
          <button
            v-if="keyword || activeCat !== 'all' || onlyFavorites"
            class="text-sm text-primary hover:underline"
            @click="
              ((activeCat = 'all'), (keyword = ''), (onlyFavorites = false)), syncQuery()
            "
          >
            重置筛选
          </button>
        </div>

        <div v-if="filtered.length" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          <ToolCard v-for="t in filtered" :key="t.slug" :tool="t" />
        </div>
        <div v-else class="card p-12 text-center text-text-mute">
          <el-icon :size="40" class="mb-2"><Search /></el-icon>
          <p>未找到匹配的工具</p>
        </div>
      </div>
    </div>
  </div>
</template>
