<template>
  <div class="page-interview">
    <!-- ============ 顶部 Hero ============ -->
    <div class="hero">
      <div class="hero-text">
        <h1 class="hero-title">
          <el-icon :size="28"><Reading /></el-icon>
          面试题库
        </h1>
        <p class="hero-sub">整理面试题 · 核心要点提炼 · 随机抽题模拟练习</p>
      </div>
      <div class="hero-right">
        <el-radio-group v-model="mode" size="large">
          <el-radio-button value="bank">题库管理</el-radio-button>
          <el-radio-button value="quiz">模拟刷题</el-radio-button>
        </el-radio-group>
        <el-button
          v-if="mode === 'bank'"
          type="primary" size="large" :icon="Plus"
          @click="openNew"
        >新增题目</el-button>
      </div>
    </div>

    <!-- ============ 题库管理 ============ -->
    <div v-if="mode === 'bank'" class="bank-layout">
      <!-- 左侧筛选 -->
      <aside class="side-panel">
        <div class="side-block">
          <h4 class="side-title">分类</h4>
          <div class="side-list">
            <button
              class="side-item"
              :class="{ active: filterCategory === '' }"
              @click="setFilter('category', '')"
            >
              全部 <span class="side-count">{{ stats.total }}</span>
            </button>
            <button
              v-for="c in INTERVIEW_CATEGORIES"
              :key="c.id"
              class="side-item"
              :class="{ active: filterCategory === c.id }"
              @click="setFilter('category', c.id)"
            >
              <span class="dot" :style="{ background: c.color }" />
              {{ c.name }}
              <span class="side-count">{{ stats.by_category[c.id] || 0 }}</span>
            </button>
          </div>
        </div>
        <div class="side-block">
          <h4 class="side-title">难度</h4>
          <div class="side-list">
            <button
              class="side-item"
              :class="{ active: filterDifficulty === '' }"
              @click="setFilter('difficulty', '')"
            >全部</button>
            <button
              v-for="(d, key) in DIFFICULTY_META"
              :key="key"
              class="side-item"
              :class="{ active: filterDifficulty === key }"
              @click="setFilter('difficulty', key)"
            >
              <span class="dot" :style="{ background: d.color }" />
              {{ d.name }}
            </button>
          </div>
        </div>
        <div class="side-block">
          <h4 class="side-title">快捷筛选</h4>
          <el-checkbox v-model="filterFavorite" @change="onFilterChange">仅看收藏</el-checkbox>
          <el-select
            v-model="filterTag" placeholder="按标签筛选" clearable filterable
            style="width: 100%; margin-top: 8px" @change="onFilterChange"
          >
            <el-option v-for="t in allTags" :key="t" :label="`#${t}`" :value="t" />
          </el-select>
        </div>
      </aside>

      <!-- 右侧主区 -->
      <div class="list-main">
        <div class="list-toolbar">
          <el-input
            v-model="keyword"
            placeholder="搜索题干 / 答案关键词…"
            :prefix-icon="Search"
            clearable
            style="max-width: 320px"
            @input="onKeywordChange"
          />
          <el-button :icon="Refresh" circle title="刷新" @click="onFilterChange" />
          <el-divider direction="vertical" />
          <el-button :icon="Upload" @click="importVisible = true">导入</el-button>
          <el-button :icon="Download" @click="exportVisible = true">导出</el-button>
          <el-button :icon="MagicStick" @click="aiVisible = true">AI 生成</el-button>
          <em v-if="selectedIds.size > 0" class="batch-tip">已选 {{ selectedIds.size }} 题</em>
        </div>

        <!-- 批量操作条：勾选后自动出现 -->
        <div v-if="selectedIds.size > 0" class="batch-bar">
          <span>已选 {{ selectedIds.size }} 题</span>
          <el-button size="small" @click="selectPage">全选本页</el-button>
          <el-button size="small" @click="batchFavorite(true)">批量收藏</el-button>
          <el-button size="small" @click="batchFavorite(false)">取消收藏</el-button>
          <el-input v-model="batchTag" placeholder="输入标签" size="small" style="width: 120px" />
          <el-button size="small" type="primary" @click="batchTagAdd">批量打标签</el-button>
          <el-button size="small" type="danger" @click="batchRemove">批量删除</el-button>
        </div>

        <div v-loading="loading" class="q-table-wrap">
          <div v-if="!questions.length && !loading" class="empty-state">
            <el-icon :size="40"><Collection /></el-icon>
            <p>暂无题目，点击「新增题目」或「导入」开始整理</p>
          </div>
          <el-table
            v-else
            ref="tableRef"
            :data="questions"
            row-key="id"
            border
            stripe
            class="q-table"
            :row-class-name="rowClassName"
            @row-click="openEdit"
            @selection-change="onSelectionChange"
          >
            <el-table-column type="selection" width="44" align="center" />
            <el-table-column label="分类" width="92" align="center">
              <template #default="{ row }">
                <span class="tag-cat" :style="{ background: getCategoryMeta(row.category).color }">
                  {{ getCategoryMeta(row.category).name }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="难度" width="72" align="center">
              <template #default="{ row }">
                <span class="tag-diff" :style="{ color: getDifficultyMeta(row.difficulty).color }">
                  {{ getDifficultyMeta(row.difficulty).name }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="题干" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="cell-title">{{ row.title }}</span>
              </template>
            </el-table-column>
            <el-table-column label="答案" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="cell-muted">{{ row.answer || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="核心要点" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="cell-muted">{{ row.keyPoints || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="标签" width="140">
              <template #default="{ row }">
                <div class="cell-tags">
                  <span v-for="t in row.tags" :key="t" class="tag">#{{ t }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100" show-overflow-tooltip />
            <el-table-column label="更新" width="96" align="center">
              <template #default="{ row }">
                <span class="cell-muted">{{ fmtDate(row.updatedAt) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="168" align="center" fixed="right">
              <template #default="{ row }">
                <div class="cell-actions" @click.stop>
                  <el-tooltip :content="row.favorite ? '取消收藏' : '收藏'">
                    <el-icon
                      class="fav-icon"
                      :class="{ active: row.favorite }"
                      @click="toggleFavorite(row)"
                    ><Star /></el-icon>
                  </el-tooltip>
                  <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
                  <el-button link type="danger" :icon="Delete" @click="removeQuestion(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="pagination">
          <el-pagination
            v-model:current-page="page"
            :page-size="PAGE_SIZE"
            :total="total"
            layout="prev, pager, next, total"
            @current-change="loadList"
          />
        </div>
      </div>
    </div>

    <!-- ============ 模拟刷题 ============ -->
    <div v-else-if="mode === 'quiz'" class="quiz-layout">
      <div v-if="!quizStarted" class="quiz-config">
        <h3>抽题设置</h3>
        <div class="form-row">
          <label>分类</label>
          <el-select v-model="quizCategories" multiple collapse-tags placeholder="全部分类" style="width: 100%">
            <el-option
              v-for="c in INTERVIEW_CATEGORIES" :key="c.id"
              :label="c.name" :value="c.id"
            />
          </el-select>
        </div>
        <div class="form-row">
          <label>难度</label>
          <el-select v-model="quizDifficulties" multiple collapse-tags placeholder="全部难度" style="width: 100%">
            <el-option
              v-for="(d, key) in DIFFICULTY_META" :key="key"
              :label="d.name" :value="key"
            />
          </el-select>
        </div>
        <div class="form-row">
          <label>标签</label>
          <el-select v-model="quizTags" multiple filterable collapse-tags placeholder="不限标签" style="width: 100%">
            <el-option v-for="t in allTags" :key="t" :label="`#${t}`" :value="t" />
          </el-select>
        </div>
        <div class="form-row">
          <label>题目数量</label>
          <el-input-number v-model="quizCount" :min="1" :max="50" />
        </div>
        <el-button type="primary" size="large" style="width: 100%" :loading="quizLoading" @click="startQuiz">
          开始刷题
        </el-button>
      </div>

      <div v-else class="quiz-panel">
        <div class="quiz-head">
          <el-button :icon="ArrowLeft" @click="confirmExitQuiz">退出刷题</el-button>
          <span class="quiz-progress">第 {{ quizIndex + 1 }} / {{ quizList.length }} 题</span>
          <el-button :icon="ArrowRight" :disabled="quizIndex >= quizList.length - 1" @click="nextQuiz">
            下一题
          </el-button>
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
            v-model="quizAnswer"
            type="textarea"
            :rows="5"
            placeholder="先自己口头作答或写下要点，再对照参考答案…"
            style="margin: 14px 0"
          />
          <el-collapse v-model="quizReveal">
            <el-collapse-item title="查看参考答案" name="answer">
              <p class="quiz-answer">{{ currentQuiz.answer }}</p>
              <template v-if="currentQuiz.keyPoints">
                <p class="quiz-kp-title">💡 面试核心要点</p>
                <p class="quiz-kp">{{ currentQuiz.keyPoints }}</p>
              </template>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>

    <!-- ============ 编辑弹窗 ============ -->
    <el-dialog v-model="editVisible" :title="editing?.id ? '编辑题目' : '新增题目'" width="720px" top="6vh">
      <div v-if="editing" class="edit-form">
        <div class="form-row">
          <label>题干 <i class="req">*</i></label>
          <el-input v-model="editing.title" type="textarea" :rows="2" placeholder="输入面试题题目" />
        </div>
        <div class="form-row">
          <label>参考答案</label>
          <el-input
            v-model="editing.answer"
            type="textarea"
            :autosize="{ minRows: 10, maxRows: 24 }"
            placeholder="完整的参考答案（支持换行，输入框会随内容自动增高）"
          />
        </div>
        <div class="form-row">
          <label>面试核心要点</label>
          <el-input
            v-model="editing.keyPoints"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 12 }"
            placeholder="回答这道题时必须覆盖的关键点，面试官重点考察的部分"
          />
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label>分类</label>
            <el-select v-model="editing.category" style="width: 100%">
              <el-option
                v-for="c in INTERVIEW_CATEGORIES" :key="c.id"
                :label="c.name" :value="c.id"
              />
            </el-select>
          </div>
          <div class="form-row">
            <label>难度</label>
            <el-select v-model="editing.difficulty" style="width: 100%">
              <el-option
                v-for="(d, key) in DIFFICULTY_META" :key="key"
                :label="d.name" :value="key"
              />
            </el-select>
          </div>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label>标签（逗号分隔）</label>
            <el-input v-model="editing.tagsText" placeholder="如：Vue, 响应式" />
          </div>
          <div class="form-row">
            <label>来源</label>
            <el-input v-model="editing.source" placeholder="如：某公司一面 / 牛客网" />
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============ 导入弹窗 ============ -->
    <el-dialog v-model="importVisible" title="导入题目" width="720px" top="6vh">
      <p class="import-tip">
        支持以下方式：<br />
        · <strong>上传 Excel</strong>：.xlsx / .xls（表头：分类、难度、题干、答案、核心要点、标签、来源），可先
        <el-button link type="primary" @click="downloadImportTemplate">下载导入模板</el-button><br />
        · <strong>上传文件</strong>：.json / .txt / .md（UTF-8）<br />
        · <strong>粘贴 JSON 数组</strong>：<code>[{ "title": "...", "answer": "...", "keyPoints": "...", "category": "frontend", "tags": ["Vue"], "difficulty": "easy" }]</code><br />
        · <strong>粘贴文本</strong>：每题空行分隔，首行题干，"答：" 开头为答案，可标注 <code>分类：前端</code> <code>要点：…</code> <code>标签：Vue</code> <code>难度：简单</code>
      </p>
      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".json,.txt,.md,.xlsx,.xls"
        :on-change="onFilePick"
        :on-remove="() => (pickedFile = null)"
        style="margin-bottom: 14px"
      >
        <el-icon :size="32"><Upload /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em>（Excel 在浏览器本地解析，不会上传）</div>
      </el-upload>
      <el-input
        v-model="importText"
        type="textarea"
        :rows="8"
        placeholder='或直接粘贴 JSON / 文本，例如：
什么是闭包？
答：闭包是指……
分类：前端
要点：作用域链、变量引用、内存泄漏'
      />
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- ============ 导出弹窗 ============ -->
    <el-dialog v-model="exportVisible" title="导出题目" width="500px">
      <p class="import-tip">
        按当前筛选条件导出（分类 {{ filterCategory ? getCategoryMeta(filterCategory).name : '全部' }} /
        难度 {{ filterDifficulty || '全部' }} / 关键词 {{ keyword || '无' }} /
        {{ filterFavorite ? '仅收藏' : '全部' }}）<br />
        · <strong>Excel</strong>：.xlsx 表格，答案与核心要点完整展示，可直接用 Excel/WPS 打开编辑<br />
        · <strong>JSON</strong>：结构化数据，可直接重新导入<br />
        · <strong>文本</strong>：与粘贴导入格式互通，方便编辑分享
      </p>
      <template #footer>
        <el-button @click="exportVisible = false">取消</el-button>
        <el-button :icon="Download" @click="doExport('text')">TXT</el-button>
        <el-button :icon="Download" @click="doExport('json')">JSON</el-button>
        <el-button type="primary" :icon="Download" @click="doExportExcel">Excel</el-button>
      </template>
    </el-dialog>

    <!-- ============ AI 生成弹窗 ============ -->
    <AiGenerateDialog v-model="aiVisible" @imported="onAiImported" />
  </div>
</template>

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
  importQuestions, importFile as importFileApi, downloadExport, downloadExcelExport, parseExcelImport,
  batchDeleteQuestions, batchUpdateQuestions, saveQuizRecords,
  quizQuestions as fetchQuizQuestions, getStats, parseImportText,
  type ListParams
} from '@/composables/useInterviewBank'
import AiGenerateDialog from '@/components/interview/AiGenerateDialog.vue'

const PAGE_SIZE = 10

function getDifficultyMeta(d: string) {
  return DIFFICULTY_META[d as Difficulty] ?? DIFFICULTY_META.medium
}

type BankMode = 'bank' | 'quiz'
const mode = ref<BankMode>('bank')

// ---------- 统计 ----------
const stats = ref({ total: 0, by_category: {} as Record<string, number> })
async function loadStats() {
  try {
    stats.value = await getStats()
  } catch { /* 后端未开启时静默 */ }
}

// ---------- 列表与筛选 ----------
const questions = ref<InterviewQuestion[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const keyword = ref('')
const filterCategory = ref<InterviewCategory | ''>('')
const filterDifficulty = ref<Difficulty | ''>('')
const filterFavorite = ref(false)
const filterTag = ref('')
const allTags = ref<string[]>([])

function fmtDate(ts?: number) {
  if (!ts) return '—'
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString()
}

function currentParams(): ListParams {
  return {
    category: filterCategory.value || undefined,
    difficulty: filterDifficulty.value || undefined,
    keyword: keyword.value || undefined,
    favorite: filterFavorite.value ? true : undefined,
    tag: filterTag.value || undefined,
    page: page.value,
    pageSize: PAGE_SIZE
  }
}

async function loadList() {
  loading.value = true
  try {
    const r = await listQuestions(currentParams())
    questions.value = r.items
    total.value = r.total
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载题目失败')
  } finally {
    loading.value = false
  }
}

function setFilter(key: 'category' | 'difficulty', val: string) {
  if (key === 'category') filterCategory.value = val as InterviewCategory | ''
  else filterDifficulty.value = val as Difficulty | ''
  page.value = 1
  loadList()
}

function onFilterChange() {
  page.value = 1
  loadList()
}

const onKeywordChange = debounce(() => {
  page.value = 1
  loadList()
}, 200)

function debounce<T extends (...args: never[]) => void>(fn: T, delay: number) {
  let timer: ReturnType<typeof setTimeout> | undefined
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

onMounted(() => {
  loadStats()
  loadList()
})

// ---------- 编辑 ----------
const editVisible = ref(false)
const editing = ref<Partial<InterviewQuestion> & { tagsText?: string } | null>(null)
const saving = ref(false)

function openNew() {
  editing.value = {
    category: 'frontend', tagsText: '', title: '', answer: '', keyPoints: '',
    difficulty: 'medium', source: ''
  }
  editVisible.value = true
}

function openEdit(q: InterviewQuestion) {
  editing.value = { ...q, tagsText: (q.tags || []).join(', ') }
  editVisible.value = true
}

async function saveEdit() {
  const e = editing.value
  if (!e) return
  if (!e.title?.trim()) {
    ElMessage.warning('请填写题干')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...e,
      tags: e.tagsText ? e.tagsText.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : []
    }
    if (e.id) await updateQuestion(e.id, payload as Partial<InterviewQuestion>)
    else await createQuestion(payload as Omit<InterviewQuestion, 'id' | 'createdAt' | 'updatedAt'>)
    ElMessage.success('保存成功')
    editVisible.value = false
    loadStats()
    loadList()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeQuestion(q: InterviewQuestion) {
  try {
    await ElMessageBox.confirm(`确定删除「${q.title.slice(0, 30)}…」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteQuestion(q.id)
    ElMessage.success('已删除')
    loadStats()
    loadList()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '删除失败')
  }
}

async function toggleFavorite(q: InterviewQuestion) {
  try {
    await updateQuestion(q.id, { favorite: !q.favorite })
    q.favorite = !q.favorite
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  }
}

// ---------- 批量操作 ----------
const selectedIds = ref<Set<string>>(new Set())
const batchTag = ref('')
const tableRef = ref()

function onSelectionChange(rows: InterviewQuestion[]) {
  selectedIds.value = new Set(rows.map((r) => r.id))
}

function rowClassName({ row }: { row: InterviewQuestion }): string {
  return selectedIds.value.has(row.id) ? 'row-selected' : ''
}

function selectPage() {
  tableRef.value?.toggleAllSelection()
}

async function batchFavorite(fav: boolean) {
  if (!selectedIds.value.size) {
    ElMessage.warning('请先勾选题目')
    return
  }
  try {
    const r = await batchUpdateQuestions([...selectedIds.value], { favorite: fav })
    ElMessage.success(`已更新 ${r.updated} 题`)
    loadList()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '批量操作失败')
  }
}

async function batchTagAdd() {
  const t = batchTag.value.trim()
  if (!t) {
    ElMessage.warning('请输入要添加的标签')
    return
  }
  if (!selectedIds.value.size) {
    ElMessage.warning('请先勾选题目')
    return
  }
  try {
    const targets = questions.value.filter((q) => selectedIds.value.has(q.id))
    await Promise.all(
      targets.map((q) =>
        updateQuestion(q.id, { tags: [...new Set([...(q.tags || []), t])] })
      )
    )
    ElMessage.success(`已为 ${targets.length} 题添加标签 #${t}`)
    batchTag.value = ''
    loadList()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '批量打标签失败')
  }
}

async function batchRemove() {
  if (!selectedIds.value.size) {
    ElMessage.warning('请先勾选题目')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.size} 题？`, '批量删除', { type: 'warning' })
  } catch { return }
  try {
    const r = await batchDeleteQuestions([...selectedIds.value])
    ElMessage.success(`已删除 ${r.deleted} 题`)
    selectedIds.value = new Set()
    tableRef.value?.clearSelection()
    loadStats()
    loadList()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '批量删除失败')
  }
}

// ---------- 导入 ----------
const importVisible = ref(false)
const importText = ref('')
const pickedFile = ref<File | null>(null)
const importing = ref(false)

function onFilePick(file: { raw?: File }) {
  pickedFile.value = file.raw || null
}

async function doImport() {
  importing.value = true
  try {
    if (pickedFile.value) {
      const name = pickedFile.value.name.toLowerCase()
      if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
        const items = await parseExcelImport(pickedFile.value)
        if (!items.length) {
          ElMessage.warning('未从 Excel 解析到有效题目，请检查表头是否为「分类/难度/题干/答案/核心要点/标签/来源」')
          return
        }
        const r = await importQuestions(items)
        ElMessage.success(`导入 ${r.inserted} 条，跳过 ${r.skipped} 条`)
        importVisible.value = false
        loadStats()
        loadList()
        return
      }
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
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
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
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  }
}

async function doExportExcel() {
  try {
    await downloadExcelExport({
      category: filterCategory.value || undefined,
      difficulty: filterDifficulty.value || undefined,
      keyword: keyword.value || undefined
    })
    exportVisible.value = false
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '导出失败')
  }
}

/** 下载 Excel 导入模板（纯前端生成，含示例行） */
async function downloadImportTemplate() {
  try {
    const XLSX = await import('xlsx')
    const ws = XLSX.utils.json_to_sheet([
      {
        分类: '前端',
        难度: '简单',
        题干: 'Vue 中 computed 和 watch 的区别？',
        答案: 'computed 是计算属性，基于依赖缓存……',
        核心要点: '缓存机制、使用场景、副作用处理',
        标签: 'Vue,响应式',
        来源: '示例（此行可删除）'
      }
    ], { header: ['分类', '难度', '题干', '答案', '核心要点', '标签', '来源'] })
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '面试题模板')
    ws['!cols'] = [{ wch: 10 }, { wch: 8 }, { wch: 36 }, { wch: 60 }, { wch: 30 }, { wch: 18 }, { wch: 16 }]
    XLSX.writeFile(wb, '面试题导入模板.xlsx')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '模板下载失败')
  }
}

// ---------- AI 生成 ----------
const aiVisible = ref(false)
/** AI 出题入库后：回到第 1 页刷新，新题按 updated_at 排序自然置顶 */
function onAiImported() {
  page.value = 1
  loadStats()
  loadList()
}

// ---------- 模拟刷题 ----------
const quizCategories = ref<InterviewCategory[]>([])
const quizDifficulties = ref<Difficulty[]>([])
const quizTags = ref<string[]>([])
const quizCount = ref(10)
const quizLoading = ref(false)
const quizStarted = ref(false)
const quizList = ref<InterviewQuestion[]>([])
const quizIndex = ref(0)
const quizAnswer = ref('')
const quizReveal = ref<string[]>([])
const currentQuiz = computed(() => quizList.value[quizIndex.value] || null)

async function startQuiz() {
  quizLoading.value = true
  try {
    const items = await fetchQuizQuestions({
      categories: quizCategories.value.length ? quizCategories.value : undefined,
      difficulties: quizDifficulties.value.length ? quizDifficulties.value : undefined,
      tags: quizTags.value.length ? quizTags.value : undefined,
      count: quizCount.value
    })
    if (!items.length) {
      ElMessage.warning('没有符合条件的题目')
      return
    }
    quizList.value = items
    quizIndex.value = 0
    quizAnswer.value = ''
    quizReveal.value = []
    quizStarted.value = true
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '抽题失败')
  } finally {
    quizLoading.value = false
  }
}

async function nextQuiz() {
  if (!currentQuiz.value) return
  try {
    await saveQuizRecords([
      { questionId: currentQuiz.value.id, userAnswer: quizAnswer.value, score: quizReveal.value.includes('answer') ? 1 : 0 }
    ])
  } catch { /* 记录失败不影响刷题 */ }
  quizIndex.value += 1
  quizAnswer.value = ''
  quizReveal.value = []
}

async function confirmExitQuiz() {
  try {
    await ElMessageBox.confirm('退出后将结束本次刷题，已作答题目计入练习记录。', '退出刷题', { type: 'info' })
  } catch { return }
  if (currentQuiz.value && quizIndex.value < quizList.value.length - 1) {
    try {
      await saveQuizRecords([
        { questionId: currentQuiz.value.id, userAnswer: quizAnswer.value, score: quizReveal.value.includes('answer') ? 1 : 0 }
      ])
    } catch { /* 忽略 */ }
  }
  quizStarted.value = false
  quizList.value = []
  loadStats()
}
</script>

<style scoped>
.page-interview { max-width: 1280px; margin: 0 auto; }

/* ---------- Hero ---------- */
.hero {
  display: flex; justify-content: space-between; align-items: center;
  gap: 16px; flex-wrap: wrap; margin-bottom: 24px;
}
.hero-title { display: flex; align-items: center; gap: 10px; font-size: 26px; margin: 0; }
.hero-sub { color: var(--c-text-mute); margin: 6px 0 0; }
.hero-right { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }

/* ---------- 布局 ---------- */
.bank-layout { display: flex; gap: 20px; align-items: flex-start; }
.side-panel {
  width: 230px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px;
  position: sticky; top: 76px;
}
.side-block { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 10px; padding: 14px; }
.side-title { margin: 0 0 10px; font-size: 13px; color: var(--c-text-mute); }
.side-list { display: flex; flex-direction: column; gap: 2px; }
.side-item {
  display: flex; align-items: center; gap: 8px;
  background: none; border: none; padding: 7px 8px; border-radius: 6px;
  cursor: pointer; font-size: 13px; color: var(--c-text); text-align: left; width: 100%;
}
.side-item:hover { background: var(--c-hover); }
.side-item.active { background: var(--c-primary-soft); color: var(--c-primary); font-weight: 600; }
.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.side-count { margin-left: auto; font-size: 12px; color: var(--c-text-mute); }

/* ---------- 列表 ---------- */
.list-main { min-width: 0; flex: 1; }
.list-toolbar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.batch-tip { font-style: normal; color: var(--c-text-mute); margin-left: auto; font-size: 12px; }
.batch-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: var(--c-primary-soft); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;
}
.q-table-wrap { background: var(--c-bg-soft); border-radius: 10px; overflow: hidden; }
.q-table { width: 100%; }
.cell-title { font-weight: 500; }
.cell-muted { color: var(--c-text-mute); }
.cell-tags { display: flex; flex-wrap: nowrap; gap: 4px; overflow: hidden; }
.tag { color: var(--c-text-mute); font-size: 12px; flex-shrink: 0; }
.tag-cat { color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; display: inline-block; }
.tag-diff { font-size: 12px; font-weight: 600; }
.cell-actions { display: flex; align-items: center; gap: 2px; justify-content: center; }
.fav-icon { font-size: 18px; cursor: pointer; color: var(--c-text-mute); margin-right: 2px; }
.fav-icon.active { color: #f59e0b; }
.empty-state { text-align: center; padding: 60px 20px; color: var(--c-text-mute); }
.pagination { margin-top: 20px; display: flex; justify-content: center; }

:deep(.q-table .el-table__row) { cursor: pointer; }
:deep(.q-table .row-selected) { background-color: var(--c-primary-soft) !important; }
:deep(.q-table .el-table__cell) { padding: 8px 0; }

/* ---------- 编辑表单 ---------- */
.edit-form { display: flex; flex-direction: column; gap: 14px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-row { display: flex; flex-direction: column; gap: 6px; }
.form-row label { font-size: 13px; font-weight: 500; }
.req { color: #ef4444; font-style: normal; }

/* ---------- 导入提示 ---------- */
.import-tip {
  background: var(--c-bg-soft); border-radius: 8px; padding: 10px 14px;
  font-size: 12.5px; color: var(--c-text-mute); line-height: 1.8; margin: 0 0 12px;
}
.import-tip code { background: var(--c-code-bg, #eee); padding: 1px 5px; border-radius: 4px; font-size: 12px; }

/* ---------- 刷题 ---------- */
.quiz-layout { max-width: 860px; margin: 0 auto; }
.quiz-config {
  background: var(--c-bg-soft); border: 1px solid var(--c-border);
  border-radius: 12px; padding: 24px; max-width: 480px; margin: 0 auto;
  display: flex; flex-direction: column; gap: 14px;
}
.quiz-config h3 { margin: 0; }
.quiz-panel { display: flex; flex-direction: column; gap: 14px; }
.quiz-head { display: flex; justify-content: space-between; align-items: center; }
.quiz-progress { color: var(--c-text-mute); font-size: 14px; }
.quiz-card {
  background: var(--c-bg-soft); border: 1px solid var(--c-border);
  border-radius: 12px; padding: 24px;
}
.quiz-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.quiz-title { margin: 0 0 6px; font-size: 20px; line-height: 1.5; }
.quiz-answer { margin: 0; line-height: 1.8; white-space: pre-wrap; }
.quiz-kp-title { font-weight: 600; margin: 14px 0 4px; color: var(--c-primary); }
.quiz-kp {
  margin: 0; line-height: 1.8; white-space: pre-wrap;
  background: var(--c-primary-soft); border-radius: 8px; padding: 10px 14px;
}

/* ---------- 响应式 ---------- */
@media (max-width: 900px) {
  .bank-layout { flex-direction: column; }
  .side-panel { width: 100%; position: static; flex-direction: row; flex-wrap: wrap; }
  .side-block { flex: 1; min-width: 200px; }
}
</style>
