/**
 * PPT 导出：把编辑后的页面 JSON 通过 pptxgenjs 生成真 .pptx 文件
 * 设计基准 16:9（13.333 x 7.5 英寸），与前端 SlideCanvas 预览保持一致的版式映射
 */
import PptxGenJS from 'pptxgenjs'
import type { PptTheme, Slide } from '@/types/aiPpt'

const PAGE_W = 13.333
const PAGE_H = 7.5

function hex(color: string): string {
  return color.replace('#', '').toUpperCase()
}

function addAccentBar(slide: PptxGenJS.Slide, theme: PptTheme, x: number, y: number, w = 0.6) {
  slide.addShape('rect', { x, y, w, h: 0.07, fill: { color: hex(theme.primary) } })
}

function addHeader(slide: PptxGenJS.Slide, s: Slide, theme: PptTheme) {
  addAccentBar(slide, theme, 0.55, 0.62)
  slide.addText(s.title || '', {
    x: 0.55,
    y: 0.72,
    w: PAGE_W - 1.1,
    h: 0.7,
    fontSize: 26,
    bold: true,
    color: hex(theme.text),
    fontFace: theme.font === 'serif' ? 'Georgia' : 'Microsoft YaHei'
  })
}

function addItems(slide: PptxGenJS.Slide, s: Slide, theme: PptTheme, twoCol: boolean) {
  const items = s.items.length ? s.items : [{ title: '', detail: '' }]
  const cols = twoCol ? 2 : 1
  const colW = (PAGE_W - 1.1 - (twoCol ? 0.4 : 0)) / cols
  const rows = Math.ceil(items.length / cols)
  const rowH = Math.min(1.35, 5.4 / Math.max(1, rows))
  items.forEach((it, i) => {
    const col = i % cols
    const row = Math.floor(i / cols)
    const x = 0.55 + col * (colW + 0.4)
    const y = 1.75 + row * rowH
    slide.addShape('rect', { x, y: y + 0.08, w: 0.09, h: 0.32, fill: { color: hex(theme.primary) } })
    if (it.title) {
      slide.addText(it.title, { x: x + 0.22, y, w: colW - 0.22, h: 0.5, fontSize: 15, bold: true, color: hex(theme.text), fontFace: theme.font === 'serif' ? 'Georgia' : 'Microsoft YaHei' })
    }
    if (it.detail) {
      slide.addText(it.detail, { x: x + 0.22, y: y + 0.46, w: colW - 0.22, h: rowH - 0.5, fontSize: 11, color: hex(theme.mute), fontFace: theme.font === 'serif' ? 'Georgia' : 'Microsoft YaHei' })
    }
  })
}

function buildSlide(pptx: PptxGenJS, s: Slide, theme: PptTheme) {
  const slide = pptx.addSlide()
  const bg = hex(theme.bg)
  slide.background = { color: bg }
  const sans = theme.font === 'serif' ? 'Georgia' : 'Microsoft YaHei'

  switch (s.layout) {
    case 'cover':
    case 'end': {
      slide.addShape('rect', { x: 0, y: 0, w: PAGE_W, h: PAGE_H, fill: { color: hex(theme.primary) } })
      slide.addText(s.title || '', {
        x: 1.2,
        y: 2.5,
        w: PAGE_W - 2.4,
        h: 1.4,
        fontSize: 40,
        bold: true,
        color: 'FFFFFF',
        align: 'center',
        fontFace: sans
      })
      if (s.subtitle) {
        slide.addText(s.subtitle, { x: 1.2, y: 4.1, w: PAGE_W - 2.4, h: 0.7, fontSize: 16, color: 'E8F0FF', align: 'center', fontFace: sans })
      }
      break
    }
    case 'toc': {
      addHeader(slide, s, theme)
      addItems(slide, s, theme, s.items.length > 5)
      break
    }
    case 'two-column': {
      addHeader(slide, s, theme)
      addItems(slide, s, theme, true)
      break
    }
    case 'quote': {
      slide.addShape('rect', { x: 0.9, y: 1.4, w: 0.1, h: PAGE_H - 2.8, fill: { color: hex(theme.primary) } })
      slide.addText(s.title || '', {
        x: 1.5,
        y: 2.0,
        w: PAGE_W - 2.7,
        h: 2.4,
        fontSize: 28,
        italic: true,
        color: hex(theme.text),
        fontFace: sans,
        valign: 'middle'
      })
      if (s.subtitle) {
        slide.addText(s.subtitle, { x: 1.5, y: 4.7, w: PAGE_W - 2.7, h: 0.5, fontSize: 13, color: hex(theme.mute), fontFace: sans })
      }
      break
    }
    default: {
      addHeader(slide, s, theme)
      addItems(slide, s, theme, false)
    }
  }

  if (s.notes) slide.addNotes(s.notes)
}

export async function exportPptx(slides: Slide[], theme: PptTheme, deckTitle: string): Promise<string> {
  const pptx = new PptxGenJS()
  pptx.defineLayout({ name: 'W16x9', width: PAGE_W, height: PAGE_H })
  pptx.layout = 'W16x9'
  pptx.title = deckTitle || '演示文稿'
  const sorted = [...slides].sort((a, b) => a.index - b.index)
  for (const s of sorted) {
    buildSlide(pptx, s, theme)
  }
  const fileName = `${(deckTitle || '演示文稿').replace(/[\\/:*?"<>|]/g, '')}.pptx`
  await pptx.writeFile({ fileName })
  return fileName
}
