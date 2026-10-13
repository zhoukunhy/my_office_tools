/**
 * AI 生成 PPT 状态与逻辑：大纲生成/多轮修改、并发生成任务轮询、单页修复、本地缓存
 * 所有状态保存在浏览器本地 localStorage，不额外上报
 */
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { backendGetJson, backendPostJson, getBackendStatus, backendFetch } from '@/utils/api'
import { THEME_PRESETS } from '@/types/aiPpt'
import type { DeckOutline, PptTask, PptTheme, Slide } from '@/types/aiPpt'

export type AiPptStep = 1 | 2 | 3 | 4

const CACHE_KEY = 'ai-ppt-state-v1'

interface AiPptState {
  step: AiPptStep
  topic: string
  /** 背景与场合 */
  background: string
  /** 主要内容（希望涵盖的重点） */
  content: string
  /** 风格要求 */
  style: string
  docText: string
  pageCount: number
  outline: DeckOutline | null
  slides: Slide[]
  theme: PptTheme
  activeIndex: number
  scrollMode: boolean
}

const state = reactive<AiPptState>({
  step: 1,
  topic: '',
  background: '',
  content: '',
  style: '',
  docText: '',
  pageCount: 10,
  outline: null,
  slides: [],
  theme: { ...THEME_PRESETS[0].theme },
  activeIndex: 1,
  scrollMode: false
})

const outlineLoading = ref(false)
const revising = ref(false)
const exporting = ref(false)
const fixing = ref(false)
const taskId = ref('')
const task = ref<PptTask | null>(null)
let pollTimer: number | null = null

// ---- 本地缓存 ----

function persist() {
  try {
    const data: Partial<AiPptState> = {
      step: state.step,
      topic: state.topic,
      background: state.background,
      docText: state.docText.slice(0, 20000),
      pageCount: state.pageCount,
      outline: state.outline,
      slides: state.slides,
      theme: state.theme,
      activeIndex: state.activeIndex,
      scrollMode: state.scrollMode
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(data))
  } catch {
    /* 缓存写满等异常静默，不影响主流程 */
  }
}

function restore() {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return
    const saved = JSON.parse(raw) as Partial<AiPptState>
    Object.assign(state, {
      step: saved.step ?? 1,
      topic: saved.topic ?? '',
      background: saved.background ?? '',
      docText: saved.docText ?? '',
      pageCount: saved.pageCount ?? 10,
      outline: saved.outline ?? null,
      slides: Array.isArray(saved.slides) ? saved.slides : [],
      theme: saved.theme ?? { ...THEME_PRESETS[0].theme },
      activeIndex: saved.activeIndex ?? 1,
      scrollMode: saved.scrollMode ?? false
    })
  } catch {
    /* 缓存损坏时忽略，重新开始 */
  }
}

let watchInstalled = false
function installPersistWatch() {
  if (watchInstalled) return
  watchInstalled = true
  let timer: number | null = null
  watch(
    () => [state.step, state.topic, state.background, state.content, state.style, state.pageCount, state.outline, state.slides, state.theme, state.activeIndex, state.scrollMode],
    () => {
      if (timer) window.clearTimeout(timer)
      timer = window.setTimeout(persist, 400)
    },
    { deep: true }
  )
}

// ---- 文档提取（长文档输入） ----

export async function extractDocText(file: File): Promise<string> {
  const ext = file.name.slice(file.name.lastIndexOf('.') + 1).toLowerCase()
  if (ext === 'txt') {
    const buf = await file.arrayBuffer()
    try {
      return new TextDecoder('utf-8', { fatal: true }).decode(buf)
    } catch {
      return new TextDecoder('gbk').decode(buf)
    }
  }
  if (!['docx', 'doc', 'pdf'].includes(ext)) {
    throw new Error('仅支持 .docx / .doc / .pdf / .txt 文件')
  }
  if (!getBackendStatus().enabled) {
    throw new Error('提取 Word/PDF 文档需要开启后端加速，或改传 .txt 文件')
  }
  const fd = new FormData()
  fd.append('file', file)
  const r = await backendFetch('/doc/extract-text', fd, { timeoutMs: 120_000 })
  if (!r.ok) throw new Error(r.message)
  const raw = (await r.blob.text()).trim()
  let text = raw
  if (raw.startsWith('{')) {
    try {
      text = ((JSON.parse(raw) as { text?: string }).text ?? '').trim()
    } catch {
      text = raw
    }
  }
  if (!text) throw new Error('文档中未提取到文字内容')
  return text
}

// ---- API 调用 ----

function needBackend(): boolean {
  if (!getBackendStatus().enabled) {
    ElMessage.error('AI 生成 PPT 需要开启后端加速（个人中心可配置）')
    return true
  }
  return false
}

async function genOutline() {
  if (needBackend()) return
  if (!state.topic.trim()) {
    ElMessage.warning('请先输入 PPT 主题')
    return
  }
  outlineLoading.value = true
  try {
    const r = await backendPostJson(
      '/ai-ppt/outline',
      { topic: state.topic.trim(), background: (state.background + '\n' + state.docText).trim().slice(0, 12000), page_count: state.pageCount },
      { timeoutMs: 300_000 }
    )
    if (!r.ok) throw new Error(r.message)
    const data = r.data as { outline: DeckOutline }
    state.outline = data.outline
    state.step = 2
    ElMessage.success(`大纲已生成，共 ${data.outline.pages.length} 页`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '大纲生成失败，请重试')
  } finally {
    outlineLoading.value = false
  }
}

async function reviseOutline(feedback: string, focusIndex?: number) {
  if (needBackend() || !state.outline) return
  if (!feedback.trim()) {
    ElMessage.warning('请描述你想怎么修改')
    return
  }
  revising.value = true
  try {
    const r = await backendPostJson(
      '/ai-ppt/outline/revise',
      { outline: state.outline, feedback: feedback.trim(), focus_index: focusIndex || null },
      { timeoutMs: 300_000 }
    )
    if (!r.ok) throw new Error(r.message)
    const data = r.data as { outline: DeckOutline }
    state.outline = data.outline
    ElMessage.success('大纲已按反馈修改')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '大纲修改失败，请重试')
  } finally {
    revising.value = false
  }
}

async function pollOnce(taskIdVal: string): Promise<boolean> {
  const r = await backendGetJson(`/ai-ppt/tasks/${taskIdVal}`)
  if (!r.ok) {
    stopPolling()
    ElMessage.error(`查询生成进度失败：${r.message}`)
    return true
  }
  const data = r.data as PptTask
  task.value = data
  // 每页完成后立即合入可编辑列表（生成中也能先看先改）
  const donePages = data.pages.filter((p) => p.status === 'done' && p.data)
  if (donePages.length) {
    for (const p of donePages) {
      const slide = p.data as Slide
      const exist = state.slides.find((s) => s.index === slide.index)
      if (exist) {
        // 保留本地已有的手动编辑：仅当本地为空或未被用户改过时覆盖
        const local = state.slides.indexOf(exist)
        if (!exist._edited) state.slides[local] = slide
      } else {
        state.slides.push(slide)
      }
    }
    state.slides.sort((a, b) => a.index - b.index)
  }
  if (data.status === 'done') {
    stopPolling()
    state.step = 4
    const failedCount = data.failed
    if (failedCount > 0) {
      ElMessage.warning(`生成完成，但有 ${failedCount} 页失败，可在左侧列表对失败页单独重试`)
    } else {
      ElMessage.success(`全部 ${data.total} 页生成完成`)
    }
    return true
  }
  return false
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

async function startGenerate() {
  if (needBackend() || !state.outline) return
  try {
    const r = await backendPostJson('/ai-ppt/generate', { outline: state.outline }, { timeoutMs: 60_000 })
    if (!r.ok) throw new Error(r.message)
    const data = r.data as { task_id: string; total: number }
    taskId.value = data.task_id
    task.value = { task_id: data.task_id, status: 'running', total: data.total, completed: 0, failed: 0, pages: [] }
    state.slides = []
    state.step = 3
    stopPolling()
    pollTimer = window.setInterval(() => {
      pollOnce(taskId.value).catch(() => {})
    }, 1500)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '创建生成任务失败')
  }
}

async function fixPage(slide: Slide, feedback: string) {
  if (needBackend()) return
  fixing.value = true
  try {
    const r = await backendPostJson(
      '/ai-ppt/page/fix',
      { page: slide, deck_title: state.outline?.title ?? '', feedback: feedback.trim() },
      { timeoutMs: 180_000 }
    )
    if (!r.ok) throw new Error(r.message)
    const data = r.data as { page: Slide }
    const idx = state.slides.findIndex((s) => s.index === slide.index)
    if (idx >= 0) state.slides[idx] = { ...data.page, _edited: true }
    ElMessage.success(`第 ${slide.index} 页已重新生成`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '单页修复失败，请重试')
  } finally {
    fixing.value = false
  }
}

async function retryFailedPages() {
  if (!task.value) return
  const failedIdx = task.value.pages.filter((p) => p.status === 'failed').map((p) => p.index)
  if (!failedIdx.length) return
  const pages = state.outline?.pages.filter((p) => failedIdx.includes(p.index)) ?? []
  if (!pages.length) return
  try {
    const r = await backendPostJson(
      '/ai-ppt/generate',
      { outline: { ...state.outline!, pages }, },
      { timeoutMs: 60_000 }
    )
    if (!r.ok) throw new Error(r.message)
    const data = r.data as { task_id: string; total: number }
    taskId.value = data.task_id
    stopPolling()
    pollTimer = window.setInterval(() => {
      pollOnce(taskId.value).catch(() => {})
    }, 1500)
    ElMessage.info(`正在重试 ${data.total} 个失败页`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '重试失败')
  }
}

async function exportFile() {
  if (!state.slides.length) {
    ElMessage.warning('还没有可导出的页面')
    return
  }
  exporting.value = true
  try {
    const { exportPptx } = await import('@/utils/pptxExport')
    const name = await exportPptx(state.slides, state.theme, state.outline?.title ?? state.topic)
    ElMessage.success(`已导出：${name}`)
  } catch (err) {
    console.error(err)
    ElMessage.error(err instanceof Error ? `导出失败：${err.message}` : '导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

function resetAll() {
  stopPolling()
  Object.assign(state, {
    step: 1,
    topic: '',
    background: '',
    content: '',
    style: '',
    docText: '',
    pageCount: 10,
    outline: null,
    slides: [],
    theme: { ...THEME_PRESETS[0].theme },
    activeIndex: 1,
    scrollMode: false
  })
  task.value = null
  taskId.value = ''
  ElMessage.success('已重置，可重新开始')
}

// ---- 单例导出 ----

let inited = false

export function useAiPpt() {
  if (!inited) {
    inited = true
    restore()
    installPersistWatch()
  }
  return {
    state,
    outlineLoading,
    revising,
    exporting,
    fixing,
    task,
    taskId,
    genOutline,
    reviseOutline,
    startGenerate,
    fixPage,
    retryFailedPages,
    exportFile,
    resetAll,
    stopPolling
  }
}
