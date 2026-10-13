/** AI 生成 PPT：前后端共享的数据结构 */

export type SlideLayout = 'cover' | 'toc' | 'content' | 'two-column' | 'quote' | 'end'

export interface SlideItem {
  title: string
  detail: string
}

export interface Slide {
  index: number
  layout: SlideLayout
  title: string
  subtitle: string
  items: SlideItem[]
  notes: string
  /** 本地已被用户/AI 编辑过，轮询合入时保留本地版本 */
  _edited?: boolean
}

export interface OutlinePage {
  index: number
  title: string
  layout: SlideLayout | string
  brief: string
}

export interface DeckOutline {
  title: string
  subtitle: string
  pages: OutlinePage[]
}

export interface PptTheme {
  primary: string
  bg: string
  text: string
  mute: string
  font: 'sans' | 'serif'
}

export interface TaskPage {
  index: number
  status: 'running' | 'done' | 'failed'
  data: Slide | null
  error: string | null
}

export interface PptTask {
  task_id: string
  status: 'running' | 'done'
  total: number
  completed: number
  failed: number
  pages: TaskPage[]
}

export const LAYOUT_LABELS: Record<SlideLayout, string> = {
  cover: '封面',
  toc: '目录',
  content: '内容页',
  'two-column': '双栏',
  quote: '金句',
  end: '结束页'
}

export const THEME_PRESETS: { name: string; theme: PptTheme }[] = [
  { name: '商务蓝', theme: { primary: '#2563eb', bg: '#ffffff', text: '#1e293b', mute: '#64748b', font: 'sans' } },
  { name: '深邃夜', theme: { primary: '#38bdf8', bg: '#0f172a', text: '#e2e8f0', mute: '#94a3b8', font: 'sans' } },
  { name: '暖橙', theme: { primary: '#ea580c', bg: '#fffbeb', text: '#292524', mute: '#78716c', font: 'sans' } },
  { name: '翡翠', theme: { primary: '#059669', bg: '#ffffff', text: '#1c1917', mute: '#57534e', font: 'sans' } },
  { name: '典雅紫', theme: { primary: '#7c3aed', bg: '#faf5ff', text: '#2e1065', mute: '#6b7280', font: 'serif' } },
  { name: '水墨灰', theme: { primary: '#374151', bg: '#f9fafb', text: '#111827', mute: '#6b7280', font: 'serif' } }
]
