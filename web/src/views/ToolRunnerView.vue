<script setup lang="ts">
import { resolveToolComponent } from '@/config/tool-registry'
import { getToolBySlug } from '@/config/tools'
import { usePreferenceStore } from '@/stores/preference'
import { useRoute, useRouter } from 'vue-router'
import { computed, watch } from 'vue'
import ToolHeader from '@/components/tools/ToolHeader.vue'

const route = useRoute()
const router = useRouter()
const pref = usePreferenceStore()

const slug = computed(() => route.params.slug as string)
const tool = computed(() => getToolBySlug(slug.value))
const component = computed(() => resolveToolComponent(slug.value))

watch(
  () => slug.value,
  (s) => {
    if (s && tool.value?.status === 'online') pref.pushRecent(s)
  },
  { immediate: true }
)

watch(
  () => tool.value,
  (t) => {
    if (route.name === 'tool' && !t) router.replace('/404')
  }
)
</script>

<template>
  <div class="container-page py-8">
    <ToolHeader v-if="tool" :slug="slug" />

    <div v-if="tool">
      <component :is="component" v-if="component" />
      <div v-else class="card p-12 text-center">
        <el-icon :size="48" class="text-text-mute mb-3"><MagicStick /></el-icon>
        <h3 class="text-lg font-semibold mb-1">「{{ tool.name }}」即将上线</h3>
        <p class="text-text-soft">该工具正在开发中，敬请期待。</p>
        <div class="flex items-center justify-center gap-3 mt-6">
          <RouterLink to="/tools" class="btn-primary">查看其他工具</RouterLink>
          <RouterLink to="/" class="btn-ghost !border !border-border">返回首页</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
