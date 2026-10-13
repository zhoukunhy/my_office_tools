/**
 * PDF 渲染工具：基于 pdfjs-dist
 * 仅用于"读取预览/栅格化为图片"，结构编辑走 pdf-lib
 *
 * 说明：pdfjs-dist 导出的 PDFDocumentProxy 接口含 #private 品牌字段，
 * 与 getDocument() 实际返回的结构类型不兼容，故这里用最小结构接口收口。
 */
import * as pdfjsLib from 'pdfjs-dist'
// Vite 把 worker 文件作为 URL 资源
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

export interface PdfViewport {
  width: number
  height: number
}
export interface PdfPageProxy {
  getViewport(params: { scale: number }): PdfViewport
  render(params: { canvasContext: CanvasRenderingContext2D; viewport: PdfViewport }): {
    promise: Promise<void>
  }
}
export interface PdfDoc {
  readonly numPages: number
  getPage(pageNumber: number): Promise<PdfPageProxy>
  destroy(): Promise<void>
}

export async function loadPdf(data: ArrayBuffer): Promise<PdfDoc> {
  const loadingTask = pdfjsLib.getDocument({ data })
  return loadingTask.promise as Promise<PdfDoc>
}

/** 将指定页渲染为 canvas */
export async function renderPageToCanvas(
  pdf: PdfDoc,
  pageNum: number,
  scale = 1.5
): Promise<HTMLCanvasElement> {
  const page = await pdf.getPage(pageNum)
  const viewport = page.getViewport({ scale })
  const canvas = document.createElement('canvas')
  canvas.width = viewport.width
  canvas.height = viewport.height
  const ctx = canvas.getContext('2d')!
  await page.render({ canvasContext: ctx, viewport }).promise
  return canvas
}

/** 渲染指定页为 Blob（指定格式与质量） */
export async function renderPageToBlob(
  pdf: PdfDoc,
  pageNum: number,
  type: 'image/png' | 'image/jpeg',
  scale = 2,
  quality = 0.92
): Promise<Blob> {
  const canvas = await renderPageToCanvas(pdf, pageNum, scale)
  return await new Promise<Blob>((resolve) => {
    canvas.toBlob((blob) => resolve(blob!), type, quality)
  })
}
