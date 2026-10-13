/**
 * 面试题库前端 API 封装
 * 题目数据存于后端 SQLite（server/data/interview.db），不存浏览器。
 */
import { resolveApiUrl, backendGetJson, backendPostJson } from '@/utils/api'
import type {
  InterviewQuestion,
  InterviewCategory,
  Difficulty
} from '@/types/interview'

export interface ListParams {
  category?: InterviewCategory | ''
  tag?: string
  difficulty?: Difficulty | ''
  keyword?: string
  favorite?: boolean
  page?: number
  pageSize?: number
}

export interface ListResult {
  items: InterviewQuestion[]
  total: number
  page: number
  pageSize: number
}

export interface QuizParams {
  categories?: InterviewCategory[]
  tags?: string[]
  difficulties?: Difficulty[]
  count?: number
}

async function request(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  path: string,
  body?: unknown
): Promise<{ ok: true; data: unknown } | { ok: false; needBackend?: boolean; message: string }> {
  const url = resolveApiUrl(path)
  if (!url) return { ok: false, needBackend: true, message: '请先在「个人中心 → 后端加速」开启后端' }
  try {
    const resp = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined
    })
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`
      try {
        const j = (await resp.json()) as { detail?: unknown }
        if (j?.detail) msg += `：${String(j.detail).slice(0, 300)}`
      } catch {
        /* 忽略非 JSON 错误体 */
      }
      return { ok: false, message: msg }
    }
    return { ok: true, data: await resp.json() }
  } catch (err) {
    return { ok: false, message: err instanceof Error ? err.message : '请求失败' }
  }
}

export async function listQuestions(params: ListParams = {}): Promise<ListResult> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  if (params.tag) qs.set('tag', params.tag)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.keyword) qs.set('keyword', params.keyword)
  if (params.favorite !== undefined) qs.set('favorite', String(params.favorite))
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.pageSize ?? 20))
  const r = await backendGetJson(`/interview/questions?${qs.toString()}`)
  if (!r.ok) throw new Error(r.message)
  return r.data as ListResult
}

export async function getQuestion(id: string): Promise<InterviewQuestion> {
  const r = await backendGetJson(`/interview/questions/${id}`)
  if (!r.ok) throw new Error(r.message)
  return r.data as InterviewQuestion
}

export async function createQuestion(
  data: Omit<InterviewQuestion, 'id' | 'createdAt' | 'updatedAt'>
): Promise<InterviewQuestion> {
  const r = await backendPostJson('/interview/questions', data)
  if (!r.ok) throw new Error(r.message)
  return r.data as InterviewQuestion
}

export async function updateQuestion(
  id: string,
  data: Partial<InterviewQuestion>
): Promise<InterviewQuestion> {
  const r = await request('PUT', `/interview/questions/${id}`, data)
  if (!r.ok) throw new Error(r.message)
  return r.data as InterviewQuestion
}

export async function deleteQuestion(id: string): Promise<void> {
  const r = await request('DELETE', `/interview/questions/${id}`)
  if (!r.ok) throw new Error(r.message)
}

export async function importQuestions(
  items: Array<Record<string, unknown>>
): Promise<{ inserted: number; skipped: number }> {
  const r = await backendPostJson('/interview/import', { items })
  if (!r.ok) throw new Error(r.message)
  return r.data as { inserted: number; skipped: number }
}

/** 上传文件导入（.json / .txt / .md） */
export async function importFile(file: File): Promise<{ inserted: number; skipped: number }> {
  const url = resolveApiUrl('/interview/import-file')
  if (!url) throw new Error('请先在「个人中心 → 后端加速」开启后端')
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(url, { method: 'POST', body: form })
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try {
      const j = (await resp.json()) as { detail?: unknown }
      if (j?.detail) msg += `：${String(j.detail).slice(0, 300)}`
    } catch {
      /* 忽略非 JSON 错误体 */
    }
    throw new Error(msg)
  }
  return (await resp.json()) as { inserted: number; skipped: number }
}

/** 导出题目并触发浏览器下载（json 可回导；text 与粘贴导入互通） */
export async function downloadExport(
  params: { category?: string; difficulty?: string; keyword?: string },
  format: 'json' | 'text'
): Promise<void> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.keyword) qs.set('keyword', params.keyword)
  qs.set('format', format)
  const url = resolveApiUrl(`/interview/export?${qs.toString()}`)
  if (!url) throw new Error('请先在「个人中心 → 后端加速」开启后端')
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`导出失败：HTTP ${resp.status}`)
  const blob = await resp.blob()
  const disp = resp.headers.get('Content-Disposition') || ''
  const m = /filename\*=UTF-8''([^;]+)/i.exec(disp)
  const fallback = `interview_bank.${format === 'text' ? 'txt' : 'json'}`
  const filename = m ? decodeURIComponent(m[1]) : fallback
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

// ---------- 批量操作 ----------

export async function batchDeleteQuestions(ids: string[]): Promise<{ deleted: number }> {
  const r = await request('POST', '/interview/questions/batch-delete', { ids })
  if (!r.ok) throw new Error(r.message)
  return r.data as { deleted: number }
}

export async function batchUpdateQuestions(
  ids: string[],
  data: { category?: string; tags?: string[]; difficulty?: string; favorite?: boolean }
): Promise<{ updated: number }> {
  const r = await request('POST', '/interview/questions/batch-update', { ids, ...data })
  if (!r.ok) throw new Error(r.message)
  return r.data as { updated: number }
}

// ---------- 问答记录（错题本） ----------

export interface QuizRecordItem {
  id: string
  questionId: string
  userAnswer: string
  score: number
  createdAt: number
  question: InterviewQuestion | null
}

export async function saveQuizRecords(
  items: Array<{ questionId: string; userAnswer: string; score: number }>
): Promise<{ saved: number }> {
  const r = await backendPostJson('/interview/records', {
    items: items.map((i) => ({ question_id: i.questionId, user_answer: i.userAnswer, score: i.score }))
  })
  if (!r.ok) throw new Error(r.message)
  return r.data as { saved: number }
}

export async function listRecords(
  params: { scope?: 'wrong' | 'mastered' | 'all'; category?: string; page?: number; pageSize?: number } = {}
): Promise<{ items: QuizRecordItem[]; total: number; page: number }> {
  const qs = new URLSearchParams()
  qs.set('scope', params.scope ?? 'wrong')
  if (params.category) qs.set('category', params.category)
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.pageSize ?? 20))
  const r = await backendGetJson(`/interview/records?${qs.toString()}`)
  if (!r.ok) throw new Error(r.message)
  return r.data as { items: QuizRecordItem[]; total: number; page: number }
}

export async function deleteRecord(id: string): Promise<void> {
  const r = await request('DELETE', `/interview/records/${id}`)
  if (!r.ok) throw new Error(r.message)
}

export async function getRecordStats(): Promise<{
  total: number
  by_score: Record<string, number>
  wrong_by_category: Record<string, number>
}> {
  const r = await backendGetJson('/interview/records/stats')
  if (!r.ok) throw new Error(r.message)
  return r.data as { total: number; by_score: Record<string, number>; wrong_by_category: Record<string, number> }
}

// ---------- AI 智能出题 ----------

export async function aiGenerateQuestions(payload: {
  category: string
  difficulty: string
  count: number
  topic: string
  extra: string
}): Promise<Array<Record<string, unknown>>> {
  const r = await backendPostJson('/interview/ai-generate', payload, { timeoutMs: 240_000 })
  if (!r.ok) throw new Error(r.message)
  return ((r.data as { items: Array<Record<string, unknown>> }).items) || []
}

export async function quizQuestions(params: QuizParams): Promise<InterviewQuestion[]> {
  const qs = new URLSearchParams()
  if (params.categories?.length) qs.set('categories', params.categories.join(','))
  if (params.tags?.length) qs.set('tags', params.tags.join(','))
  if (params.difficulties?.length) qs.set('difficulties', params.difficulties.join(','))
  qs.set('count', String(params.count ?? 10))
  const r = await backendGetJson(`/interview/quiz?${qs.toString()}`)
  if (!r.ok) throw new Error(r.message)
  return ((r.data as { items: InterviewQuestion[] }).items) || []
}

export async function getStats(): Promise<{
  total: number
  by_category: Record<string, number>
  by_difficulty: Record<string, number>
  favorites: number
}> {
  const r = await backendGetJson('/interview/stats')
  if (!r.ok) throw new Error(r.message)
  return r.data as {
    total: number
    by_category: Record<string, number>
    by_difficulty: Record<string, number>
    favorites: number
  }
}

/** 解析用户粘贴的纯文本/JSON 为可导入题目数组
 *  - JSON 数组：[{title, answer, category, tags, difficulty}]
 *  - 纯文本：每题用空行分隔，首行为题干，"答：" 或 "答案：" 开头为答案
 */
export function parseImportText(text: string): Array<Record<string, unknown>> {
  const trimmed = text.trim()
  if (!trimmed) return []
  // 尝试 JSON
  if (trimmed.startsWith('[')) {
    try {
      const arr = JSON.parse(trimmed)
      if (Array.isArray(arr)) return arr as Array<Record<string, unknown>>
    } catch {
      /* 继续走文本解析 */
    }
  }
  // 文本解析：空行分题
  const blocks = trimmed.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean)
  return blocks.map((block) => {
    const lines = block.split('\n').map((l) => l.trimEnd())
    let title = ''
    let answer = ''
    let category = ''
    let difficulty = ''
    const tags: string[] = []
    for (const line of lines) {
      const m = line.match(/^(分类|category|类别|tag|标签|难度|difficulty)[:：]\s*(.+)$/i)
      if (m) {
        const val = m[2].trim()
        if (['分类', 'category', '类别'].includes(m[1])) category = val
        else if (['tag', '标签'].includes(m[1])) tags.push(...val.split(/[,，]/).map((s) => s.trim()).filter(Boolean))
        else if (['难度', 'difficulty'].includes(m[1])) difficulty = val
        continue
      }
      if (/^(答|答案|answer)[:：]/i.test(line)) {
        answer += line.replace(/^(答|答案|answer)[:：]\s*/i, '') + '\n'
      } else if (!title) {
        title = line
      } else {
        answer += line + '\n'
      }
    }
    return {
      title: title.trim(),
      answer: answer.trim(),
      category: category || undefined,
      tags: tags.length ? tags : undefined,
      difficulty: difficulty || undefined
    }
  }).filter((q) => q.title)
}
