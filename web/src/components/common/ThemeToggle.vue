<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
</script>

<template>
  <button
    class="btn-ghost"
    :title="theme.isDark ? '切换到浅色' : '切换到深色'"
    @click="theme.toggleMode()"
  >
    <el-icon :size="18">
      <component :is="theme.isDark ? 'Sunny' : 'Moon'" />
    </el-icon>
  </button>
</template>
