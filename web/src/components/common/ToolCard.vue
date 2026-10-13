<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { categories, type ToolMeta } from '@/config/tools'
import { usePreferenceStore } from '@/stores/preference'

const props = defineProps<{ tool: ToolMeta; compact?: boolean }>()
const router = useRouter()
const pref = usePreferenceStore()

const cat = computed(() => categories.find((c) => c.id === props.tool.categoryId))
const isFav = computed(() => pref.isFavorite(props.tool.slug))

function open() {
  if (props.tool.status === 'coming') return
  router.push(`/tool/${props.tool.slug}`)
}

function toggleFav(e: Event) {
  e.preventDefault()
  e.stopPropagation()
  pref.toggleFavorite(props.tool.slug)
}
</script>

<template>
  <div
    class="tool-card group relative"
    :class="{ 'opacity-70 cursor-not-allowed': tool.status === 'coming' }"
    @click="open"
  >
    <div class="flex items-start gap-3">
      <div
        class="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-white"
        :style="{ background: `linear-gradient(135deg, ${cat?.color}, ${cat?.color}cc)` }"
      >
        <el-icon :size="20"><component :is="tool.icon" /></el-icon>
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <h3 class="font-medium truncate">{{ tool.name }}</h3>
          <span v-if="tool.status === 'coming'" class="tag">即将上线</span>
          <span v-else class="tag text-primary" style="background: var(--c-primary-soft)">可用</span>
        </div>
        <p class="text-sm text-text-soft mt-0.5 line-clamp-2">{{ tool.description }}</p>
      </div>
    </div>

    <div v-if="!compact" class="flex items-center justify-between mt-3 pt-3 border-t border-border-soft">
      <span class="text-xs text-text-mute">{{ cat?.name }}</span>
      <div class="flex items-center gap-1">
        <button
          v-if="tool.status === 'online'"
          class="btn-ghost !px-1.5"
          :class="{ 'text-primary': isFav }"
          title="收藏"
          @click="toggleFav"
        >
          <el-icon :size="16">
            <component :is="isFav ? 'StarFilled' : 'Star'" />
          </el-icon>
        </button>
        <span class="text-xs text-text-mute group-hover:text-primary transition-colors">
          打开 →
        </span>
      </div>
    </div>
  </div>
</template>
