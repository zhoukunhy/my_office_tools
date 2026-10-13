<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'
import { usePreferenceStore } from '@/stores/preference'
import { backendFetch, resolveApiUrl } from '@/utils/api'
import { downloadBlob } from '@/utils/file'

const pref = usePreferenceStore()
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const exporting = ref(false)

/** 后端是否可用（已开启且能解析出 API 地址） */
const backendReady = computed(() => resolveApiUrl('/md-to-pdf') !== null)

const sample = `# Markdown 编辑器

欢迎来到 **速用工具箱** 的 Markdown 编辑器！左侧编辑、右侧实时预览，支持导出 PDF。

## 文本样式

支持 *斜体*、**加粗**、\`行内代码\`，也可组合 ***加粗斜体***。

## 列表

无序列表：

- 第一项
- 第二项
- 第三项

有序列表：

1. 准备
2. 执行
3. 完成

## 引用

> 这是一段引用。
> 可以包含 **加粗** 和 \`代码\`。

## 链接与图片

[访问示例站点](https://example.com)

## 代码块

\`\`\`
function greet(name) {
  return 'Hello, ' + name
}
\`\`\`

## 表格

| 功能 | 说明 | 状态 |
| --- | --- | --- |
| 编辑 | 实时输入 | ✅ |
| 预览 | 即时渲染 | ✅ |
| 导出 | PDF / HTML | ✅ |

---

开始你的创作吧！`

const input = ref(sample)

/* ------------------------------------------------------------------ *
 * 简易 Markdown 渲染器（先转义 HTML，再应用 markdown 规则，防 XSS）
 * ------------------------------------------------------------------ */
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** 行内规则：图片 → 链接 → 加粗 → 斜体 */
function renderInline(text: string): string {
  // 图片 ![alt](url)
  text = text.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, '<img src="$2" alt="$1" />')
  // 链接 [text](url)
  text = text.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  // 加粗 **text**
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 斜体 *text*
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return text
}

function isTableSep(l: string): boolean {
  const t = l.trim()
  return /\|/.test(t) && /-/.test(t) && /^[\s|:|-]+$/.test(t)
}

function renderMarkdown(md: string): string {
  if (!md.trim()) return ''

  // 1. 转义 HTML，防止 XSS
  let src = escapeHtml(md)

  // 2. 抽取代码块与行内代码到占位符，避免内部语法被处理
  const store: string[] = []
  const stash = (html: string): string => {
    store.push(html)
    return `\u0000${store.length - 1}\u0000`
  }
  // 代码块 ```
  src = src.replace(/```[ ]*[\w-]*\n?([\s\S]*?)```/g, (_m, code: string) =>
    stash(`<pre><code>${String(code).replace(/\n$/, '')}</code></pre>`)
  )
  // 行内代码 `code`
  src = src.replace(/`([^`\n]+)`/g, (_m, code: string) => stash(`<code>${code}</code>`))

  const lines = src.split('\n')
  const out: string[] = []
  const isPlace = (l: string) => /^\u0000\d+\u0000$/.test(l)

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // 占位符（代码块）整行输出
    if (isPlace(line)) {
      out.push(line)
      i++
      continue
    }

    // 水平分隔线 --- / *** / ___
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      out.push('<hr />')
      i++
      continue
    }

    // 标题 # ~ ######
    const h = /^(#{1,6})\s+(.*)$/.exec(line)
    if (h) {
      const level = h[1].length
      out.push(`<h${level}>${renderInline(h[2].trim())}</h${level}>`)
      i++
      continue
    }

    // 表格：当前行含 | 且下一行是分隔行
    if (/\|/.test(line) && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const splitCells = (l: string) => {
        const cells = l.split('|').map((c) => c.trim())
        while (cells.length && cells[0] === '') cells.shift()
        while (cells.length && cells[cells.length - 1] === '') cells.pop()
        return cells
      }
      const header = splitCells(line)
      out.push(
        '<table><thead><tr>' +
          header.map((c) => `<th>${renderInline(c)}</th>`).join('') +
          '</tr></thead><tbody>'
      )
      i += 2 // 跳过表头与分隔行
      while (i < lines.length && /\|/.test(lines[i])) {
        const row = splitCells(lines[i])
        out.push('<tr>' + row.map((c) => `<td>${renderInline(c)}</td>`).join('') + '</tr>')
        i++
      }
      out.push('</tbody></table>')
      continue
    }

    // 引用 >
    if (/^\s*>\s?/.test(line)) {
      const buf: string[] = []
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ''))
        i++
      }
      out.push(`<blockquote>${buf.map(renderInline).join('<br />')}</blockquote>`)
      continue
    }

    // 无序列表 - / *
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''))
        i++
      }
      out.push('<ul>' + items.map((it) => `<li>${renderInline(it)}</li>`).join('') + '</ul>')
      continue
    }

    // 有序列表 1.
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''))
        i++
      }
      out.push('<ol>' + items.map((it) => `<li>${renderInline(it)}</li>`).join('') + '</ol>')
      continue
    }

    // 空行
    if (/^\s*$/.test(line)) {
      i++
      continue
    }

    // 段落：收集连续普通行
    const buf: string[] = []
    while (
      i < lines.length &&
      !/^\s*$/.test(lines[i]) &&
      !isPlace(lines[i]) &&
      !/^\s*([-*_])\1{2,}\s*$/.test(lines[i]) &&
      !/^#{1,6}\s+/.test(lines[i]) &&
      !/^\s*>\s?/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !/\|/.test(lines[i])
    ) {
      buf.push(lines[i])
      i++
    }
    out.push(`<p>${buf.map(renderInline).join('<br />')}</p>`)
  }

  // 3. 还原代码占位符
  let result = out.join('\n')
  result = result.replace(/\u0000(\d+)\u0000/g, (_m, idx: string) => store[Number(idx)] || '')
  return result
}

const htmlContent = computed(() => renderMarkdown(input.value))

/* ------------------------------------------------------------------ *
 * 编辑器统计
 * ------------------------------------------------------------------ */
const charCount = computed(() => input.value.replace(/\s/g, '').length)
const lineCount = computed(() => input.value.split('\n').length)

/* ------------------------------------------------------------------ *
 * 工具栏：在选区前后包裹语法或插入内容
 * ------------------------------------------------------------------ */
function surround(before: string, after: string, placeholder: string) {
  const ta = textareaRef.value
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const text = input.value
  const sel = text.slice(start, end) || placeholder
  input.value = text.slice(0, start) + before + sel + after + text.slice(end)
  nextTick(() => {
    ta.focus()
    const pos = start + before.length
    ta.setSelectionRange(pos, pos + sel.length)
  })
}

function insertLine(prefix: string) {
  const ta = textareaRef.value
  if (!ta) return
  const start = ta.selectionStart
  const text = input.value
  const lineStart = text.lastIndexOf('\n', start - 1) + 1
  input.value = text.slice(0, lineStart) + prefix + text.slice(lineStart)
  nextTick(() => {
    ta.focus()
    ta.setSelectionRange(start + prefix.length, start + prefix.length)
  })
}

function insertText(content: string) {
  const ta = textareaRef.value
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const text = input.value
  input.value = text.slice(0, start) + content + text.slice(end)
  nextTick(() => {
    ta.focus()
    const pos = start + content.length
    ta.setSelectionRange(pos, pos)
  })
}

function insertTable() {
  insertText('| 列1 | 列2 | 列3 |\n| --- | --- | --- |\n| 内容 | 内容 | 内容 |\n')
}

/* ------------------------------------------------------------------ *
 * 导出
 * ------------------------------------------------------------------ */
async function exportPdf() {
  if (!pref.backendEnabled) {
    ElMessage.warning('请先在「个人中心」开启后端加速')
    return
  }
  if (!input.value.trim()) {
    ElMessage.warning('内容为空，无法导出')
    return
  }
  exporting.value = true
  try {
    const form = new FormData()
    form.append('content', input.value)
    form.append('filename', 'document.pdf')
    const r = await backendFetch('/md-to-pdf', form, { timeoutMs: 60000 })
    if (r.ok) {
      downloadBlob(r.blob, r.filename || 'document.pdf')
      ElMessage.success('PDF 导出成功')
    } else if (r.needBackend) {
      ElMessage.warning('请先开启后端加速')
    } else {
      ElMessage.error(r.message)
    }
  } finally {
    exporting.value = false
  }
}

function buildStandaloneHtml(): string {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Markdown 文档</title>
<style>
body{font-family:-apple-system,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;max-width:820px;margin:40px auto;padding:0 20px;color:#161b2c;line-height:1.7}
h1,h2,h3,h4,h5,h6{margin:1.2em 0 .6em;font-weight:600}
h1{font-size:1.8em;border-bottom:1px solid #eee;padding-bottom:.3em}
h2{font-size:1.5em;border-bottom:1px solid #eee;padding-bottom:.3em}
pre{background:#f6f8fa;padding:12px 14px;border-radius:6px;overflow-x:auto}
code{font-family:'JetBrains Mono',Consolas,monospace;font-size:.9em}
p code,li code,td code{background:#f6f8fa;padding:2px 5px;border-radius:3px}
blockquote{border-left:4px solid #4f6eff;margin:.8em 0;padding:.4em 1em;color:#555;background:#f7f8fb;border-radius:0 4px 4px 0}
table{border-collapse:collapse;margin:1em 0}
th,td{border:1px solid #ddd;padding:6px 12px}
th{background:#f7f8fb}
img{max-width:100%}
a{color:#4f6eff}
hr{border:none;border-top:1px solid #eee;margin:1.5em 0}
</style>
</head>
<body>
${htmlContent.value}
</body>
</html>`
}

function exportHtml() {
  if (!input.value.trim()) {
    ElMessage.warning('内容为空，无法导出')
    return
  }
  downloadBlob(
    new Blob([buildStandaloneHtml()], { type: 'text/html;charset=utf-8' }),
    'document.html'
  )
  ElMessage.success('HTML 导出成功')
}

async function copyHtml() {
  if (!input.value.trim()) {
    ElMessage.warning('内容为空')
    return
  }
  await navigator.clipboard.writeText(htmlContent.value)
  ElMessage.success('已复制 HTML')
}

function clearAll() {
  input.value = ''
  ElMessage.success('已清空')
}

function resetSample() {
  input.value = sample
  ElMessage.success('已载入示例')
}
</script>

<template>
  <ToolHeader title="Markdown 编辑器" description="在线编辑、实时预览、导出 PDF">
    <template #statusTop>
      <span class="text-xs" :class="backendReady ? 'text-success' : 'text-warning'">
        {{ backendReady ? '✓ 后端可用，支持导出 PDF' : '⚡ 未开启后端，导出 PDF 不可用' }}
      </span>
    </template>
  </ToolHeader>

  <section class="container-page max-w-7xl py-6">
    <!-- 工具栏 -->
    <div class="card p-3 mb-4 flex flex-wrap items-center gap-2">
      <span class="text-xs text-text-mute mr-1">格式</span>
      <button class="btn-ghost border border-border !px-2.5 font-semibold" title="一级标题" @click="insertLine('# ')">H1</button>
      <button class="btn-ghost border border-border !px-2.5 font-semibold" title="二级标题" @click="insertLine('## ')">H2</button>
      <button class="btn-ghost border border-border !px-2.5 font-semibold" title="三级标题" @click="insertLine('### ')">H3</button>
      <span class="text-text-mute">|</span>
      <button class="btn-ghost border border-border !px-2.5 font-bold" title="加粗" @click="surround('**', '**', '加粗')">B</button>
      <button class="btn-ghost border border-border !px-2.5 italic" title="斜体" @click="surround('*', '*', '斜体')">I</button>
      <button class="btn-ghost border border-border !px-2.5 font-mono" title="行内代码" @click="surround('`', '`', 'code')">Code</button>
      <span class="text-text-mute">|</span>
      <button class="btn-ghost border border-border !px-2.5" title="链接" @click="surround('[', '](https://)', '链接文字')">链接</button>
      <button class="btn-ghost border border-border !px-2.5" title="图片" @click="insertText('![图片描述](https://)')">图片</button>
      <span class="text-text-mute">|</span>
      <button class="btn-ghost border border-border !px-2.5" title="无序列表" @click="insertLine('- ')">列表</button>
      <button class="btn-ghost border border-border !px-2.5" title="引用" @click="insertLine('> ')">引用</button>
      <button class="btn-ghost border border-border !px-2.5" title="表格" @click="insertTable">表格</button>
      <button class="btn-ghost border border-border !px-2.5" title="分隔线" @click="insertText('\n---\n')">分隔线</button>

      <div class="ml-auto flex flex-wrap gap-2">
        <button class="btn-ghost border border-border" @click="resetSample">
          <el-icon :size="16"><RefreshLeft /></el-icon>载入示例
        </button>
        <button class="btn-ghost border border-border btn-ghost-danger" @click="clearAll">
          <el-icon :size="16"><Delete /></el-icon>清空
        </button>
        <button class="btn-ghost border border-border" @click="copyHtml">
          <el-icon :size="16"><CopyDocument /></el-icon>复制 HTML
        </button>
        <button class="btn-ghost border border-border" @click="exportHtml">
          <el-icon :size="16"><Document /></el-icon>导出 HTML
        </button>
        <button
          class="btn-primary"
          :disabled="exporting || !backendReady"
          @click="exportPdf"
        >
          <el-icon :size="16"><Download /></el-icon>
          {{ exporting ? '导出中…' : '导出 PDF' }}
        </button>
      </div>
    </div>

    <!-- 分屏：左编辑 / 右预览 -->
    <div class="flex flex-col lg:flex-row gap-4">
      <div class="flex-1 flex flex-col card overflow-hidden">
        <div class="text-xs text-text-mute px-3 py-2 border-b border-border bg-bg-soft">
          编辑器
        </div>
        <textarea
          ref="textareaRef"
          v-model="input"
          class="flex-1 w-full p-4 outline-none resize-none bg-transparent font-mono text-sm leading-relaxed"
          style="min-height: 500px"
          placeholder="在此输入 Markdown 文本…"
          spellcheck="false"
        ></textarea>
      </div>
      <div class="flex-1 flex flex-col card overflow-hidden">
        <div class="text-xs text-text-mute px-3 py-2 border-b border-border bg-bg-soft">
          预览
        </div>
        <div
          class="md-preview flex-1 p-4 overflow-auto"
          style="min-height: 500px"
          v-html="htmlContent"
        ></div>
      </div>
    </div>

    <!-- 统计栏 -->
    <div class="flex flex-wrap items-center justify-between mt-3 text-xs text-text-mute gap-2">
      <span>{{ charCount }} 字符 · {{ lineCount }} 行</span>
      <span :class="backendReady ? 'text-success' : 'text-warning'">
        {{ backendReady ? '✓ 后端可用，支持导出 PDF' : '⚡ 未开启后端，导出 PDF 不可用' }}
      </span>
    </div>
  </section>
</template>

<style scoped>
.md-preview {
  line-height: 1.7;
  word-break: break-word;
}
.md-preview :deep(h1),
.md-preview :deep(h2),
.md-preview :deep(h3),
.md-preview :deep(h4),
.md-preview :deep(h5),
.md-preview :deep(h6) {
  margin: 1em 0 0.5em;
  font-weight: 600;
}
.md-preview :deep(h1) {
  font-size: 1.6em;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 0.3em;
}
.md-preview :deep(h2) {
  font-size: 1.4em;
  border-bottom: 1px solid var(--c-border-soft);
  padding-bottom: 0.3em;
}
.md-preview :deep(h3) {
  font-size: 1.2em;
}
.md-preview :deep(p) {
  margin: 0.6em 0;
}
.md-preview :deep(ul),
.md-preview :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.6em;
}
.md-preview :deep(li) {
  margin: 0.25em 0;
}
.md-preview :deep(blockquote) {
  border-left: 3px solid var(--c-primary);
  margin: 0.8em 0;
  padding: 0.4em 1em;
  color: var(--c-text-soft);
  background: var(--c-bg-soft);
  border-radius: 0 4px 4px 0;
}
.md-preview :deep(pre) {
  background: var(--c-bg-soft);
  padding: 10px 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.8em 0;
}
.md-preview :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.9em;
}
.md-preview :deep(p code),
.md-preview :deep(li code),
.md-preview :deep(td code) {
  background: var(--c-bg-soft);
  padding: 1px 4px;
  border-radius: 3px;
}
.md-preview :deep(table) {
  border-collapse: collapse;
  margin: 0.8em 0;
  display: block;
  overflow-x: auto;
}
.md-preview :deep(th),
.md-preview :deep(td) {
  border: 1px solid var(--c-border);
  padding: 5px 10px;
  text-align: left;
}
.md-preview :deep(th) {
  background: var(--c-bg-soft);
  font-weight: 600;
}
.md-preview :deep(img) {
  max-width: 100%;
}
.md-preview :deep(a) {
  color: var(--c-primary);
}
.md-preview :deep(hr) {
  border: none;
  border-top: 1px solid var(--c-border);
  margin: 1.2em 0;
}
</style>
