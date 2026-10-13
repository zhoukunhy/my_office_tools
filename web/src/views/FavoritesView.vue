<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { usePreferenceStore } from '@/stores/preference'
import ToolCard from '@/components/common/ToolCard.vue'

const pref = usePreferenceStore()
</script>

<template>
  <div>
  <section class="container-page py-6">
    <div class="flex items-end justify-between mb-4">
      <h2 class="text-lg font-bold">我的收藏</h2>
      <RouterLink to="/tools" class="text-sm text-primary hover:underline">去工具大全 →</RouterLink>
    </div>

    <div v-if="!pref.favoriteTools.length" class="empty-block">
      <el-icon :size="34" class="mb-2 text-text-mute"><Star /></el-icon>
      <div>还没有收藏任何工具</div>
      <p class="text-xs mt-1 text-text-mute">在工具页或工具详情点击 ★ 即可加入收藏</p>
      <RouterLink to="/tools" class="btn-primary mt-4">去收藏一个</RouterLink>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <ToolCard v-for="t in pref.favoriteTools" :key="t.slug" :tool="t" compact />
    </div>

    <div v-if="pref.recentTools.length" class="mt-10">
      <h3 class="text-base font-semibold mb-4">最近使用</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <ToolCard v-for="t in pref.recentTools.slice(0, 8)" :key="t.slug" :tool="t" compact />
      </div>
    </div>
  </section>
  </div>
</template>
