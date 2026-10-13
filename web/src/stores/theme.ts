import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'
export type FontScale = 'sm' | 'base' | 'lg' | 'xl'

// 主题色预设：主色 + 深色模式下的背景/主色偏移
export interface ThemeColorPreset {
  id: string
  label: string
  primary: string
  primarySoft: string // 浅底色（浅色模式）
  gradientFrom: string
  gradientTo: string
}

export const THEME_COLOR_PRESETS: ThemeColorPreset[] = [
  {
    id: 'indigo',
    label: '星辰蓝',
    primary: '#4f6eff',
    primarySoft: 'rgba(79,110,255,0.12)',
    gradientFrom: '#4f6eff',
    gradientTo: '#8a6dff'
  },
  {
    id: 'mint',
    label: '薄荷绿',
    primary: '#13b997',
    primarySoft: 'rgba(19,185,151,0.12)',
    gradientFrom: '#13b997',
    gradientTo: '#36d1a5'
  },
  {
    id: 'coral',
    label: '暖阳橙',
    primary: '#ff7a59',
    primarySoft: 'rgba(255,122,89,0.12)',
    gradientFrom: '#ff7a59',
    gradientTo: '#ffa970'
  },
  {
    id: 'rose',
    label: '玫瑰粉',
    primary: '#ef4f88',
    primarySoft: 'rgba(239,79,136,0.12)',
    gradientFrom: '#ef4f88',
    gradientTo: '#ff80a8'
  },
  {
    id: 'obsidian',
    label: '黑曜紫',
    primary: '#8b5cf6',
    primarySoft: 'rgba(139,92,246,0.14)',
    gradientFrom: '#8b5cf6',
    gradientTo: '#5b8cff'
  },
  {
    id: 'ink',
    label: '墨黑（纯极简）',
    primary: '#111827',
    primarySoft: 'rgba(17,24,39,0.08)',
    gradientFrom: '#111827',
    gradientTo: '#374151'
  }
]

const STORAGE_KEY = 'suyong-theme-v2'

interface ThemeState {
  mode: ThemeMode
  colorId: string
  fontSize: FontScale
}

/**
 * 主题 store - 浅/深色 + 主题色 + 字号 三档可配置，全部持久化
 */
export const useThemeStore = defineStore('theme', {
  state: (): ThemeState => ({
    mode: 'light',
    colorId: 'indigo',
    fontSize: 'base'
  }),
  getters: {
    isDark: (s) => s.mode === 'dark',
    color(state): ThemeColorPreset {
      return THEME_COLOR_PRESETS.find((p) => p.id === state.colorId) || THEME_COLOR_PRESETS[0]
    }
  },
  persist: {
    key: STORAGE_KEY
  },
  actions: {
    init() {
      // 兼容旧存储，仅首次未持久化时使用（pinia-plugin-persistedstate v4 暴露 $persisted）
      const legacy = localStorage.getItem('suyong-theme') as ThemeMode | null
      try {
        const vAny = this as unknown as Record<string, unknown>
        const already =
          typeof vAny.$persisted === 'boolean' ? vAny.$persisted : typeof vAny.$persist === 'object'
        if (legacy && !already) this.mode = legacy
      } catch {
        // ignore
      }
      if (this.mode !== 'light' && this.mode !== 'dark' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
        this.mode = 'dark'
      }
      this.apply()
    },
    toggleMode() {
      this.mode = this.mode === 'dark' ? 'light' : 'dark'
      this.apply()
    },
    setColor(id: string) {
      if (!THEME_COLOR_PRESETS.some((p) => p.id === id)) return
      this.colorId = id
      this.apply()
    },
    setFontSize(fs: FontScale) {
      this.fontSize = fs
      this.apply()
    },
    apply() {
      const html = document.documentElement
      // 深浅色
      if (this.mode === 'dark') html.classList.add('dark')
      else html.classList.remove('dark')

      // 主题色通过 CSS 变量下发（覆盖 main.css 默认值）
      const c = this.color
      const dark = this.mode === 'dark'
      const primary = c.primary
      const hover = this.shade(primary, -12)
      const pressed = this.shade(primary, -22)
      const soft = c.primarySoft
      const bg = dark ? '#0b1220' : '#f7f8fb'
      const card = dark ? '#121b2d' : '#ffffff'
      const text = dark ? '#e6e9f2' : '#161b2c'
      const textSoft = dark ? '#c7cde0' : '#3e4560'
      const textMute = dark ? '#8a92ab' : '#7a8095'
      const border = dark ? '#1f2a44' : '#e6e8ef'
      const bgSoft = dark ? '#162039' : '#eef1f7'

      const vars: Record<string, string> = {
        '--c-primary': primary,
        '--c-primary-hover': hover,
        '--c-primary-pressed': pressed,
        '--c-primary-soft': soft,
        '--c-bg': bg,
        '--c-bg-soft': bgSoft,
        '--c-card': card,
        '--c-text': text,
        '--c-text-soft': textSoft,
        '--c-text-mute': textMute,
        '--c-border': border,
        '--grad-hero': `linear-gradient(135deg, ${c.gradientFrom}, ${c.gradientTo})`
      }
      Object.entries(vars).forEach(([k, v]) => html.style.setProperty(k, v))

      // 字号
      const fontScales: Record<FontScale, string> = {
        sm: '14px',
        base: '15px',
        lg: '16.5px',
        xl: '18px'
      }
      html.style.fontSize = fontScales[this.fontSize]
    },
    /** 简单的明度偏移算法：正数变浅，负数变深（hex → rgb 线性插值） */
    shade(hex: string, percent: number) {
      const c = hex.replace('#', '')
      const num = parseInt(c.length === 3 ? c.split('').map((x) => x + x).join('') : c, 16)
      let r = (num >> 16) & 0xff
      let g = (num >> 8) & 0xff
      let b = num & 0xff
      const t = percent < 0 ? 0 : 255
      const p = Math.abs(percent) / 100
      r = Math.round((t - r) * p) + r
      g = Math.round((t - g) * p) + g
      b = Math.round((t - b) * p) + b
      return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`
    }
  }
})
