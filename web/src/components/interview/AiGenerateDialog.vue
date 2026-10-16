<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { INTERVIEW_CATEGORIES, DIFFICULTY_META, getCategoryMeta, type InterviewCategory } from '@/types/interview'
import { aiGenerateQuestions, importQuestions } from '@/composables/useInterviewBank'

const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{ (e: 'imported', count: number): void }>()

const form = ref({
  category: 'frontend' as InterviewCategory,
  difficulty: 'medium',
  count: 5,
  topic: '',
  extra: ''
})
const generating = ref(false)
const importing = ref(false)
const preview = ref<Array<Record<string, unknown>>>([])
const checked = ref<Set<number>>(new Set())

async function generate() {
  generating.value = true
  preview.value = []
  try {
    const items = await aiGenerateQuestions({
      category: form.value.category,
      difficulty: form.value.difficulty,
      count: form.value.count,
      topic: form.value.topic,
      extra: form.value.extra
    })
    preview.value = items
    checked.value = new Set(items.map((_, i) => i))
    ElMessage.success(`已生成 ${items.length} 题，请检查后确认入库`)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : 'AI 出题失败')
  } finally {
    generating.value = false
  }
}

function toggle(i: number) {
  const s = new Set(checked.value)
  if (s.has(i)) s.delete(i)
  else s.add(i)
  checked.value = s
}

// ---------- 题目详情 ----------
const detailVisible = ref(false)
const detailIdx = ref(-1)
const detailQ = computed(() => (detailIdx.value >= 0 ? preview.value[detailIdx.value] : null))
const detailKeyPoints = computed(() => {
  const q = detailQ.value as Record<string, unknown> | null
  return q ? String(q.keyPoints ?? q.key_points ?? '') : ''
})

function openDetail(i: number) {
  detailIdx.value = i
  detailVisible.value = true
}

function selectAll(v: boolean) {
  checked.value = v ? new Set(preview.value.map((_, i) => i)) : new Set()
}

async function confirmImport() {
  if (!checked.value.size) {
    ElMessage.warning('请至少勾选一道题')
    return
  }
  importing.value = true
  try {
    const items = preview.value.filter((_, i) => checked.value.has(i))
    const r = await importQuestions(items)
    ElMessage.success(`已入库 ${r.inserted} 题`)
    emit('imported', r.inserted)
    visible.value = false
    preview.value = []
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '入库失败')
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="AI 智能出题" width="760px" top="5vh" :close-on-click-modal="!generating">
    <div class="ai-form">
      <div class="form-row3">
        <div>
          <label>分类</label>
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in INTERVIEW_CATEGORIES" :key="c.id" :value="c.id" :label="c.name" />
          </el-select>
        </div>
        <div>
          <label>难度</label>
          <el-select v-model="form.difficulty" style="width: 100%">
            <el-option v-for="(m, k) in DIFFICULTY_META" :key="k" :value="k" :label="m.name" />
          </el-select>
        </div>
        <div>
          <label>数量</label>
          <el-input-number v-model="form.count" :min="1" :max="30" style="width: 100%" />
        </div>
      </div>
      <div class="form-row">
        <label>主题 / 知识点（留空 = 该分类高频考点）</label>
        <el-input v-model="form.topic" placeholder="例如：Vue3 响应式原理 / MySQL 索引优化 / RAG 检索策略" />
      </div>
      <div class="form-row">
        <label>补充要求（可选）</label>
        <el-input v-model="form.extra" type="textarea" :rows="2" placeholder="例如：偏向实际场景题；不要八股文；结合我司业务（电商）" />
      </div>
      <el-button type="primary" :icon="MagicStick" :loading="generating" @click="generate">
        {{ generating ? 'AI 出题中，约需 10~30 秒…' : '生成题目' }}
      </el-button>
      <p class="ai-note">需后端已配置 LLM（server/.env 中 LLM_API_KEY）。生成后可勾选再入库。</p>
    </div>

    <div v-if="preview.length" class="ai-preview">
      <div class="preview-head">
        <el-checkbox :model-value="checked.size === preview.length" @change="(v: unknown) => selectAll(!!v)">
          全选（已选 {{ checked.size }} / {{ preview.length }}）
        </el-checkbox>
      </div>
      <div v-for="(q, i) in preview" :key="i" class="preview-card" :class="{ checked: checked.has(i) }" @click="openDetail(i)">
        <div class="preview-meta">
          <span class="tag-cat" :style="{ background: getCategoryMeta(String(q.category)).color }">
            {{ getCategoryMeta(String(q.category)).name }}
          </span>
          <span class="tag-diff" :style="{ color: DIFFICULTY_META[(q.difficulty as keyof typeof DIFFICULTY_META)]?.color }">
            {{ DIFFICULTY_META[(q.difficulty as keyof typeof DIFFICULTY_META)]?.name ?? q.difficulty }}
          </span>
          <span v-for="t in (q.tags as string[]) || []" :key="t" class="tag">#{{ t }}</span>
          <el-checkbox :model-value="checked.has(i)" @click.stop @change="toggle(i)" />
        </div>
        <h4>{{ q.title }}</h4>
        <p>{{ q.answer }}</p>
        <span class="detail-hint">点击卡片查看详情</span>
      </div>
    </div>

    <!-- 题目详情弹窗（嵌套） -->
    <el-dialog v-model="detailVisible" title="题目详情" width="640px" top="8vh" append-to-body>
      <div v-if="detailQ" class="detail-body">
        <div class="preview-meta">
          <span class="tag-cat" :style="{ background: getCategoryMeta(String(detailQ.category)).color }">
            {{ getCategoryMeta(String(detailQ.category)).name }}
          </span>
          <span class="tag-diff" :style="{ color: DIFFICULTY_META[(detailQ.difficulty as keyof typeof DIFFICULTY_META)]?.color }">
            {{ DIFFICULTY_META[(detailQ.difficulty as keyof typeof DIFFICULTY_META)]?.name ?? detailQ.difficulty }}
          </span>
          <span v-for="t in (detailQ.tags as string[]) || []" :key="t" class="tag">#{{ t }}</span>
          <el-checkbox :model-value="checked.has(detailIdx)" @change="toggle(detailIdx)">勾选入库</el-checkbox>
        </div>
        <h3 class="detail-title">{{ detailQ.title }}</h3>
        <h4 class="detail-label">参考答案</h4>
        <p class="detail-text">{{ detailQ.answer || '（AI 未生成答案）' }}</p>
        <template v-if="detailKeyPoints">
          <h4 class="detail-label">面试核心要点</h4>
          <p class="detail-text kp">{{ detailKeyPoints }}</p>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button
        v-if="preview.length"
        type="primary"
        :loading="importing"
        :disabled="!checked.size"
        @click="confirmImport"
      >导入选中的 {{ checked.size }} 题</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.ai-form { display: flex; flex-direction: column; gap: 14px; }
.form-row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.form-row3 label, .form-row label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.ai-note { margin: 0; font-size: 12px; color: var(--c-text-mute); }
.ai-preview { margin-top: 18px; max-height: 46vh; overflow: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 4px; }
.preview-head { position: sticky; top: 0; background: var(--c-bg); padding: 6px 0; z-index: 1; }
.preview-card { border: 1px solid var(--c-border); border-radius: 8px; padding: 12px 14px; cursor: pointer; background: var(--c-bg-soft); }
.preview-card.checked { border-color: var(--c-primary); background: var(--c-primary-soft); }
.preview-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.tag-cat { color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.tag-diff { font-size: 12px; font-weight: 600; }
.tag { color: var(--c-text-mute); font-size: 12px; }
.preview-meta .el-checkbox { margin-left: auto; }
.preview-card h4 { margin: 0 0 6px; font-size: 14px; }
.preview-card p { margin: 0; font-size: 12px; color: var(--c-text-mute); line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.detail-hint { display: block; margin-top: 6px; font-size: 11px; color: var(--c-text-mute); opacity: .7; }

/* ---------- 详情弹窗 ---------- */
.detail-body { display: flex; flex-direction: column; gap: 8px; }
.detail-body .preview-meta { margin-bottom: 2px; }
.detail-body .preview-meta .el-checkbox { margin-left: auto; }
.detail-title { margin: 4px 0; font-size: 17px; line-height: 1.6; }
.detail-label { margin: 8px 0 0; font-size: 13px; color: var(--c-primary); }
.detail-text {
  margin: 0; font-size: 13.5px; line-height: 1.8; white-space: pre-wrap; word-break: break-word;
  background: var(--c-bg-soft); border-radius: 8px; padding: 10px 14px;
}
.detail-text.kp { background: var(--c-primary-soft); }
</style>
