<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ThemeToggle from '@/components/common/ThemeToggle.vue'
import { usePreferenceStore } from '@/stores/preference'
import { tools } from '@/config/tools'

const router = useRouter()
const pref = usePreferenceStore()

const keyword = ref('')
const showSuggest = ref(false)

const suggestions = ref<typeof tools>([])

function onInput() {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) {
    suggestions.value = []
    return
  }
  suggestions.value = tools
    .filter(
      (t) =>
        t.name.toLowerCase().includes(kw) ||
        t.description.toLowerCase().includes(kw) ||
        t.keywords.some((k) => k.toLowerCase().includes(kw))
    )
    .slice(0, 6)
}

function goSearch() {
  const kw = keyword.value.trim()
  if (!kw) return
  router.push({ path: '/tools', query: { q: kw } })
  showSuggest.value = false
}

function pick(slug: string) {
  router.push(`/tool/${slug}`)
  showSuggest.value = false
  keyword.value = ''
  suggestions.value = []
}

function hideSuggest() {
  window.setTimeout(() => (showSuggest.value = false), 150)
}
</script>

<template>
  <header
    class="sticky top-0 z-50 backdrop-blur-md border-b border-border"
    style="background-color: color-mix(in srgb, var(--c-card) 85%, transparent)"
  >
    <div class="container-page h-14 flex items-center gap-3">
      <!-- Logo -->
      <RouterLink to="/" class="flex items-center gap-2 shrink-0">
        <img src="/favicon.svg" alt="logo" class="w-7 h-7" />
        <span class="font-bold text-base sm:text-lg tracking-tight">速用工具箱</span>
      </RouterLink>

      <!-- 导航（md 以上） -->
      <nav class="hidden md:flex items-center gap-1 ml-2">
        <RouterLink to="/" class="btn-ghost" active-class="text-primary">首页</RouterLink>
        <RouterLink to="/tools" class="btn-ghost" active-class="text-primary">工具大全</RouterLink>
        <RouterLink to="/resume" class="btn-ghost" active-class="text-primary">简历制作</RouterLink>
        <RouterLink to="/ai-ppt" class="btn-ghost" active-class="text-primary">AI 生成PPT</RouterLink>
        <RouterLink to="/favorites" class="btn-ghost" active-class="text-primary">我的收藏</RouterLink>
        <RouterLink to="/me" class="btn-ghost" active-class="text-primary">个人中心</RouterLink>
      </nav>

      <!-- 搜索 -->
      <div class="flex-1 max-w-md ml-auto relative">
        <el-input
          v-model="keyword"
          placeholder="搜索工具，如 PDF 合并、二维码…"
          :prefix-icon="'Search'"
          clearable
          size="default"
          @input="onInput"
          @focus="showSuggest = true"
          @blur="hideSuggest"
          @keyup.enter="goSearch"
        />
        <div
          v-if="showSuggest && suggestions.length"
          class="absolute left-0 right-0 mt-1 card overflow-hidden shadow-md z-50"
        >
          <button
            v-for="s in suggestions"
            :key="s.slug"
            class="w-full flex items-center gap-2 px-3 py-2 hover:bg-bg-soft text-left transition-colors"
            @mousedown.prevent="pick(s.slug)"
          >
            <el-icon :size="16" class="text-text-mute"><component :is="s.icon" /></el-icon>
            <span class="text-sm">{{ s.name }}</span>
            <span class="ml-auto text-xs text-text-mute line-clamp-1 max-w-[50%]">{{
              s.description
            }}</span>
          </button>
        </div>
      </div>

      <!-- 收藏计数徽标（仅 sm 以上，tab 栏本身也有入口） -->
      <RouterLink
        to="/favorites"
        class="btn-ghost hidden sm:inline-flex relative"
        title="我的收藏"
      >
        <el-icon :size="18"><StarFilled /></el-icon>
        <span
          v-if="pref.favorites.length"
          class="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full text-[10px] text-white inline-flex items-center justify-center"
          style="background-color: var(--c-danger)"
        >
          {{ pref.favorites.length > 9 ? '9+' : pref.favorites.length }}
        </span>
      </RouterLink>

      <ThemeToggle />
    </div>
  </header>
</template>
