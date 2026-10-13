<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  modelValue: string
}>()

const items = [
  { to: '/', tab: 'home', label: '首页', icon: 'House' },
  { to: '/tools', tab: 'tools', label: '工具', icon: 'Grid' },
  { to: '/favorites', tab: 'favorites', label: '收藏', icon: 'StarFilled' },
  { to: '/me', tab: 'me', label: '我的', icon: 'User' }
]
</script>

<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-40 border-t md:hidden"
    style="
      border-color: var(--c-border);
      background-color: color-mix(in srgb, var(--c-card) 92%, transparent);
      backdrop-filter: blur(8px);
    "
  >
    <div class="grid grid-cols-4 h-16 max-w-xl mx-auto">
      <RouterLink
        v-for="it in items"
        :key="it.tab"
        :to="it.to"
        class="flex flex-col items-center justify-center gap-1 text-[11px]"
        :class="modelValue === it.tab ? 'text-primary' : 'text-text-mute'"
      >
        <el-icon :size="22"><component :is="it.icon" /></el-icon>
        <span>{{ it.label }}</span>
      </RouterLink>
    </div>
  </nav>
</template>
