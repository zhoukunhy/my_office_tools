<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '@/utils/file'
import ToolHeader from '@/components/tools/ToolHeader.vue'

const JsonEditor = defineAsyncComponent(
  () => import('@/components/common/JsonEditor.vue')
)

const input = ref('{\n  "name": "速用工具箱",\n  "tools": ["pdf", "image", "dev"],\n  "free": true\n}')
const indent = ref(2)
const error = ref('')
const editorReady = ref(false)

const stats = computed(() => input.value.length)

function setError(msg: string) {
  error.value = msg
}

function parse(): unknown | null {
  setError('')
  if (!input.value.trim()) {
    setError('输入为空')
    return null
  }
  try {
    return JSON.parse(input.value)
  } catch (e) {
    setError((e as Error).message)
    return null
  }
}

function format() {
  const data = parse()
  if (data === null) {
    ElMessage.error('JSON 格式错误，无法格式化')
    return
  }
  input.value = JSON.stringify(data, null, indent.value === 0 ? '\t' : indent.value)
  ElMessage.success('格式化成功')
}

function minify() {
  const data = parse()
  if (data === null) {
    ElMessage.error('JSON 格式错误，无法压缩')
    return
  }
  input.value = JSON.stringify(data)
  ElMessage.success('压缩成功')
}

function validate() {
  const data = parse()
  if (data !== null) ElMessage.success('JSON 格式正确')
  else ElMessage.error('JSON 格式错误')
}

async function copy() {
  await navigator.clipboard.writeText(input.value)
  ElMessage.success('已复制')
}

function clear() {
  input.value = ''
  setError('')
}

function download() {
  const data = parse()
  if (data === null) {
    ElMessage.error('JSON 格式错误，无法下载')
    return
  }
  const text = JSON.stringify(data, null, indent.value === 0 ? '\t' : indent.value)
  downloadBlob(new Blob([text], { type: 'application/json' }), 'data.json')
}
</script>

<template>
  <ToolHeader
    title="JSON 格式化 & 压缩"
    description="支持折叠、行号、查找替换（Ctrl+F / Ctrl+H）、格式化、压缩、校验、下载。"
  />

  <section class="container-page max-w-6xl py-6">
    <div class="card p-4 mb-4 flex flex-wrap items-center gap-3">
      <div>
        <label class="text-sm text-text-soft block mb-1">缩进</label>
        <el-radio-group v-model="indent">
          <el-radio-button :value="2">2 空格</el-radio-button>
          <el-radio-button :value="4">4 空格</el-radio-button>
          <el-radio-button :value="0">Tab</el-radio-button>
        </el-radio-group>
      </div>
      <div class="flex flex-wrap gap-2 ml-auto">
        <button class="btn-primary" @click="format">
          <el-icon :size="16"><MagicStick /></el-icon>格式化
        </button>
        <button class="btn-ghost border border-border" @click="minify">
          <el-icon :size="16"><Compress /></el-icon>压缩
        </button>
        <button class="btn-ghost border border-border" @click="validate">
          <el-icon :size="16"><CircleCheck /></el-icon>校验
        </button>
        <button class="btn-ghost border border-border" @click="copy">
          <el-icon :size="16"><CopyDocument /></el-icon>复制
        </button>
        <button class="btn-ghost border border-border" @click="download">
          <el-icon :size="16"><Download /></el-icon>下载
        </button>
        <button class="btn-ghost border border-border btn-ghost-danger" @click="clear">
          <el-icon :size="16"><Delete /></el-icon>清空
        </button>
      </div>
    </div>

    <div class="card p-2">
      <JsonEditor
        v-model="input"
        language="json"
        placeholder="在此粘贴 JSON 文本，支持 Ctrl+F 查找 / Ctrl+H 替换"
        class="block"
        style="height: 60vh; min-height: 380px"
        @ready="editorReady = true"
      />
    </div>

    <div class="flex flex-wrap items-center justify-between mt-3 text-sm gap-2">
      <span class="text-text-mute">
        {{ stats }} 字符
        <span class="mx-2">·</span>
        {{ input.trim() ? (input || '').split(/\r?\n/).length : 0 }} 行
      </span>
      <span v-if="error" class="text-danger flex items-center gap-1">
        <el-icon :size="14"><CircleCloseFilled /></el-icon> {{ error }}
      </span>
      <span v-else-if="input.trim()" class="text-success flex items-center gap-1">
        <el-icon :size="14"><CircleCheckFilled /></el-icon>
        格式正确 · 支持折叠、行号、查找替换
        <span v-if="!editorReady" class="text-text-mute">（编辑器加载中…）</span>
      </span>
    </div>
  </section>
</template>
