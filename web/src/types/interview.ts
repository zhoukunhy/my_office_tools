/**
 * 面试题库类型定义
 */

/** 题目分类（技术领域大分类） */
export type InterviewCategory =
  | 'frontend' // 前端
  | 'backend' // 后端
  | 'database' // 数据库
  | 'algorithm' // 数据结构与算法
  | 'ai' // AI / 大模型
  | 'os' // 操作系统 / 计算机基础
  | 'network' // 网络
  | 'devops' // 运维 / DevOps
  | 'other' // 其他

/** 分类元数据 */
export interface InterviewCategoryMeta {
  id: InterviewCategory
  name: string
  color: string
  icon: string
  /** 二级标签（vue/react 等） */
  tags: string[]
}

export const INTERVIEW_CATEGORIES: InterviewCategoryMeta[] = [
  { id: 'frontend', name: '前端', color: '#4f6eff', icon: 'Monitor', tags: ['Vue', 'React', 'Angular', 'JavaScript', 'TypeScript', 'HTML', 'CSS', '工程化', 'Webpack', 'Vite', '性能优化'] },
  { id: 'backend', name: '后端', color: '#10b981', icon: 'Server', tags: ['Java', 'Go', 'C#', 'Node.js', 'Python', 'C/C++', 'Spring', 'Gin', '.NET', '微服务', '分布式'] },
  { id: 'database', name: '数据库', color: '#f59e0b', icon: 'Coin', tags: ['MySQL', 'MongoDB', 'Redis', 'PostgreSQL', 'SQL Server', 'Oracle', 'Elasticsearch'] },
  { id: 'algorithm', name: '数据结构 & 算法', color: '#8b5cf6', icon: 'Histogram', tags: ['数组', '链表', '树', '图', '动态规划', '贪心', '回溯', '排序', '二分', '双指针', '滑动窗口'] },
  { id: 'ai', name: 'AI / 大模型', color: '#ef4444', icon: 'MagicStick', tags: ['LLM', 'Prompt', 'RAG', 'LangChain', 'LangGraph', 'Embedding', '向量数据库', 'Agent', '微调', '推理优化'] },
  { id: 'os', name: '操作系统', color: '#64748b', icon: 'Tools', tags: ['进程', '线程', '内存管理', '文件系统', 'Linux', 'Shell'] },
  { id: 'network', name: '网络', color: '#06b6d4', icon: 'Connection', tags: ['HTTP', 'HTTPS', 'TCP/IP', 'DNS', 'WebSocket', 'CDN', '负载均衡'] },
  { id: 'devops', name: '运维 / DevOps', color: '#ec4899', icon: 'RefreshRight', tags: ['Docker', 'Kubernetes', 'CI/CD', 'Nginx', '监控', '云原生'] },
  { id: 'other', name: '其他', color: '#94a3b8', icon: 'Reading', tags: ['综合', '软技能', 'HR面'] }
]

export function getCategoryMeta(id: string): InterviewCategoryMeta {
  return INTERVIEW_CATEGORIES.find((c) => c.id === id) ?? INTERVIEW_CATEGORIES[INTERVIEW_CATEGORIES.length - 1]
}

/** 难度 */
export type Difficulty = 'easy' | 'medium' | 'hard'

export const DIFFICULTY_META: Record<Difficulty, { name: string; color: string }> = {
  easy: { name: '简单', color: '#10b981' },
  medium: { name: '中等', color: '#f59e0b' },
  hard: { name: '困难', color: '#ef4444' }
}

/** 题目 */
export interface InterviewQuestion {
  id: string
  category: InterviewCategory
  tags: string[] // 二级标签
  title: string // 题干
  answer: string // 参考答案
  keyPoints?: string // 面试核心要点
  difficulty: Difficulty
  createdAt: number
  updatedAt: number
  source?: string // 来源（公司/网站/自定义）
  favorite?: boolean
}

/** 导入用的题目结构（兼容字段） */
export interface ImportedQuestion {
  category?: string
  tags?: string[] | string
  title?: string
  question?: string
  answer?: string
  difficulty?: string
  source?: string
}

/** 问答会话单题记录 */
export interface QuizItem {
  questionId: string
  question: InterviewQuestion
  userAnswer: string
  revealed: boolean
  score: number // 自评 0/1/2/3 或 -1 未评
}

/** 问答模式配置 */
export interface QuizConfig {
  categories: InterviewCategory[]
  tags: string[]
  difficulty: Difficulty[]
  count: number
  showAnswerImmediately: boolean
}
