/**
 * 图片处理工具：本地解码、Canvas 重编码、压缩
 */
export type ImgFormat = 'png' | 'jpeg' | 'webp'

export interface LoadedImage {
  img: HTMLImageElement
  width: number
  height: number
}

export function loadImage(file: File | Blob): Promise<LoadedImage> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const result = { img, width: img.naturalWidth, height: img.naturalHeight }
      URL.revokeObjectURL(url)
      resolve(result)
    }
    img.onerror = (e) => {
      URL.revokeObjectURL(url)
      reject(e)
    }
    img.src = url
  })
}

const MIME: Record<ImgFormat, string> = {
  png: 'image/png',
  jpeg: 'image/jpeg',
  webp: 'image/webp'
}

/** 通过 Canvas 重编码图片，可指定格式与质量 */
export function encodeImage(
  img: HTMLImageElement,
  format: ImgFormat,
  quality = 0.92,
  maxW?: number,
  maxH?: number
): Promise<Blob> {
  let w = img.naturalWidth
  let h = img.naturalHeight
  if (maxW && w > maxW) {
    h = Math.round((h * maxW) / w)
    w = maxW
  }
  if (maxH && h > maxH) {
    w = Math.round((w * maxH) / h)
    h = maxH
  }
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')!
  // 白底，防止透明 PNG 转 JPG 出现黑底
  if (format === 'jpeg') {
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, w, h)
  }
  ctx.drawImage(img, 0, 0, w, h)
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('编码失败'))),
      MIME[format],
      quality
    )
  })
}

/** 检测浏览器是否支持 webp 编码 */
export function supportsWebp(): boolean {
  const c = document.createElement('canvas')
  return c.toDataURL('image/webp').startsWith('data:image/webp')
}

/** 等比计算目标尺寸（返回实际目标宽高） */
export function fitSize(
  w: number,
  h: number,
  mode: 'percent' | 'width' | 'height' | 'exact',
  value: number,
  value2 = 0,
  keepRatio = true
): { w: number; h: number } {
  if (mode === 'percent') {
    const s = Math.max(1, value) / 100
    return { w: Math.max(1, Math.round(w * s)), h: Math.max(1, Math.round(h * s)) }
  }
  if (mode === 'width') return { w: Math.max(1, Math.round(value)), h: Math.max(1, Math.round((h * value) / w)) }
  if (mode === 'height') return { w: Math.max(1, Math.round((w * value) / h)), h: Math.max(1, Math.round(value)) }
  // exact
  if (keepRatio) {
    const r = Math.min(value / w, value2 / h)
    return { w: Math.max(1, Math.round(w * r)), h: Math.max(1, Math.round(h * r)) }
  }
  return { w: Math.max(1, Math.round(value)), h: Math.max(1, Math.round(value2)) }
}

/**
 * PNG 量化降色（智能压缩）
 * 使用 image-q 调色板量化 + 可选抖动，256 色内体积可降 50%+
 */
export async function quantizeCanvas(
  source: HTMLCanvasElement,
  colors = 256,
  dither: 'none' | 'floyd-steinberg' = 'floyd-steinberg'
): Promise<HTMLCanvasElement> {
  const { buildPalette, applyPalette, utils } = await import('image-q')
  const ctx = source.getContext('2d')!
  const imageData = ctx.getImageData(0, 0, source.width, source.height)
  const pc = utils.PointContainer.fromImageData(imageData)
  const palette = await buildPalette([pc], {
    paletteQuantization: 'wuquant',
    colors: Math.min(256, Math.max(2, colors))
  })
  const out = await applyPalette(pc, palette, {
    imageQuantization: dither === 'none' ? 'nearest' : 'floyd-steinberg'
  })
  const canvas = document.createElement('canvas')
  canvas.width = source.width
  canvas.height = source.height
  const octx = canvas.getContext('2d')!
  const rgba = new Uint8ClampedArray(out.toUint8Array())
  octx.putImageData(new ImageData(rgba, source.width, source.height), 0, 0)
  return canvas
}

/** 在 canvas 上执行 3x3 卷积（用于锐化） */
export function convolve(
  source: HTMLCanvasElement,
  kernel: number[],
  divisor = 1,
  offset = 0
): HTMLCanvasElement {
  const w = source.width
  const h = source.height
  const src = source.getContext('2d')!.getImageData(0, 0, w, h)
  const out = new ImageData(w, h)
  const s = src.data
  const d = out.data
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let r = 0,
        g = 0,
        b = 0
      for (let ky = -1; ky <= 1; ky++) {
        const yy = Math.min(h - 1, Math.max(0, y + ky))
        for (let kx = -1; kx <= 1; kx++) {
          const xx = Math.min(w - 1, Math.max(0, x + kx))
          const i = (yy * w + xx) * 4
          const kv = kernel[(ky + 1) * 3 + (kx + 1)]
          r += s[i] * kv
          g += s[i + 1] * kv
          b += s[i + 2] * kv
        }
      }
      const oi = (y * w + x) * 4
      d[oi] = Math.min(255, Math.max(0, r / divisor + offset))
      d[oi + 1] = Math.min(255, Math.max(0, g / divisor + offset))
      d[oi + 2] = Math.min(255, Math.max(0, b / divisor + offset))
      d[oi + 3] = s[oi + 3]
    }
  }
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  canvas.getContext('2d')!.putImageData(out, 0, 0)
  return canvas
}
