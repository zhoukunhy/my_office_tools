<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Reading, Star, Search, Plus, Upload, Edit, Delete, Refresh,
  ArrowLeft, ArrowRight, Collection, Download, MagicStick
} from '@element-plus/icons-vue'
import {
  INTERVIEW_CATEGORIES, DIFFICULTY_META, getCategoryMeta,
  type InterviewQuestion, type InterviewCategory, type Difficulty
} from '@/types/interview'
import {
  listQuestions, createQuestion, updateQuestion, deleteQuestion,
  importQuestions, importFile as importFileApi, downloadExport,
  batchDeleteQuestions, batchUpdateQuestions, saveQuizRecords,
  quizQuestions as fetchQuizQuestions, getStats, parseImportText,
  type ListParams
} from '@/composables/useInterviewBank'
import RecordsView from '@/components/interview/RecordsView.vue'
import AiGenerateDialog from '@/components/interview/AiGenerateDialog.vue'

type Mode = 'bank' | 'quiz' | 'records'

const mode = ref<Mode>('bank')
const loading = ref(false)
const questions = ref<InterviewQuestion[]>([])
const total = ref(0)
const stats = ref<{ total: number; by_category: Record<string, number>; favorites: number }>({
  total: 0, by_category: {}, favorites: 0
})

// 筛选条件
const filterCategory = ref<InterviewCategory | ''>('')
const filterTag = ref('')
const filterDifficulty = ref<Difficulty | ''>('')
const filterFavorite = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = 20

const allTags = computed(() => {
  const set = new Set<string>()
  questions.value.forEach((q) => q.tags.forEach((t) => set.add(t)))
  return Array.from(set)
})

async function loadStats() {
  try {
    stats.value = await getStats()
  } catch (e) {
    console.warn(e)
  }
}

async function loadList() {
  loading.value = true
  try {
    const params: ListParams = {
      category: filterCategory.value || undefined,
      tag: filterTag.value || undefined,
      difficulty: filterDifficulty.value || undefined,
      keyword: keyword.value || undefined,
      favorite: filterFavorite.value || undefined,
      page: page.value,
      pageSize
    }
    const r = await listQuestions(params)
    questions.value = r.items
    total.value = r.total
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  page.value = 1
  loadList()
}

onMounted(() => {
  loadStats()
  loadList()
})

// ---------- 编辑弹窗 ----------
const editVisible = ref(false)
const editing = ref<Partial<InterviewQuestion> | null>(null)
const isNew = ref(false)

function openNew() {
  editing.value = {
    category: filterCategory.value || 'frontend',
    tags: [],
    title: '',
    answer: '',
    difficulty: 'medium',
    source: '',
    favorite: false
  }
  isNew.value = true
  editVisible.value = true
}

function openEdit(q: InterviewQuestion) {
  editing.value = { ...q }
  isNew.value = false
  editVisible.value = true
}

async function saveEdit() {
  if (!editing.value?.title?.trim()) {
    ElMessage.warning('题干不能为空')
    return
  }
  try {
    if (isNew.value) {
      await createQuestion(editing.value as Omit<InterviewQuestion, 'id' | 'createdAt' | 'updatedAt'>)
      ElMessage.success('已新增')
    } else {
      await updateQuestion(editing.value!.id!, editing.value)
      ElMessage.success('已保存')
    }
    editVisible.value = false
    loadStats()
    loadList()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function removeQuestion(q: InterviewQuestion) {
  try {
    await ElMessageBox.confirm(`确定删除「${q.title.slice(0, 30)}」？`, '删除题目', { type: 'warning' })
    await deleteQuestion(q.id)
    ElMessage.success('已删除')
    loadStats()
    loadList()
  } catch { /* 取消 */ }
}

async function toggleFavorite(q: InterviewQuestion) {
  await updateQuestion(q.id, { favorite: !q.favorite })
  q.favorite = !q.favorite
  loadStats()
}

// ---------- 导入弹窗 ----------
const importVisible = ref(false)
const importText = ref('')

function openImport() {
  importText.value = ''
  importVisible.value = true
}

async function doImport() {
  try {
    if (pickedFile.value) {
      const r = await importFileApi(pickedFile.value)
      ElMessage.success(`导入 ${r.inserted} 条，跳过 ${r.skipped} 条`)
      importVisible.value = false
      loadStats()
      loadList()
      return
    }
    const items = parseImportText(importText.value)
    if (!items.length) {
      ElMessage.warning('未解析到有效题目')
      return
    }
    const r = await importQuestions(items)
    ElMessage.success(`导入 ${r.inserted} 条，跳过 ${r.skipped} 条`)
    importVisible.value = false
    loadStats()
    loadList()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  }
}

// ---------- 文件选择导入 ----------
const pickedFile = ref<File | null>(null)
function onFilePick(file: { raw?: File }) {
  pickedFile.value = file.raw ?? null
}

// ---------- 导出 ----------
const exportVisible = ref(false)
async function doExport(format: 'json' | 'text') {
  try {
    await downloadExport(
      {
        category: filterCategory.value || undefined,
        difficulty: filterDifficulty.value || undefined,
        keyword: keyword.value || undefined
      },
      format
    )
    exportVisible.value = false
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  }
}

// ---------- 批量操作 ----------
const batchMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const batchTag = ref('')

function toggleBatch() {
  batchMode.value = !batchMode.value
  selectedIds.value = new Set()
}
function onCardClick(q: InterviewQuestion) {
  if (!batchMode.value) return
  const s = new Set(selectedIds.value)
  if (s.has(q.id)) s.delete(q.id)
  else s.add(q.id)
  selectedIds.value = s
}
function selectPage() {
  selectedIds.value = new Set(questions.value.map((q) => q.id))
}
async function doBatchDelete() {
  const ids = Array.from(selectedIds.value)
  if (!ids.length) {
    ElMessage.warning('未选择题目')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 道题？相关问答记录将一并清除。`, '批量删除', { type: 'warning' })
    const r = await batchDeleteQuestions(ids)
    ElMessage.success(`已删除 ${r.deleted} 题`)
    selectedIds.value = new Set()
    loadStats()
    loadList()
  } catch (e) {
    if (e instanceof Error) ElMessage.error(e.message)
  }
}
async function doBatchTag() {
  const ids = Array.from(selectedIds.value)
  const tags = batchTag.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  if (!ids.length) {
    ElMessage.warning('未选择题目')
    return
  }
  if (!tags.length) {
    ElMessage.warning('请输入标签')
    return
  }
  try {
    const r = await batchUpdateQuestions(ids, { tags })
    ElMessage.success(`已为 ${r.updated} 题覆盖设置标签`)
    batchTag.value = ''
    loadList()
  } catch (e) {
    if (e instanceof Error) ElMessage.error(e.message)
  }
}

// ---------- AI 出题 ----------
const aiVisible = ref(false)
function onAiImported() {
  loadStats()
  loadList()
}

// ---------- 问答模式 ----------
const quizCategories = ref<InterviewCategory[]>(['frontend'])
const quizDifficulties = ref<Difficulty[]>([])
const quizCount = ref(10)
const quizStarted = ref(false)
const quizQuestions = ref<InterviewQuestion[]>([])
const quizIndex = ref(0)
const quizAnswers = ref<string[]>([])
const quizRevealed = ref<boolean[]>([])
const quizScores = ref<number[]>([])

const currentQuiz = computed(() => quizQuestions.value[quizIndex.value])

async function startQuiz() {
  if (!quizCategories.value.length) {
    ElMessage.warning('请至少选择一个分类')
    return
  }
  try {
    quizQuestions.value = await fetchQuizQuestions({
      categories: quizCategories.value,
      difficulties: quizDifficulties.value,
      count: quizCount.value
    })
    if (!quizQuestions.value.length) {
      ElMessage.warning('该筛选条件下暂无题目')
      return
    }
    quizIndex.value = 0
    quizAnswers.value = new Array(quizQuestions.value.length).fill('')
    quizRevealed.value = new Array(quizQuestions.value.length).fill(false)
    quizScores.value = new Array(quizQuestions.value.length).fill(-1)
    quizStarted.value = true
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '出题失败')
  }
}

function revealAnswer() {
  quizRevealed.value[quizIndex.value] = true
}
function rate(s: number) {
  quizScores.value[quizIndex.value] = s
  // 自评即落库：错题本据此归类（score<=1 为错题）
  const q = currentQuiz.value
  if (q) {
    saveQuizRecords([{ questionId: q.id, userAnswer: quizAnswers.value[quizIndex.value] || '', score: s }])
      .catch(() => ElMessage.warning('记录保存失败，请检查后端连接'))
  }
}
function nextQuiz() {
  if (quizIndex.value < quizQuestions.value.length - 1) quizIndex.value++
}
function prevQuiz() {
  if (quizIndex.value > 0) quizIndex.value--
}
function exitQuiz() {
  quizStarted.value = false
  quizQuestions.value = []
}
</script>

<template>
  <div class="interview-page">
    <header class="page-hero">
      <div class="hero-left">
        <el-icon class="hero-icon"><Reading /></el-icon>
        <div>
          <h1>面试题库</h1>
          <p>分类整理 · 检索 · 导入 · 随机出题问答</p>
        </div>
      </div>
      <div class="hero-right">
        <el-radio-group v-model="mode" size="default">
          <el-radio-button value="bank">题目库</el-radio-button>
          <el-radio-button value="quiz">问答模式</el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <!-- ============ 题目库模式 ============ -->
    <div v-if="mode === 'bank'" class="bank-layout">
      <aside class="filter-side">
        <div class="side-card">
          <div class="side-h">
            <span>统计</span>
            <el-button link :icon="Refresh" @click="loadStats" />
          </div>
          <div class="stat-row"><span>总题数</span><strong>{{ stats.total }}</strong></div>
          <div class="stat-row"><span>收藏</span><strong>{{ stats.favorites }}</strong></div>
        </div>

        <div class="side-card">
          <div class="side-h"><span>分类</span></div>
          <div class="cat-list">
            <div
              class="cat-item"
              :class="{ active: !filterCategory }"
              @click="filterCategory = ''; resetAndLoad()"
            >
              <span>全部</span><em>{{ stats.total }}</em>
            </div>
            <div
              v-for="c in INTERVIEW_CATEGORIES"
              :key="c.id"
              class="cat-item"
              :class="{ active: filterCategory === c.id }"
              @click="filterCategory = c.id; resetAndLoad()"
            >
              <span class="cat-dot" :style="{ background: c.color }" />
              <span>{{ c.name }}</span>
              <em>{{ stats.by_category[c.id] || 0 }}</em>
            </div>
          </div>
        </div>

        <div class="side-card">
          <div class="side-h"><span>难度</span></div>
          <div class="chip-row">
            <span
              class="chip"
              :class="{ active: !filterDifficulty }"
              @click="filterDifficulty = ''; resetAndLoad()"
            >全部</span>
            <span
              v-for="(m, k) in DIFFICULTY_META"
              :key="k"
              class="chip"
              :class="{ active: filterDifficulty === k }"
              :style="filterDifficulty === k ? { background: m.color, borderColor: m.color } : {}"
              @click="filterDifficulty = k as Difficulty; resetAndLoad()"
            >{{ m.name }}</span>
          </div>
          <div class="fav-toggle">
            <el-checkbox v-model="filterFavorite" @change="resetAndLoad">仅看收藏</el-checkbox>
          </div>
        </div>

        <div v-if="allTags.length" class="side-card">
          <div class="side-h"><span>标签</span></div>
          <div class="chip-row">
            <span
              v-for="t in allTags"
              :key="t"
              class="chip"
              :class="{ active: filterTag === t }"
              @click="filterTag = filterTag === t ? '' : t; resetAndLoad()"
            >{{ t }}</span>
          </div>
        </div>
      </aside>

      <section class="list-main">
        <div class="list-toolbar">
          <el-input
            v-model="keyword"
            placeholder="搜索题干或答案…"
            :prefix-icon="Search"
            clearable
            @keyup.enter="resetAndLoad"
            @clear="resetAndLoad"
            style="flex: 1; max-width: 420px"
          />
          <el-button type="primary" :icon="Plus" @click="openNew">新增题目</el-button>
          <el-button :icon="Upload" @click="openImport">导入</el-button>
          <el-button :icon="Download" @click="exportVisible = true">导出</el-button>
          <el-button type="warning" plain :icon="MagicStick" @click="aiVisible = true">AI 出题</el-button>
          <el-button :type="batchMode ? 'primary' : 'default'" @click="toggleBatch">
            {{ batchMode ? '退出批量' : '批量管理' }}
          </el-button>
          <el-button :icon="Refresh" @click="loadList" />
        </div>

        <!-- 批量操作条 -->
        <div v-if="batchMode" class="batch-bar">
          <span>已选 <strong>{{ selectedIds.size }}</strong> 题</span>
          <el-button size="small" @click="selectPage">全选本页</el-button>
          <el-button size="small" @click="selectedIds = new Set()">清空</el-button>
          <el-input v-model="batchTag" size="small" placeholder="标签（逗号分隔，覆盖设置）" style="width: 220px" />
          <el-button size="small" type="primary" @click="doBatchTag">应用标签</el-button>
          <el-button size="small" type="danger" @click="doBatchDelete">批量删除</el-button>
          <em class="batch-tip">点击题目卡片即可勾选</em>
        </div>

        <div v-loading="loading" class="q-list">
          <div v-if="!questions.length && !loading" class="empty-state">
            <el-icon :size="40"><Collection /></el-icon>
            <p>暂无题目，点击「新增题目」或「导入」开始整理</p>
          </div>
          <div
            v-for="q in questions"
            :key="q.id"
            class="q-card"
            :class="{ 'batch-selected': batchMode && selectedIds.has(q.id) }"
            @click="onCardClick(q)"
          >
            <div class="q-head">
              <div class="q-tags">
                <el-checkbox
                  v-if="batchMode"
                  :model-value="selectedIds.has(q.id)"
                  @click.stop
                  @change="onCardClick(q)"
                />
                <span class="tag-cat" :style="{ background: getCategoryMeta(q.category).color }">
                  {{ getCategoryMeta(q.category).name }}
                </span>
                <span class="tag-diff" :style="{ color: DIFFICULTY_META[q.difficulty].color }">
                  {{ DIFFICULTY_META[q.difficulty].name }}
                </span>
                <span v-for="t in q.tags" :key="t" class="tag">#{{ t }}</span>
              </div>
              <div class="q-actions" @click.stop>
                <el-icon
                  class="fav-icon"
                  :class="{ active: q.favorite }"
                  @click="toggleFavorite(q)"
                ><Star /></el-icon>
                <el-button link :icon="Edit" @click="openEdit(q)">编辑</el-button>
                <el-button link type="danger" :icon="Delete" @click="removeQuestion(q)">删除</el-button>
              </div>
            </div>
            <h3 class="q-title" @click.stop="batchMode ? onCardClick(q) : openEdit(q)">{{ q.title }}</h3>
            <p class="q-answer">{{ q.answer.slice(0, 120) }}{{ q.answer.length > 120 ? '…' : '' }}</p>
            <div class="q-foot">
              <span v-if="q.source">来源：{{ q.source }}</span>
              <span>{{ new Date(q.updatedAt).toLocaleDateString() }}</span>
            </div>
          </div>
        </div>

        <div v-if="total > pageSize" class="pagination">
          <el-pagination
            v-model:current-page="page"
            :total="total"
            :page-size="pageSize"
            layout="prev, pager, next, total"
            @current-change="loadList"
          />
        </div>
      </section>
    </div>

    <!-- ============ 错题本模式 ============ -->
    <RecordsView v-else-if="mode === 'records'" class="records-wrap" />

    <!-- ============ 问答模式 ============ -->
    <div v-else class="quiz-wrap">
      <div v-if="!quizStarted" class="quiz-config">
        <h3>配置出题范围</h3>
        <div class="cfg-block">
          <label>分类（至少选一个）</label>
          <el-checkbox-group v-model="quizCategories">
            <el-checkbox v-for="c in INTERVIEW_CATEGORIES" :key="c.id" :value="c.id">
              {{ c.name }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="cfg-block">
          <label>难度（不选=全部）</label>
          <el-checkbox-group v-model="quizDifficulties">
            <el-checkbox v-for="(m, k) in DIFFICULTY_META" :key="k" :value="k">{{ m.name }}</el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="cfg-block">
          <label>题目数量</label>
          <el-input-number v-model="quizCount" :min="1" :max="100" />
        </div>
        <el-button type="primary" size="large" @click="startQuiz">开始随机出题</el-button>
      </div>

      <div v-else class="quiz-stage">
        <div class="quiz-progress">
          <span>第 {{ quizIndex + 1 }} / {{ quizQuestions.length }} 题</span>
          <el-progress :percentage="Math.round(((quizIndex + 1) / quizQuestions.length) * 100)" :stroke-width="6" />
        </div>

        <div v-if="currentQuiz" class="quiz-card">
          <div class="quiz-meta">
            <span class="tag-cat" :style="{ background: getCategoryMeta(currentQuiz.category).color }">
              {{ getCategoryMeta(currentQuiz.category).name }}
            </span>
            <span class="tag-diff" :style="{ color: DIFFICULTY_META[currentQuiz.difficulty].color }">
              {{ DIFFICULTY_META[currentQuiz.difficulty].name }}
            </span>
            <span v-for="t in currentQuiz.tags" :key="t" class="tag">#{{ t }}</span>
          </div>
          <h2 class="quiz-title">{{ currentQuiz.title }}</h2>
          <el-input
            v-model="quizAnswers[quizIndex]"
            type="textarea"
            :rows="6"
            placeholder="在这里作答…（纯本地记录，不会上传）"
          />
          <div class="quiz-actions">
            <el-button v-if="!quizRevealed[quizIndex]" type="primary" @click="revealAnswer">
              查看参考答案
            </el-button>
            <template v-else>
              <div class="answer-box">
                <strong>参考答案：</strong>
                <p>{{ currentQuiz.answer }}</p>
              </div>
              <div class="rate-row">
                <span>自评：</span>
                <el-button
                  v-for="s in [0, 1, 2, 3]"
                  :key="s"
                  size="small"
                  :type="quizScores[quizIndex] === s ? 'primary' : 'default'"
                  @click="rate(s)"
                >{{ ['不会', '一般', '掌握', '熟练'][s] }}</el-button>
              </div>
            </template>
          </div>
          <div class="quiz-nav">
            <el-button :icon="ArrowLeft" :disabled="quizIndex === 0" @click="prevQuiz">上一题</el-button>
            <el-button @click="exitQuiz">退出</el-button>
            <el-button
              type="primary"
              :icon="ArrowRight"
              :disabled="quizIndex === quizQuestions.length - 1"
              @click="nextQuiz"
            >下一题</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ 编辑弹窗 ============ -->
    <el-dialog v-model="editVisible" :title="isNew ? '新增题目' : '编辑题目'" width="720px" top="6vh">
      <div v-if="editing" class="edit-form">
        <div class="form-row">
          <label>分类</label>
          <el-select v-model="editing.category" style="width: 100%">
            <el-option v-for="c in INTERVIEW_CATEGORIES" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
        </div>
        <div class="form-row">
          <label>标签（逗号分隔）</label>
          <el-input
            :model-value="editing.tags?.join(', ') || ''"
            placeholder="Vue, 响应式"
            @update:model-value="(v: string) => { if (editing) editing.tags = v.split(/[,，]/).map((s) => s.trim()).filter(Boolean) }"
          />
        </div>
        <div class="form-row">
          <label>难度</label>
          <el-radio-group v-model="editing.difficulty">
            <el-radio v-for="(m, k) in DIFFICULTY_META" :key="k" :value="k">{{ m.name }}</el-radio>
          </el-radio-group>
        </div>
        <div class="form-row">
          <label>题干 *</label>
          <el-input v-model="editing.title" type="textarea" :rows="2" />
        </div>
        <div class="form-row">
          <label>参考答案</label>
          <el-input v-model="editing.answer" type="textarea" :rows="10" />
        </div>
        <div class="form-row">
          <label>来源</label>
          <el-input v-model="editing.source" placeholder="可选，如：字节跳动 / 牛客网" />
        </div>
      </div>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">{{ isNew ? '新增' : '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- ============ 导入弹窗 ============ -->
    <el-dialog v-model="importVisible" title="导入题目" width="720px" top="6vh">
      <p class="import-tip">
        支持三种方式：<br />
        · <strong>上传文件</strong>：.json / .txt / .md（UTF-8）<br />
        · <strong>粘贴 JSON 数组</strong>：<code>[{ "title": "...", "answer": "...", "category": "frontend", "tags": ["Vue"], "difficulty": "easy" }]</code><br />
        · <strong>粘贴文本</strong>：每题空行分隔，首行题干，"答：" 开头为答案，可标注 <code>分类：前端</code> <code>标签：Vue</code> <code>难度：简单</code>
      </p>
      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".json,.txt,.md"
        :on-change="onFilePick"
        :on-remove="() => (pickedFile = null)"
        style="margin-bottom: 14px"
      >
        <el-icon :size="32"><Upload /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em>（选了文件则忽略下方文本）</div>
      </el-upload>
      <el-input
        v-model="importText"
        type="textarea"
        :rows="10"
        placeholder='例如：&#10;Vue 的响应式原理是什么？&#10;答：Vue 通过 Object.defineProperty...&#10;分类：前端&#10;标签：Vue&#10;&#10;第二题...'
      />
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" @click="doImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- ============ 导出弹窗 ============ -->
    <el-dialog v-model="exportVisible" title="导出题目" width="480px">
      <p class="import-tip">
        按当前筛选条件导出（分类 {{ filterCategory || '全部' }} / 难度 {{ filterDifficulty || '全部' }} / 关键词 {{ keyword || '无' }}）<br />
        · <strong>JSON</strong>：结构化数据，可直接重新导入<br />
        · <strong>文本</strong>：与粘贴导入格式互通，方便编辑分享
      </p>
      <template #footer>
        <el-button @click="exportVisible = false">取消</el-button>
        <el-button :icon="Download" @click="doExport('text')">导出 TXT</el-button>
        <el-button type="primary" :icon="Download" @click="doExport('json')">导出 JSON</el-button>
      </template>
    </el-dialog>

    <!-- ============ AI 出题弹窗 ============ -->
    <AiGenerateDialog v-model="aiVisible" @imported="onAiImported" />
  </div>
</template>

<style scoped>
.interview-page { min-height: 100vh; background: var(--c-bg); padding: 24px; box-sizing: border-box; }
.page-hero { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { font-size: 36px; color: var(--c-primary); }
.hero-left h1 { margin: 0; font-size: 24px; }
.hero-left p { margin: 4px 0 0; color: var(--c-text-mute); font-size: 13px; }

/* 题库布局 */
.bank-layout { display: grid; grid-template-columns: 240px 1fr; gap: 18px; align-items: start; }
.filter-side { position: sticky; top: 16px; }
.side-card { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 10px; padding: 14px; margin-bottom: 14px; }
.side-h { display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 13px; margin-bottom: 10px; }
.stat-row { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; }
.stat-row strong { color: var(--c-primary); }
.cat-list { display: flex; flex-direction: column; gap: 2px; }
.cat-item { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.cat-item:hover { background: var(--c-hover); }
.cat-item.active { background: var(--c-primary-soft); color: var(--c-primary); font-weight: 600; }
.cat-item em { margin-left: auto; font-style: normal; color: var(--c-text-mute); font-size: 12px; }
.cat-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { padding: 4px 10px; border: 1px solid var(--c-border); border-radius: 12px; font-size: 12px; cursor: pointer; background: var(--c-bg); }
.chip.active { color: #fff; }
.fav-toggle { margin-top: 10px; }

.list-main { min-width: 0; }
.list-toolbar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }
.q-list { display: flex; flex-direction: column; gap: 12px; }
.empty-state { text-align: center; padding: 60px 20px; color: var(--c-text-mute); }
.q-card { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 10px; padding: 16px 18px; transition: border-color .2s; }
.q-card:hover { border-color: var(--c-primary); }
.q-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 10px; }
.q-tags { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.tag-cat { color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.tag-diff { font-size: 12px; font-weight: 600; }
.tag { color: var(--c-text-mute); font-size: 12px; }
.q-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.fav-icon { font-size: 18px; cursor: pointer; color: var(--c-text-mute); }
.fav-icon.active { color: #f59e0b; }
.q-title { margin: 0 0 8px; font-size: 15px; cursor: pointer; }
.q-answer { margin: 0; color: var(--c-text-mute); font-size: 13px; line-height: 1.6; }
.q-foot { margin-top: 10px; display: flex; justify-content: space-between; font-size: 12px; color: var(--c-text-mute); }
.pagination { margin-top: 20px; display: flex; justify-content: center; }

/* 问答模式 */
.quiz-wrap { max-width: 820px; margin: 0 auto; }
.quiz-config { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 12px; padding: 30px; }
.quiz-config h3 { margin: 0 0 20px; }
.cfg-block { margin-bottom: 20px; }
.cfg-block label { display: block; font-weight: 600; margin-bottom: 10px; font-size: 14px; }
.quiz-progress { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.quiz-progress span { white-space: nowrap; font-size: 13px; }
.quiz-card { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 12px; padding: 28px; }
.quiz-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; align-items: center; }
.quiz-title { margin: 0 0 18px; font-size: 19px; line-height: 1.5; }
.quiz-actions { margin-top: 16px; }
.answer-box { margin-top: 16px; padding: 16px; background: var(--c-primary-soft); border-left: 3px solid var(--c-primary); border-radius: 6px; }
.answer-box p { margin: 8px 0 0; white-space: pre-wrap; line-height: 1.7; }
.rate-row { margin-top: 14px; display: flex; align-items: center; gap: 8px; }
.quiz-nav { margin-top: 24px; display: flex; justify-content: space-between; }

/* 编辑表单 */
.edit-form { display: flex; flex-direction: column; gap: 16px; }
.form-row { display: flex; flex-direction: column; gap: 6px; }
.form-row label { font-size: 13px; font-weight: 600; }
.import-tip { background: var(--c-bg-soft); padding: 12px; border-radius: 6px; font-size: 13px; line-height: 1.8; margin: 0 0 14px; }
.import-tip code { background: var(--c-bg); padding: 1px 6px; border-radius: 3px; }

.batch-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; background: var(--c-primary-soft); border: 1px dashed var(--c-primary); border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; font-size: 13px; }
.batch-tip { font-style: normal; color: var(--c-text-mute); margin-left: auto; font-size: 12px; }
.q-card.batch-selected { border-color: var(--c-primary); background: var(--c-primary-soft); }
.records-wrap { max-width: 900px; margin: 0 auto; }

@media (max-width: 768px) {
  .bank-layout { grid-template-columns: 1fr; }
  .filter-side { position: static; }
  .interview-page { padding: 14px; }
}
</style>
