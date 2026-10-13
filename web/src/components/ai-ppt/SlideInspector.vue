<script setup lang="ts">
/**
 * 幻灯片检查器：在线编辑当前页内容与版式、切换主题配色、AI 修复单页
 */
import { computed, ref } from 'vue'
import { LAYOUT_LABELS, THEME_PRESETS } from '@/types/aiPpt'
import type { SlideLayout } from '@/types/aiPpt'
import { useAiPpt } from '@/composables/useAiPpt'

const { state, fixing, fixPage } = useAiPpt()

const tab = ref<'content' | 'theme'>('content')
const fixFeedback = ref('')

const current = computed(() => state.slides.find((s) => s.index === state.activeIndex) ?? null)
const layoutOptions = Object.entries(LAYOUT_LABELS).map(([value, label]) => ({ value: value as SlideLayout, label }))

function addItem() {
  if (!current.value) return
  current.value.items.push({ title: '新要点', detail: '展开说明' })
  current.value._edited = true
}

function removeItem(i: number) {
  if (!current.value) return
  current.value.items.splice(i, 1)
  current.value._edited = true
}

function markEdited() {
  if (current.value) current.value._edited = true
}

function applyPreset(i: number) {
  state.theme = { ...THEME_PRESETS[i].theme }
}

async function doFix() {
  if (!current.value) return
  await fixPage(current.value, fixFeedback.value)
  fixFeedback.value = ''
}
</script>

<template>
  <div class="inspector">
    <div class="tabs">
      <button :class="{ active: tab === 'content' }" @click="tab = 'content'">页面内容</button>
      <button :class="{ active: tab === 'theme' }" @click="tab = 'theme'">主题配色</button>
    </div>

    <div v-if="tab === 'content'" class="pane">
      <template v-if="current">
        <div class="field-row">
          <label>版式</label>
          <select v-model="current.layout" @change="markEdited">
            <option v-for="opt in layoutOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <label class="field">标题<input v-model="current.title" @input="markEdited" /></label>
        <label v-if="current.layout === 'cover' || current.layout === 'end' || current.layout === 'quote'" class="field">副标题 / 出处<input v-model="current.subtitle" @input="markEdited" /></label>

        <div class="items-head">
          <span>要点列表</span>
          <button class="mini-btn" @click="addItem"><el-icon><Plus /></el-icon>加要点</button>
        </div>
        <div v-for="(it, i) in current.items" :key="i" class="item-edit">
          <div class="item-line">
            <input v-model="it.title" placeholder="要点标题" @input="markEdited" />
            <button class="del" title="删除该要点" @click="removeItem(i)"><el-icon><Close /></el-icon></button>
          </div>
          <textarea v-model="it.detail" rows="2" placeholder="展开说明（可留空）" @input="markEdited" />
        </div>
        <p v-if="!current.items.length" class="empty-tip">此版式不展示要点（封面/金句/结束页），可切换版式或直接填写标题副标题。</p>

        <label class="field">演讲者备注<textarea v-model="current.notes" rows="2" @input="markEdited" /></label>

        <div class="fix-box">
          <h4><el-icon><MagicStick /></el-icon> AI 修复此页</h4>
          <textarea v-model="fixFeedback" rows="2" placeholder="告诉 AI 这页有什么问题，例如：要点太多太挤，精简到3条；语气更正式；补充数据支撑…" />
          <button class="fix-btn" :disabled="fixing" @click="doFix">
            <el-icon v-if="!fixing"><RefreshRight /></el-icon><el-icon v-else class="is-loading"><Loading /></el-icon>
            {{ fixing ? '修复中…' : 'AI 重新生成此页' }}
          </button>
        </div>
      </template>
      <p v-else class="empty-tip">本页尚未生成完成，生成后即可编辑。</p>
    </div>

    <div v-else class="pane">
      <div class="presets">
        <button v-for="(p, i) in THEME_PRESETS" :key="p.name" class="preset" :class="{ active: state.theme.primary === p.theme.primary }" @click="applyPreset(i)">
          <span class="dot" :style="{ background: p.theme.primary }"></span>{{ p.name }}
        </button>
      </div>
      <label class="field">主题色<input type="color" v-model="state.theme.primary" @input="markEdited" /></label>
      <label class="field">页面背景<input type="color" v-model="state.theme.bg" @input="markEdited" /></label>
      <label class="field">正文颜色<input type="color" v-model="state.theme.text" @input="markEdited" /></label>
      <label class="field">次要文字<input type="color" v-model="state.theme.mute" @input="markEdited" /></label>
      <div class="field-row">
        <label>字体</label>
        <select v-model="state.theme.font">
          <option value="sans">无衬线（现代）</option>
          <option value="serif">衬线（典雅）</option>
        </select>
      </div>
      <p class="theme-tip">主题全局生效，所有页面实时预览；导出 PPTX 使用相同配色。</p>
    </div>
  </div>
</template>

<style scoped>
.inspector { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--c-border); margin-bottom: 12px; }
.tabs button { border: 0; background: none; padding: 9px 12px; font-size: 13px; color: var(--c-text-mute); cursor: pointer; border-bottom: 2px solid transparent; }
.tabs button.active { color: var(--c-primary); border-bottom-color: var(--c-primary); font-weight: 600; }
.pane { overflow: auto; display: flex; flex-direction: column; gap: 11px; padding-right: 4px; min-height: 0; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--c-text-soft); }
.field input, .field textarea, .field-row select { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 6px; padding: 8px 10px; font-size: 13px; outline: none; font-family: inherit; }
.field textarea { resize: vertical; }
.field input:focus, .field textarea:focus, .field-row select:focus { border-color: var(--c-primary); }
.field input[type='color'] { height: 36px; padding: 3px; cursor: pointer; }
.field-row { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--c-text-soft); }
.items-head { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--c-text-soft); margin-top: 4px; }
.mini-btn { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-primary); border-radius: 6px; padding: 4px 9px; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 3px; }
.item-edit { border: 1px solid var(--c-border); border-radius: 8px; padding: 8px; display: flex; flex-direction: column; gap: 6px; background: var(--c-bg-soft); }
.item-line { display: flex; gap: 6px; }
.item-line input { flex: 1; border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 6px; padding: 7px 9px; font-size: 13px; font-weight: 600; outline: none; min-width: 0; }
.item-line input:focus { border-color: var(--c-primary); }
.item-edit textarea { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text-mute); border-radius: 6px; padding: 6px 9px; font-size: 12px; outline: none; resize: vertical; font-family: inherit; }
.item-edit textarea:focus { border-color: var(--c-primary); color: var(--c-text); }
.del { border: 0; background: none; color: var(--c-text-mute); cursor: pointer; padding: 4px; }
.del:hover { color: #dc2626; }
.empty-tip { font-size: 12px; color: var(--c-text-mute); text-align: center; padding: 14px 0; }
.fix-box { border: 1px dashed var(--c-border); border-radius: 10px; padding: 12px; margin-top: 6px; display: flex; flex-direction: column; gap: 8px; background: var(--c-bg-soft); }
.fix-box h4 { margin: 0; font-size: 13px; color: var(--c-primary); display: flex; align-items: center; gap: 5px; }
.fix-box textarea { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 8px; padding: 9px 11px; font-size: 13px; outline: none; resize: vertical; font-family: inherit; }
.fix-btn { border: 0; background: var(--c-primary); color: #fff; border-radius: 8px; padding: 9px; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.fix-btn:disabled { opacity: 0.6; cursor: wait; }
.presets { display: flex; flex-wrap: wrap; gap: 8px; }
.preset { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 20px; padding: 6px 12px; font-size: 12px; cursor: pointer; }
.preset.active { border-color: var(--c-primary); color: var(--c-primary); font-weight: 600; }
.preset .dot { width: 12px; height: 12px; border-radius: 50%; }
.theme-tip { font-size: 11px; color: var(--c-text-mute); }
</style>
