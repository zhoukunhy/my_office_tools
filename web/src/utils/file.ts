/**
 * 文件处理工具：本地读取、下载、批量打包
 * 全部在浏览器本地完成，无网络上传
 */
import JSZip from 'jszip'

/** 字节大小可读化 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 2)} ${units[i]}`
}

/** 读取 File 为 ArrayBuffer */
export function readFileAsArrayBuffer(file: File | Blob): Promise<ArrayBuffer> {
  return file.arrayBuffer()
}

/** 触发浏览器下载（Blob） */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Uint8Array 转 Blob（兼容 TS5.9 的 ArrayBufferLike 类型） */
export function bytesToBlob(bytes: Uint8Array, type: string): Blob {
  // slice() 返回独立副本，其 buffer 为 ArrayBuffer
  return new Blob([bytes.slice().buffer as ArrayBuffer], { type })
}

/** 将多个文件打包为 zip 下载 */
export async function downloadFilesAsZip(
  files: { blob: Blob; name: string }[],
  zipName = 'suyong-export.zip'
) {
  const zip = new JSZip()
  for (const f of files) {
    zip.file(f.name, f.blob)
  }
  const content = await zip.generateAsync({ type: 'blob' })
  downloadBlob(content, zipName)
}

/** 从文件名取扩展名（小写，不含点） */
export function getExt(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

/** 替换扩展名 */
export function replaceExt(filename: string, newExt: string): string {
  const base = filename.replace(/\.[^.]+$/, '')
  return `${base}.${newExt}`
}

/** 生成不带扩展名的文件名序号副本 */
export function baseName(filename: string): string {
  return filename.replace(/\.[^.]+$/, '')
}
