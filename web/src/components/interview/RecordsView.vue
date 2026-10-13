<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Refresh } from '@element-plus/icons-vue'
import { INTERVIEW_CATEGORIES, DIFFICULTY_META, getCategoryMeta } from '@/types/interview'
import {
  listRecords, deleteRecord, getRecordStats, type QuizRecordItem
} from '@/composables/useInterviewBank'

const scope = ref<'wrong' | 'mastered' | 'all'>('wrong')
const category = ref('')
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const records = ref<QuizRecordItem[]>([])
const total = ref(0)
const stats = ref<{ total: number; by_score: Record<string, number>; wrong_by_category: Record<string, number> }>({
  total: 0, by_score: {}, wrong_by_category: {}
})

const SCORE_LABEL: Record<number, string> = { 0: '不会', 1: '一般', 2: '掌握', 3: '熟练' }

async function load() {
  loading.value = true
  try {
    const r = await listRecords({
      scope: scope.value,
      category: category.value || undefined,
      page: page.value,
      pageSize
    })
    records.value = r.items
    total.value = r.total
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '加载记录失败')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getRecordStats()
  } catch {
    /* 统计失败不阻塞列表 */
  }
}

async function remove(r: QuizRecordItem) {
  try {
    await ElMessageBox.confirm(
      r.score <= 1 ? '标记为已掌握并移出错题本？' : '删除该条问答记录？',
      '提示',
      { type: 'warning' }
    )
    await deleteRecord(r.id)
    ElMessage.success('已删除')
    loadStats()
    load()
  } catch {
    /* 取消 */
  }
}

onMounted(() => {
  loadStats()
  load()
})
</script>

<template>
  <div class="records-view">
    <div class="records-toolbar">
      <el-radio-group v-model="scope" @change="page = 1; load()">
        <el-radio-button value="wrong">错题本（{{ (stats.by_score?.['0'] || 0) + (stats.by_score?.['1'] || 0) }}）</el-radio-button>
        <el-radio-button value="mastered">已掌握（{{ (stats.by_score?.['2'] || 0) + (stats.by_score?.['3'] || 0) }}）</el-radio-button>
        <el-radio-button value="all">全部（{{ stats.total }}）</el-radio-button>
      </el-radio-group>
      <el-select v-model="category" placeholder="全部分类" clearable style="width: 150px" @change="page = 1; load()">
        <el-option v-for="c in INTERVIEW_CATEGORIES" :key="c.id" :value="c.id" :label="c.name" />
      </el-select>
      <el-button :icon="Refresh" @click="loadStats(); load()" />
    </div>

    <div v-loading="loading" class="records-list">
      <div v-if="!records.length && !loading" class="empty-state">
        <p>暂无{{ scope === 'wrong' ? '错题' : '' }}记录，去「问答模式」答题自评后会自动记录</p>
      </div>
      <div v-for="r in records" :key="r.id" class="record-card">
        <div class="record-head">
          <div class="record-meta">
            <template v-if="r.question">
              <span class="tag-cat" :style="{ background: getCategoryMeta(r.question.category).color }">
                {{ getCategoryMeta(r.question.category).name }}
              </span>
              <span class="tag-diff" :style="{ color: DIFFICULTY_META[r.question.difficulty].color }">
                {{ DIFFICULTY_META[r.question.difficulty].name }}
              </span>
            </template>
            <span class="score-badge" :class="r.score <= 1 ? 'bad' : 'good'">
              {{ SCORE_LABEL[r.score] ?? '未评' }}
            </span>
            <span class="record-date">{{ new Date(r.createdAt).toLocaleString() }}</span>
          </div>
          <el-button link type="danger" :icon="Delete" @click="remove(r)">
            {{ r.score <= 1 ? '标记掌握' : '删除' }}
          </el-button>
        </div>
        <h3 class="record-title">{{ r.question?.title || '（原题已删除）' }}</h3>
        <p v-if="r.userAnswer" class="record-answer"><strong>我的回答：</strong>{{ r.userAnswer }}</p>
        <p v-if="r.question?.answer" class="record-ref"><strong>参考答案：</strong>{{ r.question.answer }}</p>
      </div>
    </div>

    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="page"
        :total="total"
        :page-size="pageSize"
        layout="prev, pager, next, total"
        @current-change="load"
      />
    </div>
  </div>
</template>

<style scoped>
.records-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.records-list { display: flex; flex-direction: column; gap: 12px; }
.empty-state { text-align: center; padding: 60px 20px; color: var(--c-text-mute); }
.record-card { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 10px; padding: 16px 18px; }
.record-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 8px; }
.record-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tag-cat { color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.tag-diff { font-size: 12px; font-weight: 600; }
.score-badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.score-badge.bad { background: color-mix(in srgb, #ef4444 15%, transparent); color: #ef4444; }
.score-badge.good { background: color-mix(in srgb, #10b981 15%, transparent); color: #10b981; }
.record-date { color: var(--c-text-mute); font-size: 12px; }
.record-title { margin: 0 0 8px; font-size: 15px; }
.record-answer, .record-ref { margin: 6px 0 0; font-size: 13px; line-height: 1.6; }
.record-answer { color: var(--c-text-soft); }
.record-ref { color: var(--c-text-mute); white-space: pre-wrap; }
.pagination { margin-top: 20px; display: flex; justify-content: center; }
</style>
