<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { registerSW } from 'virtual:pwa-register'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import AppTabBar from '@/components/layout/AppTabBar.vue'
import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const theme = useThemeStore()

const activeTab = computed(() => (route.meta?.tab as string) || '')
const showTabBar = computed(() => !!activeTab.value)
const fontSizeClass = computed(() => `font-${theme.fontSize}`)

// PWA 更新提示
onMounted(() => {
  registerSW({
    onNeedRefresh() {
      ElMessage({
        message: '检测到新版本，已自动更新～',
        type: 'success',
        duration: 2500
      })
    }
  })
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-bg text-text" :class="fontSizeClass">
    <AppHeader />
    <main class="flex-1 pb-20">
      <RouterView v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>
    <AppTabBar v-if="showTabBar" :model-value="activeTab" />
    <AppFooter v-if="!showTabBar" />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
