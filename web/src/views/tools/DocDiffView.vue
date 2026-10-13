<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { usePreferenceStore } from '@/stores/preference'
import { backendFetch, type BackendStatus } from '@/utils/api'
import { downloadBlob } from '@/utils/file'

const pref = usePreferenceStore()
const backend = computed<BackendStatus>(() => ({
  enabled: pref.backendEnabled,
  base: pref.backendBaseUrl?.trim() || ''
}))

// 当前 Tab: 'text' | 'file'
const activeTab = ref<'text' | 'file'>('text')

// diff 粒度: 'word' | 'char'
const diffLevel = ref<'word' | 'char'>('word')

// ===== Tab 1: 文本对比 =====
const leftText = ref('')
const rightText = ref('')

// ===== Tab 2: 文件上传对比 =====
const leftFile = ref<File | null>(null)
const rightFile = ref<File | null>(null)
const leftFileText = ref('')
const rightFileText = ref('')
const extractingLeft = ref(false)
const extractingRight = ref(false)

// ===== 结果 =====
const diffHtml = ref('')
const stats = ref({
  leftChars: 0,
  rightChars: 0,
  additions: 0,
  deletions: 0
})
const compared = ref(false)

// ===== LCS 算法 =====
type DiffOp = { type: 'equal' | 'add' | 'del'; value: string }

/** 词级分词：中英文混合处理 */
function tokenizeWords(text: string): string[] {
  // 将文本拆分为：连续中文单字、英文单词、数字、标点、空白
  // 使用正向匹配：\u4e00-\u9fff 中文字符单字为单位
  const tokens: string[] = []
  const regex = /[\u4e00-\u9fff]|[A-Za-z0-9]+|\s+|[^\u4e00-\u9fffA-Za-z0-9\s]/g
  let m
  while ((m = regex.exec(text)) !== null) {
    tokens.push(m[0])
  }
  return tokens
}

/** 字符级分词：按单个字符切分 */
function tokenizeChars(text: string): string[] {
  return Array.from(text)
}

/** 计算 LCS 回溯 diff 结果 */
function computeLCSDiff(a: string, b: string, level: 'word' | 'char'): DiffOp[] {
  const tokensA = level === 'word' ? tokenizeWords(a) : tokenizeChars(a)
  const tokensB = level === 'word' ? tokenizeWords(b) : tokenizeChars(b)

  const m = tokensA.length
  const n = tokensB.length

  // 构建 LCS DP 表（使用 Uint32Array 优化内存）
  const dp: Uint32Array[] = []
  for (let i = 0; i <= m; i++) {
    dp.push(new Uint32Array(n + 1))
  }

  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (tokensA[i] === tokensB[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1])
      }
    }
  }

  // 回溯生成 diff
  const ops: DiffOp[] = []
  let i = 0
  let j = 0
  while (i < m && j < n) {
    if (tokensA[i] === tokensB[j]) {
      ops.push({ type: 'equal', value: tokensA[i] })
      i++
      j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ type: 'del', value: tokensA[i] })
      i++
    } else {
      ops.push({ type: 'add', value: tokensB[j] })
      j++
    }
  }
  while (i < m) {
    ops.push({ type: 'del', value: tokensA[i] })
    i++
  }
  while (j < n) {
    ops.push({ type: 'add', value: tokensB[j] })
    j++
  }

  return mergeSameOps(ops)
}

/** 合并相邻同类操作，减少 span 数量 */
function mergeSameOps(ops: DiffOp[]): DiffOp[] {
  if (ops.length === 0) return ops
  const result: DiffOp[] = []
  let current = { ...ops[0] }
  for (let k = 1; k < ops.length; k++) {
    const op = ops[k]
    if (op.type === current.type) {
      current.value += op.value
    } else {
      result.push(current)
      current = { ...op }
    }
  }
  result.push(current)
  return result
}

/** 生成 diff HTML */
function opsToHtml(ops: DiffOp[]): { html: string; additions: number; deletions: number } {
  let html = ''
  let additions = 0
  let deletions = 0
  for (const op of ops) {
    const text = escapeHtml(op.value)
    if (op.type === 'add') {
      additions += op.value.length
      html += `<span style="color:#10b981;background:#ecfdf5;">${text}</span>`
    } else if (op.type === 'del') {
      deletions += op.value.length
      html += `<span style="color:#ef4444;background:#fef2f2;text-decoration:line-through;">${text}</span>`
    } else {
      html += text
    }
  }
  return { html, additions, deletions }
}

/** HTML 转义 */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/\n/g, '<br/>')
}

/** 执行对比（文本模式） */
function runTextCompare() {
  if (!leftText.value && !rightText.value) {
    ElMessage.warning('请至少输入左侧或右侧文本')
    return
  }
  doCompare(leftText.value, rightText.value)
}

/** 执行对比（文件模式） */
function runFileCompare() {
  if (!leftFileText.value && !rightFileText.value) {
    ElMessage.warning('请先上传并提取左右两侧文件')
    return
  }
  doCompare(leftFileText.value, rightFileText.value)
}

/** 核心对比函数 */
function doCompare(a: string, b: string) {
  const ops = computeLCSDiff(a, b, diffLevel.value)
  const { html, additions, deletions } = opsToHtml(ops)
  diffHtml.value = html
  stats.value = {
    leftChars: a.length,
    rightChars: b.length,
    additions,
    deletions
  }
  compared.value = true
}

// ===== 文件提取（Tab2） =====
const ACCEPT_EXTS = ['txt', 'docx', 'doc', 'pdf']

function isValidExt(name: string): boolean {
  const idx = name.lastIndexOf('.')
  const ext = idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
  return ACCEPT_EXTS.includes(ext)
}

function getExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
}

async function extractTextFromFile(file: File): Promise<string> {
  const ext = getExt(file.name)
  if (ext === 'txt') {
    return await file.text()
  }
  // docx / doc / pdf 走后端
  if (!backend.value.enabled) {
    throw new Error('需要开启后端加速才能提取文档文本')
  }
  const fd = new FormData()
  fd.append('file', file)
  const r = await backendFetch('/doc/extract-text', fd, { timeoutMs: 300_000 })
  if (!r.ok) throw new Error(r.message)
  // 返回的是 text/plain blob
  return await r.blob.text()
}

async function handleLeftFiles(files: File[]) {
  if (!files.length) return
  const f = files[0]
  if (!isValidExt(f.name)) {
    ElMessage.error('仅支持 .txt / .docx / .doc / .pdf 文件')
    return
  }
  leftFile.value = f
  extractingLeft.value = true
  compared.value = false
  try {
    leftFileText.value = await extractTextFromFile(f)
    ElMessage.success(`左侧文件提取成功（${leftFileText.value.length} 字符）`)
  } catch (err) {
    leftFileText.value = ''
    ElMessage.error(err instanceof Error ? err.message : '文本提取失败')
  } finally {
    extractingLeft.value = false
  }
}

async function handleRightFiles(files: File[]) {
  if (!files.length) return
  const f = files[0]
  if (!isValidExt(f.name)) {
    ElMessage.error('仅支持 .txt / .docx / .doc / .pdf 文件')
    return
  }
  rightFile.value = f
  extractingRight.value = true
  compared.value = false
  try {
    rightFileText.value = await extractTextFromFile(f)
    ElMessage.success(`右侧文件提取成功（${rightFileText.value.length} 字符）`)
  } catch (err) {
    rightFileText.value = ''
    ElMessage.error(err instanceof Error ? err.message : '文本提取失败')
  } finally {
    extractingRight.value = false
  }
}

// ===== 其他辅助 =====
function clearText() {
  leftText.value = ''
  rightText.value = ''
  diffHtml.value = ''
  stats.value = { leftChars: 0, rightChars: 0, additions: 0, deletions: 0 }
  compared.value = false
}

function clearFiles() {
  leftFile.value = null
  rightFile.value = null
  leftFileText.value = ''
  rightFileText.value = ''
  diffHtml.value = ''
  stats.value = { leftChars: 0, rightChars: 0, additions: 0, deletions: 0 }
  compared.value = false
}

function downloadDiffHtml() {
  if (!diffHtml.value) {
    ElMessage.warning('暂无对比结果')
    return
  }
  const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>文档对比结果</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:24px;line-height:1.8;white-space:pre-wrap;word-break:break-word;}</style>
</head><body>${diffHtml.value.replace(/<br\/>/g, '\n')}</body></html>`
  downloadBlob(new Blob([fullHtml], { type: 'text/html;charset=utf-8' }), '文档对比结果.html')
}

</script>

<template>
  <ToolHeader title="文档对比" description="Word / 文本差异对比">
    <template #statusTop>
      <span
        v-if="activeTab === 'file'"
        class="text-xs"
        :class="backend.enabled ? 'text-success' : 'text-warning'"
      >
        {{ backend.enabled ? '✓ 后端加速已开启（支持 docx/doc/pdf）' : '⚡ 未开启后端，仅 .txt 可直接读取' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-6xl py-6">
    <!-- Tab 切换 -->
    <div class="card p-4 mb-4">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div class="inline-flex rounded-lg p-1 bg-bg-muted">
          <button
            class="px-4 py-1.5 rounded-md text-sm font-medium transition"
            :class="activeTab === 'text' ? 'bg-white shadow text-primary' : 'text-text-soft hover:text-primary'"
            @click="activeTab = 'text'"
          >
            文本对比
          </button>
          <button
            class="px-4 py-1.5 rounded-md text-sm font-medium transition"
            :class="activeTab === 'file' ? 'bg-white shadow text-primary' : 'text-text-soft hover:text-primary'"
            @click="activeTab = 'file'"
          >
            文件上传对比
          </button>
        </div>

        <!-- 粒度切换 -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-text-mute">对比粒度：</span>
          <div class="inline-flex rounded-md border border-border overflow-hidden text-xs">
            <button
              class="px-3 py-1"
              :class="diffLevel === 'word' ? 'bg-primary text-white' : 'hover:bg-bg-muted text-text-soft'"
              @click="diffLevel = 'word'"
            >
              Word 级别
            </button>
            <button
              class="px-3 py-1"
              :class="diffLevel === 'char' ? 'bg-primary text-white' : 'hover:bg-bg-muted text-text-soft'"
              @click="diffLevel = 'char'"
            >
              字符级别
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== Tab 1: 文本对比 ===== -->
    <div v-if="activeTab === 'text'">
      <div class="card p-4 mb-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div class="flex items-center justify-between mb-2">
              <div class="text-sm font-semibold">左侧（原文本）</div>
              <span class="text-xs text-text-mute">{{ leftText.length }} 字符</span>
            </div>
            <el-input
              v-model="leftText"
              type="textarea"
              :autosize="{ minRows: 12, maxRows: 20 }"
              placeholder="在此粘贴原始文本..."
              class="font-mono text-sm"
            />
          </div>
          <div>
            <div class="flex items-center justify-between mb-2">
              <div class="text-sm font-semibold">右侧（修改后文本）</div>
              <span class="text-xs text-text-mute">{{ rightText.length }} 字符</span>
            </div>
            <el-input
              v-model="rightText"
              type="textarea"
              :autosize="{ minRows: 12, maxRows: 20 }"
              placeholder="在此粘贴修改后的文本..."
              class="font-mono text-sm"
            />
          </div>
        </div>

        <div class="flex items-center gap-2 mt-4 justify-end">
          <button class="btn-ghost border border-border btn-ghost-danger" @click="clearText">
            <el-icon :size="16"><Delete /></el-icon>清空
          </button>
          <button class="btn-primary" @click="runTextCompare">
            <el-icon :size="16"><Compare /></el-icon>对比
          </button>
        </div>
      </div>
    </div>

    <!-- ===== Tab 2: 文件上传对比 ===== -->
    <div v-else>
      <div class="card p-4 mb-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- 左侧 -->
          <div>
            <FileDropZone
              accept=".txt,.docx,.doc,.pdf"
              :multiple="false"
              hint="支持 .txt / .docx / .doc / .pdf"
              chunk-label="左侧（原文件）"
              title="拖拽 / 选择左侧文件"
              @files="handleLeftFiles"
            />
            <div v-if="extractingLeft" class="flex items-center gap-2 text-xs text-primary mb-2">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在提取文本...
            </div>
            <div v-else-if="leftFile" class="text-xs text-text-mute mb-2 flex items-center gap-1">
              <el-icon :size="14"><Check /></el-icon>
              已提取：{{ leftFile.name }}（{{ leftFileText.length }} 字符）
            </div>
            <div v-if="leftFileText" class="mt-2">
              <el-input
                :model-value="leftFileText"
                type="textarea"
                :rows="6"
                readonly
                placeholder="左侧提取的文本将在此预览"
                class="font-mono text-xs bg-bg-muted"
              />
            </div>
          </div>

          <!-- 右侧 -->
          <div>
            <FileDropZone
              accept=".txt,.docx,.doc,.pdf"
              :multiple="false"
              hint="支持 .txt / .docx / .doc / .pdf"
              chunk-label="右侧（修改后文件）"
              title="拖拽 / 选择右侧文件"
              @files="handleRightFiles"
            />
            <div v-if="extractingRight" class="flex items-center gap-2 text-xs text-primary mb-2">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在提取文本...
            </div>
            <div v-else-if="rightFile" class="text-xs text-text-mute mb-2 flex items-center gap-1">
              <el-icon :size="14"><Check /></el-icon>
              已提取：{{ rightFile.name }}（{{ rightFileText.length }} 字符）
            </div>
            <div v-if="rightFileText" class="mt-2">
              <el-input
                :model-value="rightFileText"
                type="textarea"
                :rows="6"
                readonly
                placeholder="右侧提取的文本将在此预览"
                class="font-mono text-xs bg-bg-muted"
              />
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2 mt-4 justify-end">
          <button class="btn-ghost border border-border btn-ghost-danger" @click="clearFiles">
            <el-icon :size="16"><Delete /></el-icon>清空
          </button>
          <button
            class="btn-primary"
            :disabled="extractingLeft || extractingRight"
            @click="runFileCompare"
          >
            <el-icon :size="16"><Compare /></el-icon>
            {{ extractingLeft || extractingRight ? '文本提取中...' : '对比' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ===== 对比结果 ===== -->
    <div v-if="compared" class="card p-4 mb-4">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div class="text-sm font-semibold">对比结果</div>
        <div class="flex items-center gap-2 flex-wrap">
          <!-- 统计 -->
          <div class="flex items-center gap-3 text-xs">
            <span class="text-text-mute">
              左侧 <span class="text-text-soft font-medium">{{ stats.leftChars }}</span>
            </span>
            <span class="text-text-mute">
              右侧 <span class="text-text-soft font-medium">{{ stats.rightChars }}</span>
            </span>
            <span class="text-text-mute">
              新增 <span class="font-medium" style="color:#10b981;">+{{ stats.additions }}</span>
            </span>
            <span class="text-text-mute">
              删除 <span class="font-medium" style="color:#ef4444;">-{{ stats.deletions }}</span>
            </span>
          </div>
          <div class="h-4 w-px bg-border" />
          <!-- 图例 -->
          <div class="flex items-center gap-3 text-xs">
            <span class="inline-flex items-center gap-1">
              <span
                class="inline-block w-3 h-3 rounded"
                style="background:#ecfdf5;border:1px solid #10b98133;"
              ></span>
              <span class="text-text-mute">新增</span>
            </span>
            <span class="inline-flex items-center gap-1">
              <span
                class="inline-block w-3 h-3 rounded"
                style="background:#fef2f2;border:1px solid #ef444433;"
              ></span>
              <span class="text-text-mute">删除</span>
            </span>
          </div>
          <div class="h-4 w-px bg-border" />
          <button class="btn-ghost border border-border text-xs" @click="downloadDiffHtml">
            <el-icon :size="14"><Download /></el-icon>导出 HTML
          </button>
        </div>
      </div>

      <!-- Diff HTML 容器 -->
      <div
        class="border border-border rounded-lg p-4 bg-white font-mono text-sm leading-relaxed whitespace-pre-wrap break-words max-h-[600px] overflow-auto"
        v-html="diffHtml"
      ></div>
    </div>

    <!-- 空态 -->
    <div v-else class="card p-8 mb-4 text-center">
      <el-icon :size="40" class="text-text-mute mb-2"><DocumentCopy /></el-icon>
      <div class="text-text-soft font-medium mb-1">暂无对比结果</div>
      <p class="text-xs text-text-mute">
        {{ activeTab === 'text' ? '在左右两侧输入文本后点击「对比」按钮' : '上传左右两份文件提取文本后点击「对比」按钮' }}
      </p>
    </div>
  </section>
</template>
