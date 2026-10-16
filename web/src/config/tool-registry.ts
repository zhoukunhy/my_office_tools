import type { Component } from 'vue'
import { defineAsyncComponent } from 'vue'
import { tools } from '@/config/tools'

/**
 * 工具 slug -> 实现组件 的懒加载映射
 * 仅 status=online 的工具在此注册组件
 */
const registry: Record<string, () => Promise<{ default: Component }>> = {
  'pdf-merge': () => import('@/views/tools/PdfMergeView.vue'),
  'pdf-split': () => import('@/views/tools/PdfSplitView.vue'),
  'pdf-to-image': () => import('@/views/tools/PdfToImageView.vue'),
  'pdf-pages': () => import('@/views/tools/PdfPagesView.vue'),
  'pdf-compress': () => import('@/views/tools/PdfCompressView.vue'),
  'pdf-watermark': () => import('@/views/tools/PdfWatermarkView.vue'),
  'word-to-pdf': () => import('@/views/tools/WordToPdfView.vue'),
  'pdf-to-word': () => import('@/views/tools/PdfToWordView.vue'),
  'text-batch': () => import('@/views/tools/TextBatchView.vue'),
  'markdown-editor': () => import('@/views/tools/MarkdownEditorView.vue'),
  'base-convert': () => import('@/views/tools/BaseConvertView.vue'),
  'password-gen': () => import('@/views/tools/PasswordGenView.vue'),
  'image-compress': () => import('@/views/tools/ImageCompressView.vue'),
  'image-convert': () => import('@/views/tools/ImageConvertView.vue'),
  'image-resize': () => import('@/views/tools/ImageResizeView.vue'),
  'image-watermark': () => import('@/views/tools/ImageWatermarkView.vue'),
  'image-stitch': () => import('@/views/tools/ImageStitchView.vue'),
  'image-beautify': () => import('@/views/tools/ImageBeautifyView.vue'),
  'image-bg-remove': () => import('@/views/tools/ImageBgRemoveView.vue'),
  'image-inpaint': () => import('@/views/tools/ImageInpaintView.vue'),
  'json-format': () => import('@/views/tools/JsonFormatView.vue'),
  qrcode: () => import('@/views/tools/QrcodeView.vue'),
  timestamp: () => import('@/views/tools/TimestampView.vue'),
  'doc-diff': () => import('@/views/tools/DocDiffView.vue'),
  'ocr': () => import('@/views/tools/OcrView.vue'),
  'video-compress': () => import('@/views/tools/VideoCompressView.vue'),
  'video-to-audio': () => import('@/views/tools/VideoToAudioView.vue'),
  'video-to-gif': () => import('@/views/tools/VideoToGifView.vue'),
}

export function resolveToolComponent(slug: string): Component | null {
  const loader = registry[slug]
  if (!loader) return null
  return defineAsyncComponent(loader)
}

/** 当前已注册（online）的 slug 集合，用于校验 */
export const onlineSlugs = new Set(tools.filter((t) => t.status === 'online').map((t) => t.slug))
