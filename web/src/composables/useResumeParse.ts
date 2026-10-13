/**
 * 简历文本解析：把 docx/pdf/txt 提取出的纯文本，启发式解析为结构化简历数据
 * 解析全部在浏览器本地完成；仅 docx/doc/pdf 的文本提取依赖已开启的后端加速
 */
import { backendFetch, getBackendStatus } from '@/utils/api'

export type ResumeSection = 'experience' | 'projects' | 'education'

export interface ResumeItem {
  id: number
  title: string
  organization: string
  period: string
  description: string
}

export interface ResumeProfile {
  name: string
  role: string
  email: string
  phone: string
  location: string
  summary: string
}

export interface ParsedEntry {
  title: string
  organization: string
  period: string
  description: string
}

export interface ParsedResume {
  profile: Partial<ResumeProfile>
  experience: ParsedEntry[]
  projects: ParsedEntry[]
  education: ParsedEntry[]
}

export const SECTION_LABELS: Record<ResumeSection, string> = {
  experience: '工作经历',
  projects: '项目经历',
  education: '教育背景'
}

const SECTION_WORDS: { key: ResumeSection; words: string[] }[] = [
  { key: 'experience', words: ['工作经历', '工作经验', '职业经历', '工作履历', '实习经历', '实习经验', '实践经历'] },
  { key: 'projects', words: ['项目经历', '项目经验', '项目实践', '项目案例', '代表项目'] },
  { key: 'education', words: ['教育经历', '教育背景', '教育经验', '学习经历', '教育情况'] }
]

const SUMMARY_WORDS = ['自我评价', '个人评价', '个人简介', '自我介绍', '个人总结', '职业总结', '技能特长', '专业技能', '荣誉奖项', '证书']

const EMAIL_RE = /[\w.+-]+@[\w-]+\.[\w.-]+/
const PHONE_RE = /(?:\+?86[\s-]?)?1[3-9]\d{9}/
const DATE_RE = /(?:19|20)\d{2}\s*(?:[.\-/年]|\s*[-–—~至])/
const PERIOD_RE = /(?:19|20)\d{2}\s*[.\-/年]?\s*\d{0,2}\s*(?:[.\-/月]\s*\d{0,2}\s*月?)?\s*(?:[-–—~至到]\s*(?:(?:19|20)\d{2}\s*[.\-/年]?\s*\d{0,2}\s*(?:[.\-/月]\s*\d{0,2}\s*月?)?|至今|现在|今|now))?/

const SUPPORTED_EXTS = ['docx', 'doc', 'pdf', 'txt']

function getExt(name: string) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i + 1).toLowerCase() : ''
}

export function isSupportedResumeFile(name: string) {
  return SUPPORTED_EXTS.includes(getExt(name))
}

function cleanSeg(s: string) {
  return s.replace(/^[\s\-–—•·|｜:：,，、]+|[\s\-–—|｜,，、]+$/g, '').trim()
}

function classifyLine(line: string): ResumeSection | 'summary' | null {
  if (line.length > 26 || /\d{3}/.test(line) || EMAIL_RE.test(line)) return null
  for (const { key, words } of SECTION_WORDS) {
    if (words.some((w) => line.includes(w))) return key
  }
  if (SUMMARY_WORDS.some((w) => line.includes(w))) return 'summary'
  return null
}

function splitHeadLine(line: string, period: string): { title: string; organization: string } {
  let rest = cleanSeg(period ? line.replace(period, '') : line)
  rest = rest.replace(/^[|｜·\-–—\s]+|[|｜·\-–—\s]+$/g, '')
  const parts = rest.split(/\s*[|｜]\s*|\s{2,}/).map(cleanSeg).filter(Boolean)
  if (parts.length >= 2) return { title: parts[0], organization: parts[1] }
  const two = rest.split(/\s+/)
  if (two.length === 2 && two[0].length <= 15 && two[1].length <= 15) {
    return { title: two[0], organization: two[1] }
  }
  return { title: parts[0] || '经历条目', organization: '' }
}

function parseSection(lines: string[]): ParsedEntry[] {
  const entries: ParsedEntry[] = []
  for (const raw of lines) {
    const trimmed = raw.trim()
    const isBullet = /^[•·\-–—*]/.test(trimmed)
    const period = trimmed.match(PERIOD_RE)?.[0] ?? ''
    const looksLikeHead = (DATE_RE.test(trimmed) || trimmed.includes('|') || trimmed.includes('｜')) && !isBullet && trimmed.length <= 80
    if (looksLikeHead) {
      const { title, organization } = splitHeadLine(trimmed, period)
      entries.push({ title: title || '经历条目', organization, period, description: '' })
    } else if (entries.length) {
      const last = entries[entries.length - 1]
      const text = cleanSeg(trimmed)
      if (!text) continue
      if (!last.organization && !isBullet && text.length <= 24 && !/[。；;]/.test(text)) {
        last.organization = text
      } else {
        last.description = last.description ? `${last.description}\n${text}` : text
      }
    } else if (cleanSeg(trimmed)) {
      entries.push({ title: cleanSeg(trimmed), organization: '', period, description: '' })
    }
  }
  return entries
}

function parseHeader(lines: string[]): ParsedResume['profile'] {
  const profile: ParsedResume['profile'] = {}
  const roleRe = /(?:求职意向|应聘岗位|目标职位|期望职位)[:：]?\s*(\S{1,20})/
  const locRe = /(?:现居|所在城市|工作地点|期望城市|城市)[:：]?\s*(\S{1,20})/
  const leftover: string[] = []
  for (const raw of lines) {
    if (!profile.email) {
      const m = raw.match(EMAIL_RE)
      if (m) profile.email = m[0]
    }
    if (!profile.phone) {
      const m = raw.match(PHONE_RE)
      if (m) profile.phone = m[0]
    }
    const rm = raw.match(roleRe)
    if (rm && !profile.role) {
      profile.role = cleanSeg(rm[1])
      continue
    }
    const lm = raw.match(locRe)
    if (lm && !profile.location) {
      profile.location = cleanSeg(lm[1])
      continue
    }
    leftover.push(raw)
  }
  const rest = leftover.filter((l) => l !== profile.email && !PHONE_RE.test(l))
  const nameIdx = rest.findIndex((l) => l.length >= 2 && l.length <= 12 && !/\d/.test(l) && !EMAIL_RE.test(l))
  if (nameIdx >= 0) {
    profile.name = rest[nameIdx]
    for (let i = nameIdx + 1; i < rest.length; i++) {
      const l = rest[i]
      if (l.length <= 15 && !/\d/.test(l) && !profile.role) {
        profile.role = l
        break
      }
    }
  }
  return profile
}

export function parseResumeText(text: string): ParsedResume {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
  const buckets: Record<'header' | 'summary' | ResumeSection, string[]> = {
    header: [],
    summary: [],
    experience: [],
    projects: [],
    education: []
  }
  let current: keyof typeof buckets = 'header'
  for (const line of lines) {
    const kind = classifyLine(line)
    if (kind) current = kind
    buckets[current].push(line)
  }
  const profile = parseHeader(buckets.header)
  const summaryText = buckets.summary.map(cleanSeg).filter(Boolean).join(' ')
  if (summaryText) profile.summary = summaryText.slice(0, 300)
  return {
    profile,
    experience: parseSection(buckets.experience),
    projects: parseSection(buckets.projects),
    education: parseSection(buckets.education)
  }
}

export async function extractResumeText(file: File): Promise<string> {
  const ext = getExt(file.name)
  if (!SUPPORTED_EXTS.includes(ext)) {
    throw new Error('仅支持 .docx / .doc / .pdf / .txt 格式的简历文件')
  }
  if (ext === 'txt') {
    const buf = await file.arrayBuffer()
    try {
      return new TextDecoder('utf-8', { fatal: true }).decode(buf)
    } catch {
      return new TextDecoder('gbk').decode(buf)
    }
  }
  if (!getBackendStatus().enabled) {
    throw new Error('解析 Word/PDF 简历需要开启后端加速（个人中心可开启），或改传 .txt 文件')
  }
  const fd = new FormData()
  fd.append('file', file)
  const r = await backendFetch('/doc/extract-text', fd, { timeoutMs: 120_000 })
  if (!r.ok) throw new Error(r.message)
  const raw = (await r.blob.text()).trim()
  if (!raw) throw new Error('文件中未提取到文字内容（可能是扫描件，请先转文字）')
  // 后端返回 JSON：{ filename, length, text }；兼容纯文本响应
  let text = raw
  if (raw.startsWith('{')) {
    try {
      const parsed = JSON.parse(raw) as { text?: string }
      text = (parsed.text ?? '').trim()
    } catch {
      text = raw
    }
  }
  if (!text) throw new Error('文件中未提取到文字内容（可能是扫描件，请先转文字）')
  return text
}
