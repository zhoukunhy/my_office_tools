import { defineStore } from 'pinia'
import { tools as allTools } from '@/config/tools'

/** 本机后端默认地址（不含 /api 后缀，请求时由 resolveApiUrl 自动拼接） */
export const DEFAULT_BACKEND_BASE = 'http://127.0.0.1:8000'

interface PreferenceState {
  favorites: string[] // tool slug
  recent: string[] // 最近使用 tool slug（按时间倒序，最多 12 条）
  /** 后端配置：是否启用后端加速功能（PDF压缩/互转/OCR） */
  backendEnabled: boolean
  /** 后端 API 地址；空字符串 = 使用同源相对路径 /api */
  backendBaseUrl: string
  /** 用户是否在 /me 页面主动保存过后端配置（用于区分"从未配置"与"配置为空"） */
  backendConfigured: boolean
}

const RECENT_MAX = 12

export const usePreferenceStore = defineStore('preference', {
  state: (): PreferenceState => ({
    favorites: [],
    recent: [],
    backendEnabled: true,
    backendBaseUrl: DEFAULT_BACKEND_BASE,
    backendConfigured: false
  }),
  getters: {
    favoriteTools: (s) => allTools.filter((t) => s.favorites.includes(t.slug)),
    recentTools: (s) =>
      s.recent
        .map((slug) => allTools.find((t) => t.slug === slug))
        .filter((t): t is NonNullable<typeof t> => Boolean(t))
  },
  persist: {
    key: 'suyong-preference-v2'
  },
  actions: {
    init() {
      // 后端加速默认配置迁移：老版本 localStorage 里 enabled=false 且 base 为空（从未配置过）
      // 时，自动填入本机默认地址并启用，免去手动填写。
      if (!this.backendConfigured) {
        this.backendEnabled = true
        if (!this.backendBaseUrl) this.backendBaseUrl = DEFAULT_BACKEND_BASE
      }
      // 兼容旧 localStorage key
      if (!this.favorites.length) {
        try {
          const v = localStorage.getItem('suyong-favorites')
          if (v) this.favorites = JSON.parse(v)
        } catch {
          // ignore
        }
      }
      if (!this.recent.length) {
        try {
          const v = localStorage.getItem('suyong-recent')
          if (v) this.recent = JSON.parse(v)
        } catch {
          // ignore
        }
      }
    },
    isFavorite(slug: string) {
      return this.favorites.includes(slug)
    },
    toggleFavorite(slug: string) {
      if (this.favorites.includes(slug)) {
        this.favorites = this.favorites.filter((s) => s !== slug)
      } else {
        this.favorites.push(slug)
      }
    },
    pushRecent(slug: string) {
      this.recent = [slug, ...this.recent.filter((s) => s !== slug)].slice(0, RECENT_MAX)
    },
    setBackend(baseUrl: string, enabled: boolean) {
      // 规范化：去尾部斜杠；去掉误填的尾部 /api（resolveApiUrl 会自动拼接 /api 前缀）
      this.backendBaseUrl = (baseUrl || '')
        .trim()
        .replace(/\/+$/, '')
        .replace(/\/api$/i, '')
      this.backendEnabled = enabled
      this.backendConfigured = true
    }
  }
})
