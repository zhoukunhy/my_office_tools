<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { downloadBlob } from '@/utils/file'

const input = ref('')

const ops = reactive<Record<string, boolean>>({
  trim: false,
  extraSpaces: false,
  removeEmpty: false,
  dedupe: false,
  removeBreaks: false,
  findReplace: false,
  upper: false,
  lower: false,
  titleCase: false,
  sentenceCase: false
})

const findText = ref('')
const replaceText = ref('')

const toggleOps: { key: string; label: string }[] = [
  { key: 'trim', label: '去除首尾空格' },
  { key: 'extraSpaces', label: '去多余空格' },
  { key: 'removeEmpty', label: '去空行' },
  { key: 'dedupe', label: '去重' },
  { key: 'removeBreaks', label: '去换行' },
  { key: 'upper', label: '全大写' },
  { key: 'lower', label: '全小写' },
  { key: 'titleCase', label: '首字母大写' },
  { key: 'sentenceCase', label: '句首大写' },
  { key: 'findReplace', label: '查找替换' }
]

function titleCaseLine(line: string): string {
  return line.replace(/[A-Za-z]+/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
}

function sentenceCaseLine(line: string): string {
  const lower = line.toLowerCase()
  return lower.replace(/(^\s*|[.!?。！？]\s+)([a-z])/g, (_m, p: string, c: string) => p + c.toUpperCase())
}

const result = computed(() => {
  const text = input.value
  if (!text) return ''
  let lines = text.split(/\r?\n/)

  if (ops.trim) lines = lines.map((l) => l.trim())
  if (ops.extraSpaces) lines = lines.map((l) => l.replace(/[ \t]+/g, ' ').trim())
  if (ops.findReplace && findText.value !== '') {
    const f = findText.value
    const r = replaceText.value
    lines = lines.map((l) => l.split(f).join(r))
  }
  if (ops.upper) lines = lines.map((l) => l.toUpperCase())
  if (ops.lower) lines = lines.map((l) => l.toLowerCase())
  if (ops.titleCase) lines = lines.map((l) => titleCaseLine(l))
  if (ops.sentenceCase) lines = lines.map((l) => sentenceCaseLine(l))
  if (ops.removeEmpty) lines = lines.filter((l) => l.trim() !== '')
  if (ops.dedupe) {
    const seen = new Set<string>()
    lines = lines.filter((l) => {
      if (seen.has(l)) return false
      seen.add(l)
      return true
    })
  }
  if (ops.removeBreaks) return lines.join('')
  return lines.join('\n')
})

function countWords(text: string): number {
  const t = text.trim()
  if (!t) return 0
  let n = 0
  const words = t.match(/[A-Za-z0-9]+/g)
  if (words) n += words.length
  const cjk = t.match(/[\u4e00-\u9fff]/g)
  if (cjk) n += cjk.length
  return n
}

const inputLines = computed(() => (input.value ? input.value.split(/\r?\n/).length : 0))
const inputChars = computed(() => input.value.length)
const inputWords = computed(() => countWords(input.value))
const resultLines = computed(() => (result.value ? result.value.split(/\r?\n/).length : 0))
const resultChars = computed(() => result.value.length)

async function onFiles(files: File[]) {
  const texts: string[] = []
  for (const f of files) {
    texts.push(await f.text())
  }
  const joined = texts.join('\n')
  input.value = input.value ? `${input.value}\n${joined}` : joined
  ElMessage.success(`已导入 ${files.length} 个文件`)
}

async function copyResult() {
  if (!result.value) {
    ElMessage.warning('没有可复制的内容')
    return
  }
  await navigator.clipboard.writeText(result.value)
  ElMessage.success('已复制到剪贴板')
}

function downloadResult() {
  if (!result.value) {
    ElMessage.warning('没有可下载的内容')
    return
  }
  downloadBlob(
    new Blob([result.value], { type: 'text/plain;charset=utf-8' }),
    '文本批量处理结果.txt'
  )
}

function clearAll() {
  input.value = ''
  findText.value = ''
  replaceText.value = ''
  for (const k of Object.keys(ops)) ops[k] = false
}
</script>

<template>
  <ToolHeader
    title="文本批量处理"
    description="支持去空行、去重、去换行、大小写转换、查找替换等批量文本处理，可导入 .txt/.csv 文件。"
  />

  <section class="container-page max-w-6xl py-6">
    <!-- 输入 -->
    <div class="card p-4 mb-4">
      <FileDropZone
        accept=".txt,.csv"
        :multiple="true"
        hint="支持 .txt / .csv 文本文件，可批量追加到输入框"
        chunk-label="① 导入文件（可选）"
        @files="onFiles"
      />
      <div class="text-sm font-semibold mb-2 mt-2">② 输入文本</div>
      <el-input
        v-model="input"
        type="textarea"
        :autosize="{ minRows: 10, maxRows: 25 }"
        placeholder="在此粘贴或输入文本，或使用上方导入文件"
      />
      <div class="text-xs text-text-mute mt-2">
        {{ inputLines }} 行 · {{ inputWords }} 词 · {{ inputChars }} 字符
      </div>
    </div>

    <!-- 操作 -->
    <div class="card p-4 mb-4">
      <div class="text-sm font-semibold mb-3">③ 选择处理操作</div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="op in toggleOps"
          :key="op.key"
          class="text-sm"
          :class="ops[op.key] ? 'btn-primary' : 'btn-ghost border border-border'"
          @click="ops[op.key] = !ops[op.key]"
        >
          {{ op.label }}
        </button>
      </div>
      <div v-if="ops.findReplace" class="flex flex-col sm:flex-row gap-2 mt-3">
        <el-input v-model="findText" placeholder="查找内容" class="flex-1" />
        <el-input v-model="replaceText" placeholder="替换为" class="flex-1" />
      </div>
      <p class="text-xs text-text-mute mt-3 leading-relaxed">
        操作按顺序执行：去除首尾空格 → 去多余空格 → 查找替换 → 大小写转换 → 去空行 → 去重 → 去换行。
      </p>
    </div>

    <!-- 结果 -->
    <div class="card p-4 mb-4">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-semibold">④ 处理结果</div>
        <span class="text-xs text-text-mute">{{ resultLines }} 行 · {{ resultChars }} 字符</span>
      </div>
      <el-input
        :model-value="result"
        type="textarea"
        :autosize="{ minRows: 10, maxRows: 25 }"
        readonly
        placeholder="处理结果将在此显示（只读）"
      />
    </div>

    <!-- 操作按钮 -->
    <div class="flex flex-wrap items-center gap-2 justify-end">
      <button class="btn-primary" @click="copyResult">
        <el-icon :size="16"><CopyDocument /></el-icon>复制结果
      </button>
      <button class="btn-ghost border border-border" @click="downloadResult">
        <el-icon :size="16"><Download /></el-icon>下载 .txt
      </button>
      <button class="btn-ghost border border-border btn-ghost-danger" @click="clearAll">
        <el-icon :size="16"><Delete /></el-icon>清空
      </button>
    </div>
  </section>
</template>
