<script setup lang="ts">
/**
 * 自动增高文本域：内容多时始终完整展开（不隐藏、不出现内滚动），
 * 超过 maxHeight 后才内部滚动，防止页面被无限撑爆
 */
import { nextTick, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
    minHeight?: number
    maxHeight?: number
  }>(),
  { placeholder: '', minHeight: 84, maxHeight: 340 }
)

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const el = ref<HTMLTextAreaElement | null>(null)

function resize() {
  const t = el.value
  if (!t) return
  t.style.height = 'auto'
  const h = Math.min(Math.max(t.scrollHeight, props.minHeight), props.maxHeight)
  t.style.height = `${h}px`
}

watch(
  () => props.modelValue,
  () => nextTick(resize)
)

onMounted(resize)

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
  nextTick(resize)
}
</script>

<template>
  <textarea
    ref="el"
    class="auto-textarea"
    :value="modelValue"
    :placeholder="placeholder"
    :style="{ minHeight: `${minHeight}px`, maxHeight: `${maxHeight}px` }"
    @input="onInput"
  />
</template>

<style scoped>
.auto-textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--c-border);
  background: var(--c-bg-soft);
  color: var(--c-text);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.65;
  outline: none;
  resize: none;
  overflow-y: auto;
  font-family: inherit;
}
.auto-textarea:focus {
  border-color: var(--c-primary);
}
</style>
