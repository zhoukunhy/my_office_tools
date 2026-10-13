/**
 * 工具元数据配置
 * - categories: 工具分类
 * - tools: 全工具清单（含 P0 已上线 与 P1/P2 即将上线）
 * 统一在首页/列表页/搜索/收藏 复用
 */

export type ToolStatus = 'online' | 'coming'
export type ToolPriority = 'P0' | 'P1' | 'P2'

export interface ToolCategory {
  id: string
  name: string
  description: string
  icon: string // Element Plus 图标组件名
  color: string // 分类主色（用于图标背景渐变）
}

export interface ToolMeta {
  slug: string // 路由 slug，对应 /tool/:slug
  name: string
  description: string
  keywords: string[]
  categoryId: string
  icon: string
  status: ToolStatus
  priority: ToolPriority
  hot?: boolean // 首页热门推荐
}

export const categories: ToolCategory[] = [
  {
    id: 'pdf',
    name: 'PDF 工具',
    description: '合并、拆分、转图、删页旋转，本地安全处理',
    icon: 'Document',
    color: '#ef4444'
  },
  {
    id: 'image',
    name: '图片工具',
    description: '压缩、格式互转、批量处理，图片本地优化',
    icon: 'PictureFilled',
    color: '#f59e0b'
  },
  {
    id: 'text',
    name: '文本 / 文档',
    description: 'OCR、文本批量整理、文档对比、Markdown',
    icon: 'EditPen',
    color: '#10b981'
  },
  {
    id: 'av',
    name: '音视频 / GIF',
    description: '视频压缩、提取音频、转 GIF、屏幕录制',
    icon: 'VideoCamera',
    color: '#8b5cf6'
  },
  {
    id: 'dev',
    name: '开发 / 通用',
    description: 'JSON、时间戳、二维码、编码、进制转换',
    icon: 'Monitor',
    color: '#4f6eff'
  },
  {
    id: 'system',
    name: '系统效率',
    description: '常用效率软件推荐与下载指引',
    icon: 'Tools',
    color: '#64748b'
  }
]

export const tools: ToolMeta[] = [
  // ===== PDF 工具（P0） =====
  {
    slug: 'pdf-merge',
    name: 'PDF 合并',
    description: '多个 PDF 按顺序合并为单个文件',
    keywords: ['pdf', 'merge', '合并', '拼接'],
    categoryId: 'pdf',
    icon: 'Connection',
    status: 'online',
    priority: 'P0',
    hot: true
  },
  {
    slug: 'pdf-split',
    name: 'PDF 拆分',
    description: '按页码范围拆分 PDF 为多个文件',
    keywords: ['pdf', 'split', '拆分', '分割'],
    categoryId: 'pdf',
    icon: 'Scissor',
    status: 'online',
    priority: 'P0'
  },
  {
    slug: 'pdf-to-image',
    name: 'PDF 转图片',
    description: 'PDF 每页导出为 PNG / JPG 图片',
    keywords: ['pdf', 'image', '转图片', '导出'],
    categoryId: 'pdf',
    icon: 'Picture',
    status: 'online',
    priority: 'P0',
    hot: true
  },
  {
    slug: 'pdf-pages',
    name: 'PDF 删页 / 旋转',
    description: '删除指定页、旋转页面方向',
    keywords: ['pdf', 'delete', 'rotate', '删页', '旋转'],
    categoryId: 'pdf',
    icon: 'RefreshRight',
    status: 'online',
    priority: 'P0'
  },
  {
    slug: 'pdf-compress',
    name: 'PDF 压缩',
    description: '减小 PDF 体积（默认本地简化版，开启后端可获得强力压缩）',
    keywords: ['pdf', 'compress', '压缩'],
    categoryId: 'pdf',
    icon: 'Compress',
    status: 'online',
    priority: 'P1',
    hot: true
  },
  {
    slug: 'pdf-watermark',
    name: 'PDF 水印移除',
    description: '检测并移除 PDF 文本/注释/图片水印',
    keywords: ['pdf', 'watermark', '水印', '去除', '移除'],
    categoryId: 'pdf',
    icon: 'Stamp',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'word-to-pdf',
    name: 'Word 转 PDF',
    description: 'DOCX/DOC → PDF（需后端能力，支持批量）',
    keywords: ['word', 'docx', 'pdf', '转换', '转pdf'],
    categoryId: 'pdf',
    icon: 'Document',
    status: 'online',
    priority: 'P1',
    hot: true
  },
  {
    slug: 'pdf-to-word',
    name: 'PDF 转 Word',
    description: 'PDF → DOCX（需后端能力）',
    keywords: ['pdf', 'word', 'docx', '转换'],
    categoryId: 'pdf',
    icon: 'EditPen',
    status: 'online',
    priority: 'P1'
  },

  // ===== 图片工具（P0） =====
  {
    slug: 'image-compress',
    name: '图片压缩',
    description: '无损 / 可调质量压缩 PNG、JPG、WebP',
    keywords: ['image', 'compress', '压缩', '图片'],
    categoryId: 'image',
    icon: 'Compress',
    status: 'online',
    priority: 'P0',
    hot: true
  },
  {
    slug: 'image-convert',
    name: '图片格式转换',
    description: 'PNG / JPG / WebP 批量格式互转',
    keywords: ['image', 'convert', '格式', 'png', 'jpg', 'webp'],
    categoryId: 'image',
    icon: 'Refresh',
    status: 'online',
    priority: 'P0'
  },
  {
    slug: 'image-resize',
    name: '图片改尺寸 / 重命名',
    description: '批量调整尺寸与重命名，支持像素/百分比',
    keywords: ['image', 'resize', '尺寸', '重命名'],
    categoryId: 'image',
    icon: 'Crop',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'image-watermark',
    name: '图片水印',
    description: '为图片添加文字 / Logo 水印，支持平铺',
    keywords: ['image', 'watermark', '水印'],
    categoryId: 'image',
    icon: 'Stamp',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'image-stitch',
    name: '长图拼接',
    description: '多图纵向/横向拼接为单张长图',
    keywords: ['image', 'stitch', '拼接', '长图'],
    categoryId: 'image',
    icon: 'Sort',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'image-beautify',
    name: '截图美化',
    description: '圆角、边框、阴影、锐化与亮度调节',
    keywords: ['image', 'screenshot', '截图', '美化', '圆角', '阴影'],
    categoryId: 'image',
    icon: 'PictureRounded',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'image-bg-remove',
    name: 'AI 一键抠图',
    description: 'AI 去除图片背景，首次使用需下载模型，本地推理',
    keywords: ['image', 'ai', '抠图', '背景', 'bg'],
    categoryId: 'image',
    icon: 'MagicStick',
    status: 'online',
    priority: 'P1',
    hot: true
  },
  {
    slug: 'image-inpaint',
    name: '图片去文字 / 瑕疵修复',
    description: '涂抹去除文字或瑕疵，AI 自动修复（需后端）',
    keywords: ['image', 'inpaint', '去文字', '修复', '涂抹', '抠除'],
    categoryId: 'image',
    icon: 'Brush',
    status: 'online',
    priority: 'P2'
  },

  // ===== 文本 / 文档（P1） =====
  {
    slug: 'ocr',
    name: '图片 OCR 文字识别',
    description: '从截图 / 照片提取文字（支持本地降级 + 后端强化）',
    keywords: ['ocr', '文字', '识别', '提取'],
    categoryId: 'text',
    icon: 'Reading',
    status: 'online',
    priority: 'P1',
    hot: true
  },
  {
    slug: 'text-batch',
    name: '文本批量处理',
    description: '去空行、去换行、批量替换、大小写转换',
    keywords: ['text', 'batch', '文本', '替换', '去重', '去空行'],
    categoryId: 'text',
    icon: 'EditPen',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'markdown-editor',
    name: 'Markdown 编辑器',
    description: '在线编辑、预览、导出 PDF',
    keywords: ['markdown', '编辑', '预览', '导出', 'pdf'],
    categoryId: 'text',
    icon: 'Document',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'doc-diff',
    name: '文档对比',
    description: 'Word / PDF / 文本差异对比',
    keywords: ['diff', '对比', '差异', 'word', '文本', 'pdf'],
    categoryId: 'text',
    icon: 'DCaret',
    status: 'online',
    priority: 'P2'
  },

  // ===== 音视频 / GIF（P2） =====
  {
    slug: 'video-compress',
    name: '视频压缩',
    description: '减小视频体积（后端 ffmpeg 能力）',
    keywords: ['video', 'compress', '视频', '压缩', 'ffmpeg', '减小'],
    categoryId: 'av',
    icon: 'VideoCamera',
    status: 'online',
    priority: 'P2'
  },
  {
    slug: 'video-to-audio',
    name: '视频提取音频',
    description: '从视频提取 MP3 / WAV / AAC 音频',
    keywords: ['video', 'audio', 'mp3', '提取', 'wav', 'aac', '录音'],
    categoryId: 'av',
    icon: 'Headset',
    status: 'online',
    priority: 'P2'
  },
  {
    slug: 'video-to-gif',
    name: '视频转 GIF',
    description: '截取视频片段转 GIF 动图（纯前端）',
    keywords: ['video', 'gif', '动图', '截图', '动画'],
    categoryId: 'av',
    icon: 'VideoPlay',
    status: 'online',
    priority: 'P2'
  },

  // ===== 开发 / 通用（P0） =====
  {
    slug: 'json-format',
    name: 'JSON 格式化',
    description: 'JSON 格式化 / 压缩 / 校验',
    keywords: ['json', 'format', '格式化', '压缩'],
    categoryId: 'dev',
    icon: 'Coin',
    status: 'online',
    priority: 'P0',
    hot: true
  },
  {
    slug: 'qrcode',
    name: '二维码生成 / 解析',
    description: '生成二维码、解析图片二维码',
    keywords: ['qrcode', '二维码', '生成', '解析'],
    categoryId: 'dev',
    icon: 'Grid',
    status: 'online',
    priority: 'P0'
  },
  {
    slug: 'timestamp',
    name: '时间戳转换',
    description: '时间戳 / 日期互转，支持时区',
    keywords: ['timestamp', '时间戳', '日期', 'date', '时区'],
    categoryId: 'dev',
    icon: 'Timer',
    status: 'online',
    priority: 'P0'
  },
  {
    slug: 'base-convert',
    name: '进制 / 单位换算',
    description: '进制转换、常用单位换算',
    keywords: ['进制', 'base', '单位', '换算', '二进制', '十六进制'],
    categoryId: 'dev',
    icon: 'Histogram',
    status: 'online',
    priority: 'P1'
  },
  {
    slug: 'password-gen',
    name: '随机密码生成',
    description: '生成强随机密码与加密小工具',
    keywords: ['password', '密码', '生成', 'base64', 'md5', 'sha256', '哈希'],
    categoryId: 'dev',
    icon: 'Lock',
    status: 'online',
    priority: 'P1'
  }
]

/** 按 slug 快速查找 */
export function getToolBySlug(slug: string): ToolMeta | undefined {
  return tools.find((t) => t.slug === slug)
}

/** 按分类取工具列表 */
export function getToolsByCategory(categoryId: string): ToolMeta[] {
  return tools.filter((t) => t.categoryId === categoryId)
}

/** 取热门工具 */
export function getHotTools(): ToolMeta[] {
  return tools.filter((t) => t.hot)
}
