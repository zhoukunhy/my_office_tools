<script setup lang="ts">
/**
 * 大纲确认与修改：页列表手动编辑 + AI 按反馈修改（可聚焦某一页，支持多轮）
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { LAYOUT_LABELS } from '@/types/aiPpt'
import type { SlideLayout } from '@/types/aiPpt'
import { useAiPpt } from '@/composables/useAiPpt'

const { state, revising, reviseOutline, startGenerate } = useAiPpt()

const feedback = ref('')
const focusIndex = ref<number | 0>(0)

const layoutOptions = Object.entries(LAYOUT_LABELS).map(([value, label]) => ({ value: value as SlideLayout, label }))
const focusOptions = computed(() => [
  { value: 0, label: '全部页面（整体调整）' },
  ...(state.outline?.pages ?? []).map((p) => ({ value: p.index, label: `只改第 ${p.index} 页：${p.title.slice(0, 12)}` }))
])

function removePage(index: number) {
  if (!state.outline) return
  if (state.outline.pages.length <= 3) {
    ElMessage.warning('大纲至少保留 3 页')
    return
  }
  state.outline.pages = state.outline.pages.filter((p) => p.index !== index).map((p, i) => ({ ...p, index: i + 1 }))
}

function addPage(afterIndex: number) {
  if (!state.outline) return
  const pages = [...state.outline.pages]
  pages.splice(afterIndex, 0, { index: 0, title: '新页面标题', layout: 'content', brief: '这一页要讲什么' })
  state.outline.pages = pages.map((p, i) => ({ ...p, index: i + 1 }))
}

async function doRevise() {
  await reviseOutline(feedback.value, focusIndex.value || undefined)
  feedback.value = ''
}

function doGenerate() {
  if (!state.outline?.pages.length) {
    ElMessage.warning('大纲为空，无法生成')
    return
  }
  startGenerate()
}
</script>

<template>
  <div v-if="state.outline" class="outline-editor">
    <div class="deck-meta">
      <label>演示标题<input v-model="state.outline.title" /></label>
      <label>副标题<input v-model="state.outline.subtitle" /></label>
    </div>

    <div class="page-list">
      <div v-for="p in state.outline.pages" :key="p.index" class="page-row">
        <span class="page-no">{{ p.index }}</span>
        <select v-model="p.layout" class="layout-select" title="版式">
          <option v-for="opt in layoutOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <div class="page-fields">
          <input v-model="p.title" placeholder="页面标题" />
          <input v-model="p.brief" placeholder="本页要点说明（AI 生成内容时参考）" />
        </div>
        <div class="row-actions">
          <button title="在此页后插入一页" @click="addPage(p.index)"><el-icon><Plus /></el-icon></button>
          <button title="删除此页" class="danger" @click="removePage(p.index)"><el-icon><Delete /></el-icon></button>
        </div>
      </div>
    </div>

    <div class="revise-box">
      <div class="revise-head">
        <h3><el-icon><MagicStick /></el-icon> 让 AI 修改大纲</h3>
        <select v-model="focusIndex" class="focus-select">
          <option v-for="opt in focusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <textarea v-model="feedback" rows="2" placeholder="例如：第3页拆成两页详细讲；整体风格更偏技术汇报；把结论提前…" />
      <div class="revise-foot">
        <span class="tip">可反复修改，满意后再生成</span>
        <div class="btns">
          <button class="btn-ghost-btn" :disabled="revising" @click="doRevise">
            <el-icon v-if="!revising"><MagicStick /></el-icon><el-icon v-else class="is-loading"><Loading /></el-icon>
            {{ revising ? '修改中…' : 'AI 修改大纲' }}
          </button>
          <button class="btn-primary-btn" @click="doGenerate"><el-icon><CaretRight /></el-icon>确认大纲，开始生成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.outline-editor { display: flex; flex-direction: column; gap: 16px; }
.deck-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.deck-meta label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--c-text-soft); }
.deck-meta input { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); padding: 9px 11px; border-radius: 6px; font-size: 13px; outline: none; }
.deck-meta input:focus { border-color: var(--c-primary); }
.page-list { display: flex; flex-direction: column; gap: 8px; max-height: 340px; overflow: auto; padding-right: 4px; }
.page-row { display: flex; align-items: center; gap: 8px; border: 1px solid var(--c-border); border-radius: 8px; padding: 8px 10px; background: var(--c-bg-soft); }
.page-no { width: 26px; height: 26px; border-radius: 50%; background: var(--c-primary-soft); color: var(--c-primary); font-size: 12px; font-weight: 700; display: grid; place-items: center; flex-shrink: 0; }
.layout-select { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 6px; padding: 5px 6px; font-size: 12px; flex-shrink: 0; }
.page-fields { flex: 1; display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.page-fields input { border: 1px solid transparent; background: transparent; color: var(--c-text); padding: 4px 8px; border-radius: 5px; font-size: 13px; outline: none; }
.page-fields input:first-child { font-weight: 600; }
.page-fields input:hover, .page-fields input:focus { border-color: var(--c-border); background: var(--c-card); }
.page-fields input:focus { border-color: var(--c-primary); }
.row-actions { display: flex; gap: 4px; flex-shrink: 0; }
.row-actions button { border: 0; background: none; color: var(--c-text-mute); cursor: pointer; padding: 5px; border-radius: 5px; display: grid; place-items: center; }
.row-actions button:hover { background: var(--c-bg-soft); color: var(--c-primary); }
.row-actions button.danger:hover { color: #dc2626; }
.revise-box { border: 1px dashed var(--c-border); border-radius: 10px; padding: 14px; background: var(--c-bg-soft); }
.revise-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 9px; flex-wrap: wrap; }
.revise-head h3 { margin: 0; font-size: 14px; display: flex; align-items: center; gap: 6px; color: var(--c-primary); }
.focus-select { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 6px; padding: 6px 8px; font-size: 12px; max-width: 260px; }
.revise-box textarea { width: 100%; border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 8px; padding: 10px 12px; font-size: 13px; resize: vertical; outline: none; box-sizing: border-box; }
.revise-box textarea:focus { border-color: var(--c-primary); }
.revise-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; gap: 10px; flex-wrap: wrap; }
.tip { font-size: 11px; color: var(--c-text-mute); }
.btns { display: flex; gap: 9px; }
.btn-ghost-btn, .btn-primary-btn { border: 0; padding: 9px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; display: inline-flex; align-items: center; gap: 6px; }
.btn-ghost-btn { background: var(--c-bg-soft); color: var(--c-primary); border: 1px solid var(--c-border); }
.btn-ghost-btn:disabled { opacity: 0.6; cursor: wait; }
.btn-primary-btn { background: var(--c-primary); color: #fff; }
.btn-primary-btn:hover { background: var(--c-primary-hover); }
@media (max-width: 600px) {
  .deck-meta { grid-template-columns: 1fr; }
  .page-row { flex-wrap: wrap; }
  .page-fields { width: 100%; order: 5; }
}
</style>
