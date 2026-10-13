<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import { useThemeStore } from '@/stores/theme'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: 'json' | 'plaintext'
    placeholder?: string
    readonly?: boolean
    minimap?: boolean
  }>(),
  { language: 'json', placeholder: '', readonly: false, minimap: true }
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'ready', editor: monaco.editor.IStandaloneCodeEditor): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const editorRef = shallowRef<monaco.editor.IStandaloneCodeEditor | null>(null)
const theme = useThemeStore()

// worker 注册（浏览器端执行，SSR 安全地跳过——这里始终浏览器）
if (typeof window !== 'undefined') {
  ;(window as unknown as { MonacoEnvironment: unknown }).MonacoEnvironment = {
    getWorker(_: string, label: string) {
      if (label === 'json') return new jsonWorker()
      return new editorWorker()
    }
  }
}

const themeId = computed(() => (theme.isDark ? 'suyong-dark' : 'suyong-light'))

function defineThemes() {
  const primary = getComputedStyle(document.documentElement).getPropertyValue('--c-primary').trim() || '#4f6eff'
  monaco.editor.defineTheme('suyong-light', {
    base: 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.lineHighlightBackground': '#eef2ff33',
      'editorGutter.background': '#ffffff00',
      'editor.lineHighlightBorder': primary + '33'
    }
  })
  monaco.editor.defineTheme('suyong-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#121b2d',
      'editor.lineHighlightBackground': '#ffffff0a',
      'editorGutter.background': '#0b1220',
      'editor.lineHighlightBorder': primary + '33'
    }
  })
}

function syncValueFromProps(next: string) {
  const ed = editorRef.value
  if (!ed) return
  if (ed.getValue() !== next) ed.setValue(next ?? '')
}

watch(
  () => props.modelValue,
  (v) => syncValueFromProps(v)
)

watch(
  () => theme.mode,
  () => {
    defineThemes()
    monaco.editor.setTheme(themeId.value)
  }
)

let ro: ResizeObserver | null = null
onMounted(() => {
  if (!containerRef.value) return
  defineThemes()
  const ed = monaco.editor.create(containerRef.value, {
    value: props.modelValue ?? '',
    language: props.language,
    theme: themeId.value,
    readOnly: props.readonly,
    automaticLayout: false,
    fontSize: 13,
    fontFamily: 'var(--font-mono)',
    lineHeight: 20,
    minimap: { enabled: props.minimap },
    scrollBeyondLastLine: false,
    folding: true,
    lineNumbers: 'on',
    renderLineHighlight: 'line',
    wordWrap: 'on',
    wrappingStrategy: 'advanced',
    smoothScrolling: true,
    cursorSmoothCaretAnimation: 'on',
    find: {
      addExtraSpaceOnTop: false,
      autoFindInSelection: 'always',
      seedSearchStringFromSelection: 'always'
    },
    placeholder: props.placeholder,
    tabSize: 2,
    insertSpaces: true
  })
  ed.onDidChangeModelContent(() => {
    const v = ed.getValue()
    emit('update:modelValue', v)
  })
  editorRef.value = ed
  emit('ready', ed)
  ro = new ResizeObserver(() => ed.layout())
  ro.observe(containerRef.value)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  editorRef.value?.dispose()
  editorRef.value = null
})
</script>

<template>
  <div
    ref="containerRef"
    class="w-full h-full min-h-[280px] rounded-lg overflow-hidden border border-border"
    style="background-color: var(--c-card)"
  />
</template>
