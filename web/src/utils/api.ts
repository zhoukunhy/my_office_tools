/**
 * 后端 API 地址解析 + 常用 fetch 包装
 * 规则：
 *  1) 若 pref.backendEnabled=false，则 apiBase 返回 ''（表示：不允许使用任何需要后端的功能）
 *  2) 若 enabled 且 backendBaseUrl = ''：返回 ''（调用方用 /api 相对路径，走 vite 代理或同源部署）
 *  3) 若 enabled 且 backendBaseUrl = 'https://xxx'：返回 'https://xxx'（调用方拼接 /api/** 即可跨域直连）
 */

import { usePreferenceStore } from '@/stores/preference'

export interface BackendStatus {
  enabled: boolean
  base: string // 空字符串 → 使用同源 /api
}

export function getBackendStatus(): BackendStatus {
  try {
    const pref = usePreferenceStore()
    return {
      enabled: pref.backendEnabled,
      base: pref.backendBaseUrl?.trim() || ''
    }
  } catch {
    return { enabled: false, base: '' }
  }
}

/** 真正用于请求的完整前缀。当禁用后端时返回空字符串，调用方应提示未开启。 */
export function getApiBaseOrNull(): string | null {
  const s = getBackendStatus()
  if (!s.enabled) return null
  return s.base
}

/** 拼接最终请求 URL。当后端未开启时返回 null。 */
export function resolveApiUrl(path: string): string | null {
  const base = getApiBaseOrNull()
  if (base === null) return null
  const p = path.startsWith('/') ? path : `/${path}`
  return `${base}/api${p}`
}

/**
 * 向后端发送 JSON POST 请求（AI PPT 等新接口使用）。
 * 当后端禁用时返回 { ok:false, needBackend:true }。
 */
export async function backendPostJson(
  path: string,
  body: unknown,
  opts: { timeoutMs?: number } = {}
): Promise<{ ok: true; data: unknown } | { ok: false; needBackend?: boolean; message: string }> {
  const url = resolveApiUrl(path)
  if (!url) {
    return { ok: false, needBackend: true, message: '未开启后端加速功能' }
  }
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs || 300_000)
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal
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
  } finally {
    clearTimeout(timer)
  }
}

/** 向后端发送 GET 请求（任务状态轮询等）。 */
export async function backendGetJson(
  path: string,
  opts: { timeoutMs?: number } = {}
): Promise<{ ok: true; data: unknown } | { ok: false; needBackend?: boolean; message: string }> {
  const url = resolveApiUrl(path)
  if (!url) {
    return { ok: false, needBackend: true, message: '未开启后端加速功能' }
  }
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs || 30_000)
  try {
    const resp = await fetch(url, { signal: controller.signal })
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
  } finally {
    clearTimeout(timer)
  }
}

/**
 * 向后端发送 multipart/form-data 请求。
 * 当后端禁用时返回 { ok:false, needBackend:true }，UI 可据此弹出提醒。
 */
export async function backendFetch(
  path: string,
  body: FormData,
  opts: { timeoutMs?: number } = {}
): Promise<
  | { ok: true; blob: Blob; contentType: string; filename?: string }
  | { ok: false; needBackend?: boolean; message: string }
> {
  const url = resolveApiUrl(path)
  if (!url) {
    return { ok: false, needBackend: true, message: '未开启后端加速功能' }
  }
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs || 120_000)
  try {
    const resp = await fetch(url, { method: 'POST', body, signal: controller.signal })
    if (!resp.ok) {
      const msg = await resp.text().catch(() => '')
      return {
        ok: false,
        message: `HTTP ${resp.status}${msg ? '：' + msg.slice(0, 200) : ''}`
      }
    }
    const blob = await resp.blob()
    const disp = resp.headers.get('Content-Disposition') || ''
    const filename = (() => {
      const m = /filename\*=UTF-8''([^;]+)/i.exec(disp)
      if (m) return decodeURIComponent(m[1])
      const m2 = /filename="?([^"]+)"?/i.exec(disp)
      if (m2) return m2[1]
      return undefined
    })()
    return {
      ok: true,
      blob,
      contentType: resp.headers.get('Content-Type') || blob.type,
      filename
    }
  } catch (err) {
    return {
      ok: false,
      message: err instanceof Error ? err.message : '请求失败'
    }
  } finally {
    clearTimeout(timer)
  }
}
