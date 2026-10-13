<script setup lang="ts">
import { computed } from 'vue'

export type StepStatus = 'idle' | 'active' | 'done'

export interface ProcessStep {
  label: string
  icon?: string
  status: StepStatus
}

const props = defineProps<{
  steps: ProcessStep[]
}>()

const list = computed(() =>
  props.steps.map((s, i) => ({
    ...s,
    num: i + 1,
    cls:
      s.status === 'done'
        ? 'is-done'
        : s.status === 'active'
          ? 'is-active'
          : ''
  }))
)
</script>

<template>
  <div class="process-steps">
    <div
      v-for="(s, i) in list"
      :key="i"
      class="process-step"
      :class="s.cls"
    >
      <span class="step-num">
        <el-icon v-if="s.status === 'done'" :size="11"><Check /></el-icon>
        <el-icon v-else-if="s.icon" :size="12"><component :is="s.icon" /></el-icon>
        <template v-else>{{ s.num }}</template>
      </span>
      <span class="font-medium">{{ s.label }}</span>
    </div>
  </div>
</template>
