<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import ToolCard from '@/components/common/ToolCard.vue'
import { categories, getHotTools, getToolsByCategory } from '@/config/tools'
import { usePreferenceStore } from '@/stores/preference'

const router = useRouter()
const pref = usePreferenceStore()

const hotTools = getHotTools()
const stats = {
  tools: 24,
  categories: categories.length,
  cost: '0'
}

const onlineTools = computed(() => categories.map((c) => ({ c, list: getToolsByCategory(c.id).slice(0, 4) })))

function goCategory(catId: string) {
  router.push(`/tools?cat=${catId}`)
}
</script>

<template>
  <div>
  <!-- Hero -->
  <section class="relative overflow-hidden">
    <div
      class="absolute inset-0 opacity-10"
      style="background: var(--grad-hero); filter: blur(60px)"
    ></div>
    <div class="container-page py-10 md:py-14 relative text-center">
      <span
        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs bg-primary-soft text-primary mb-3"
      >
        <el-icon><CircleCheckFilled /></el-icon> 浏览器本地运行 · 无上传 · 无广告
      </span>
      <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight leading-tight">
        一站式<span class="text-gradient">免费办公工具箱</span>
      </h1>
      <p class="text-text-soft mt-3 max-w-2xl mx-auto leading-relaxed">
        PDF、图片、文本、音视频、开发工具全覆盖，所有处理在浏览器本地完成，
        无需安装、无付费、无隐私泄露，开箱即用。
      </p>
      <div class="flex items-center justify-center gap-3 mt-5">
        <RouterLink to="/tools" class="btn-primary !px-5 !py-2">
          <el-icon><Grid /></el-icon> 进入工具大全
        </RouterLink>
      </div>

      <!-- 数据统计 -->
      <div class="flex items-center justify-center gap-6 sm:gap-8 mt-6 text-center">
        <div>
          <div class="text-xl font-bold text-primary">{{ stats.tools }}+</div>
          <div class="text-xs text-text-mute">在线工具</div>
        </div>
        <div class="w-px h-6 bg-border"></div>
        <div>
          <div class="text-xl font-bold text-primary">{{ stats.categories }}</div>
          <div class="text-xs text-text-mute">工具分类</div>
        </div>
        <div class="w-px h-6 bg-border"></div>
        <div>
          <div class="text-xl font-bold text-primary">{{ stats.cost }}</div>
          <div class="text-xs text-text-mute">永久免费</div>
        </div>
      </div>
    </div>
  </section>

  <!-- 简历制作入口 -->
  <section class="container-page py-6">
    <RouterLink to="/resume" class="resume-home-entry">
      <div>
        <span class="text-xs tracking-widest text-amber-700">NEW · RESUME STUDIO</span>
        <h2 class="text-xl font-bold mt-1">做一份更像你的简历</h2>
        <p class="text-sm text-text-soft mt-1">精选模板、分步填写、实时预览，完成后直接生成 PDF。</p>
      </div>
      <span class="resume-home-arrow"><el-icon><ArrowRight /></el-icon></span>
    </RouterLink>
  </section>

  <!-- AI 生成 PPT 入口 -->
  <section class="container-page pb-6">
    <RouterLink to="/ai-ppt" class="resume-home-entry aippt-home-entry">
      <div>
        <span class="text-xs tracking-widest text-violet-600">AI POWERED · PPT STUDIO</span>
        <h2 class="text-xl font-bold mt-1">AI 帮你把想法变成 PPT</h2>
        <p class="text-sm text-text-soft mt-1">输入主题或文档，AI 生成逐页大纲与内容，在线编辑后一键导出 PPTX。</p>
      </div>
      <span class="resume-home-arrow"><el-icon><ArrowRight /></el-icon></span>
    </RouterLink>
  </section>

  <!-- 面试题库入口 -->
  <section class="container-page pb-6">
    <RouterLink to="/interview" class="resume-home-entry interview-home-entry">
      <div>
        <span class="text-xs tracking-widest text-emerald-600">INTERVIEW BANK</span>
        <h2 class="text-xl font-bold mt-1">整理你的面试题库</h2>
        <p class="text-sm text-text-soft mt-1">分类检索、新增导入、随机出题问答，前后端/数据库/算法/AI 全覆盖。</p>
      </div>
      <span class="resume-home-arrow"><el-icon><ArrowRight /></el-icon></span>
    </RouterLink>
  </section>

  <!-- 分类入口 -->
  <section class="container-page py-6">
    <div class="flex items-end justify-between mb-4">
      <h2 class="text-lg font-bold">工具分类</h2>
      <RouterLink to="/tools" class="text-sm text-primary hover:underline">查看全部 →</RouterLink>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <button
        v-for="c in categories"
        :key="c.id"
        class="card p-3 text-left hover:shadow-md hover:-translate-y-0.5 transition-all"
        @click="goCategory(c.id)"
      >
        <div
          class="w-8 h-8 rounded-md flex items-center justify-center text-white mb-2"
          :style="{ background: `linear-gradient(135deg, ${c.color}, ${c.color}cc)` }"
        >
          <el-icon :size="16"><component :is="c.icon" /></el-icon>
        </div>
        <div class="font-medium text-sm">{{ c.name }}</div>
        <div class="text-xs text-text-mute mt-0.5 line-clamp-2">{{ c.description }}</div>
      </button>
    </div>
  </section>

  <!-- 热门工具 -->
  <section class="container-page py-6">
    <h2 class="text-lg font-bold mb-4">🔥 热门工具</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      <ToolCard v-for="t in hotTools" :key="t.slug" :tool="t" />
    </div>
  </section>

  <!-- 最近使用 -->
  <section v-if="pref.recentTools.length" class="container-page py-6">
    <h2 class="text-lg font-bold mb-4">🕐 最近使用</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <ToolCard v-for="t in pref.recentTools.slice(0, 4)" :key="t.slug" :tool="t" compact />
    </div>
  </section>

  <!-- 分类速览 -->
  <section class="container-page py-6 pb-14">
    <h2 class="text-lg font-bold mb-4">分类速览</h2>
    <div class="grid gap-4 md:grid-cols-2">
      <div v-for="g in onlineTools" :key="g.c.id" class="card p-4">
        <div class="flex items-center gap-2 mb-3">
          <div
            class="w-7 h-7 rounded-md flex items-center justify-center text-white"
            :style="{ background: `linear-gradient(135deg, ${g.c.color}, ${g.c.color}cc)` }"
          >
            <el-icon :size="14"><component :is="g.c.icon" /></el-icon>
          </div>
          <span class="font-semibold text-sm">{{ g.c.name }}</span>
          <button
            class="ml-auto text-xs text-primary hover:underline"
            @click="goCategory(g.c.id)"
          >
            全部 →
          </button>
        </div>
        <div class="grid grid-cols-2 gap-1.5">
          <RouterLink
            v-for="t in g.list"
            :key="t.slug"
            :to="t.status === 'online' ? `/tool/${t.slug}` : `/tools?cat=${t.categoryId}`"
            class="flex items-center gap-1.5 px-2 py-1.5 rounded-md hover:bg-bg-soft text-sm transition-colors"
          >
            <el-icon :size="14" class="text-text-mute"><component :is="t.icon" /></el-icon>
            <span class="truncate">{{ t.name }}</span>
            <span v-if="t.status === 'coming'" class="ml-auto text-[10px] text-text-mute">待</span>
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
  </div>
</template>
