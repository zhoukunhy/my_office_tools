<script setup lang="ts">
/**
 * AI 生成 PPT：主题/文档输入 → 大纲确认多轮修改 → 并发生成 → 预览编辑 → 导出 PPTX
 * 全程本地编辑，仅内容生成与文档提取调用后端
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SlideCanvas from '@/components/ai-ppt/SlideCanvas.vue'
import OutlineEditor from '@/components/ai-ppt/OutlineEditor.vue'
import SlideInspector from '@/components/ai-ppt/SlideInspector.vue'
import AutoTextarea from '@/components/common/AutoTextarea.vue'
import { extractDocText, useAiPpt } from '@/composables/useAiPpt'
import { LAYOUT_LABELS } from '@/types/aiPpt'
import type { Slide } from '@/types/aiPpt'

const { state, outlineLoading, task, exporting, genOutline, exportFile, resetAll, stopPolling } = useAiPpt()

const activeSlide = computed(() => state.slides.find((s) => s.index === state.activeIndex) ?? null)
const progressPercent = computed(() => {
  if (!task.value || !task.value.total) return 0
  return Math.round(((task.value.completed + task.value.failed) / task.value.total) * 100)
})

// ---- 长文档上传提取 ----
const docInput = ref<HTMLInputElement | null>(null)
const extracting = ref(false)

async function handleDocFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || extracting.value) return
  extracting.value = true
  try {
    const text = await extractDocText(file)
    state.docText = text.slice(0, 20000)
    if (text.length > 20000) ElMessage.info('文档较长，已截取前 2 万字参与大纲生成')
    else ElMessage.success(`文档已提取 ${text.length} 字`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '文档提取失败')
  } finally {
    extracting.value = false
  }
}

function clearDoc() {
  state.docText = ''
}

// ---- 页面导航 ----
function selectSlide(s: Slide) {
  state.activeIndex = s.index
  state.scrollMode = false
}

function stepTo(n: 1 | 2 | 3 | 4) {
  if (n <= 2 && !state.outline) return
  if (n >= 3 && !state.slides.length && n === 4) return
  state.step = n
}

const stepLabels = ['输入主题', '确认大纲', '并发生成', '预览导出'] as const
const stepReachable = computed(() => [true, !!state.outline, !!state.outline, state.slides.length > 0])

onMounted(() => window.addEventListener('beforeunload', stopPolling))
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', stopPolling)
  stopPolling()
})
</script>

<template>
  <div class="ai-ppt-page">
    <!-- 顶部横幅 -->
    <section class="ppt-hero">
      <div class="container-page ppt-hero-inner">
        <div>
          <p class="ppt-kicker">AI PPT STUDIO</p>
          <h1>从一个主题，到一份完整的<em>演示文稿</em></h1>
          <p class="ppt-lead">输入主题或长文档 → AI 生成逐页大纲 → 确认后并发生成每页 → 在线编辑 → 导出 PPTX</p>
        </div>
      </div>
    </section>

    <main class="container-page ppt-main">
      <!-- 步骤条 -->
      <div class="steps">
        <button v-for="(label, i) in stepLabels" :key="label" :disabled="!stepReachable[i]" :class="{ active: state.step === i + 1, done: state.step > i + 1 }" @click="stepTo((i + 1) as 1 | 2 | 3 | 4)">
          <span>{{ i + 1 }}</span>{{ label }}
        </button>
        <button class="reset-btn" title="清空全部，重新开始" @click="resetAll"><el-icon><RefreshLeft /></el-icon>重置</button>
      </div>

      <!-- Step 1 输入 -->
      <section v-show="state.step === 1" class="panel">
        <div class="panel-grid">
          <div class="panel-left">
            <label class="ipt">PPT 主题 *<input v-model="state.topic" placeholder="例如：2026 年新能源汽车行业趋势展望" maxlength="200" /></label>
            <label class="ipt">背景与场合（可选）<AutoTextarea v-model="state.background" placeholder="给谁看、什么场合、解决什么问题，例如：向公司管理层汇报 Q4 营销复盘，重点是问题归因与下一步预算申请…" /></label>
            <label class="ipt">主要内容（可选）<AutoTextarea v-model="state.content" placeholder="希望涵盖的重点、章节素材、必须提到的数据或结论；内容多会自动展开，放心输入…" /></label>
            <label class="ipt">风格要求（可选）<AutoTextarea v-model="state.style" :min-height="64" placeholder="如：商务简洁 / 学术严谨 / 活泼有梗；每页要点不超过 4 条；多用数据对比；结尾要有行动建议…" /></label>
            <div class="count-row">
              <span>目标页数：{{ state.pageCount }} 页</span>
              <el-slider v-model="state.pageCount" :min="4" :max="20" :step="1" style="width: 200px" />
            </div>
          </div>
          <div class="panel-right">
            <div class="doc-box">
              <h3><el-icon><Document /></el-icon> 长文档投喂（可选）</h3>
              <p>上传 .docx / .doc / .pdf / .txt，提取内容作为大纲素材，生成更贴合实际的提纲。</p>
              <template v-if="state.docText">
                <div class="doc-loaded"><el-icon><CircleCheckFilled /></el-icon>已提取 {{ state.docText.length }} 字</div>
                <div class="doc-actions">
                  <button class="ghost" @click="docInput?.click()"><el-icon><RefreshRight /></el-icon>换文件</button>
                  <button class="ghost danger" @click="clearDoc"><el-icon><Delete /></el-icon>清除</button>
                </div>
              </template>
              <button v-else class="upload-btn" :disabled="extracting" @click="docInput?.click()">
                <el-icon v-if="!extracting"><UploadFilled /></el-icon><el-icon v-else class="is-loading"><Loading /></el-icon>
                {{ extracting ? '提取中…' : '选择文档' }}
              </button>
              <input ref="docInput" type="file" accept=".docx,.doc,.pdf,.txt" hidden @change="handleDocFile" />
            </div>
          </div>
        </div>
        <div class="panel-foot">
          <span class="hint">大纲由 AI（langgraph）生成，约需 10~30 秒</span>
          <button class="primary" :disabled="outlineLoading" @click="genOutline">
            <el-icon v-if="!outlineLoading"><MagicStick /></el-icon><el-icon v-else class="is-loading"><Loading /></el-icon>
            {{ outlineLoading ? '正在生成大纲…' : '生成 PPT 大纲' }}
          </button>
        </div>
      </section>

      <!-- Step 2 大纲 -->
      <section v-show="state.step === 2" class="panel">
        <OutlineEditor />
      </section>

      <!-- Step 3 生成中 -->
      <section v-show="state.step === 3" class="panel gen-panel">
        <div class="gen-head">
          <h2><el-icon class="spin"><Loading /></el-icon> 正在并发生成各页内容…</h2>
          <span v-if="task" class="gen-stat">{{ task.completed + task.failed }} / {{ task.total }} 页完成（并发进行，已完成的可先点击查看）</span>
        </div>
        <el-progress :percentage="progressPercent" :stroke-width="14" striped striped-flow />
        <div v-if="task" class="gen-grid">
          <div v-for="p in [...task.pages].sort((a, b) => a.index - b.index)" :key="p.index" class="gen-cell" :class="p.status">
            <span class="gen-idx">{{ p.index }}</span>
            <span class="gen-status">
              {{ p.status === 'done' ? '完成' : p.status === 'failed' ? '失败' : '生成中' }}
              <el-icon v-if="p.status === 'done'" class="ok"><CircleCheckFilled /></el-icon>
              <el-icon v-else-if="p.status === 'failed'" class="bad"><CircleCloseFilled /></el-icon>
            </span>
          </div>
        </div>
        <p class="gen-tip">生成过程中可先返回大纲调整；页面完成后自动进入编辑视图，失败页可稍后单独重试。</p>
      </section>

      <!-- Step 4 预览编辑 -->
      <section v-show="state.step === 4" class="editor-layout">
        <!-- 左侧页面列表 -->
        <aside class="slide-list">
          <div class="list-head">页面（{{ state.slides.length }}）</div>
          <div class="list-body">
            <button v-for="s in state.slides" :key="s.index" class="slide-item" :class="{ active: state.activeIndex === s.index && !state.scrollMode }" @click="selectSlide(s)">
              <span class="slide-idx">{{ s.index }}</span>
              <SlideCanvas :slide="s" :theme="state.theme" mini class="slide-thumb" />
              <span class="slide-name">{{ LAYOUT_LABELS[s.layout] }} · {{ s.title.slice(0, 10) }}<i v-if="s._edited" class="edited-dot" title="已编辑"></i></span>
            </button>
          </div>
        </aside>

        <!-- 中间预览 -->
        <div class="preview-col">
          <div class="preview-tools">
            <div class="mode-toggle">
              <button :class="{ active: !state.scrollMode }" @click="state.scrollMode = false">单页预览</button>
              <button :class="{ active: state.scrollMode }" @click="state.scrollMode = true">滚动检查</button>
            </div>
            <div v-if="!state.scrollMode && state.slides.length" class="page-nav">
              <button :disabled="state.activeIndex <= 1" @click="state.activeIndex--"><el-icon><ArrowLeft /></el-icon></button>
              <span>{{ state.activeIndex }} / {{ state.slides.length }}</span>
              <button :disabled="state.activeIndex >= state.slides.length" @click="state.activeIndex++"><el-icon><ArrowRight /></el-icon></button>
            </div>
            <button class="export" :disabled="exporting" @click="exportFile">
              <el-icon v-if="!exporting"><Download /></el-icon><el-icon v-else class="is-loading"><Loading /></el-icon>
              {{ exporting ? '导出中…' : '导出 PPTX' }}
            </button>
          </div>
          <div class="preview-body">
            <template v-if="state.scrollMode">
              <div v-for="s in state.slides" :key="s.index" class="scroll-page" :class="{ current: s.index === state.activeIndex }" @click="state.activeIndex = s.index">
                <SlideCanvas :slide="s" :theme="state.theme" />
                <span class="scroll-idx">P{{ s.index }}</span>
              </div>
            </template>
            <template v-else-if="activeSlide">
              <SlideCanvas :slide="activeSlide" :theme="state.theme" class="big-canvas" />
              <p v-if="activeSlide.notes" class="notes"><el-icon><ChatLineSquare /></el-icon>{{ activeSlide.notes }}</p>
            </template>
            <div v-else class="preview-empty"><el-icon><DataBoard /></el-icon><p>暂无已生成的页面</p></div>
          </div>
        </div>

        <!-- 右侧编辑 -->
        <aside class="inspector-col">
          <SlideInspector />
        </aside>
      </section>
    </main>
  </div>
</template>

<style scoped>
.ai-ppt-page { min-height: 100vh; color: var(--c-text); background: var(--c-bg); }
.ppt-hero { background: linear-gradient(135deg, #4338ca 0%, #6d28d9 60%, #7c3aed 100%); color: #fff; }
.ppt-hero-inner { padding: 44px 0 40px; }
.ppt-kicker { font-size: 11px; letter-spacing: 0.18em; font-weight: 700; color: #c7d2fe; margin: 0; }
.ppt-hero h1 { font-size: clamp(24px, 3.4vw, 40px); margin: 12px 0 10px; line-height: 1.2; }
.ppt-hero h1 em { font-style: normal; color: #fbbf24; }
.ppt-lead { color: #ddd6fe; font-size: 14px; margin: 0; }
.ppt-main { padding: 26px 0 70px; }

.steps { display: flex; gap: 6px; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
.steps button { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text-mute); border-radius: 20px; padding: 7px 14px; font-size: 12px; cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
.steps button:disabled { opacity: 0.45; cursor: not-allowed; }
.steps button span { width: 18px; height: 18px; border-radius: 50%; border: 1px solid currentColor; display: grid; place-items: center; font-size: 10px; }
.steps button.active { background: var(--c-primary); border-color: var(--c-primary); color: #fff; font-weight: 600; }
.steps button.done { color: var(--c-primary); border-color: var(--c-primary); }
.steps .reset-btn { margin-left: auto; color: #dc2626; border-color: color-mix(in srgb, #dc2626 35%, transparent); }

.panel { background: var(--c-card); border: 1px solid var(--c-border); border-radius: 14px; padding: 22px; }
.panel-grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 22px; }
.panel-left { display: flex; flex-direction: column; gap: 14px; }
.ipt { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--c-text-soft); }
.ipt input, .ipt textarea { border: 1px solid var(--c-border); background: var(--c-bg-soft); color: var(--c-text); border-radius: 8px; padding: 10px 12px; font-size: 13px; outline: none; resize: vertical; font-family: inherit; }
.ipt input:focus, .ipt textarea:focus { border-color: var(--c-primary); }
.count-row { display: flex; align-items: center; gap: 14px; font-size: 13px; color: var(--c-text-soft); }
.doc-box { border: 1px dashed var(--c-border); border-radius: 12px; padding: 18px; background: var(--c-bg-soft); height: 100%; display: flex; flex-direction: column; gap: 10px; }
.doc-box h3 { margin: 0; font-size: 14px; display: flex; align-items: center; gap: 6px; color: var(--c-primary); }
.doc-box p { margin: 0; font-size: 12px; color: var(--c-text-mute); line-height: 1.6; }
.upload-btn { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-primary); border-radius: 8px; padding: 10px; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.upload-btn:disabled { opacity: 0.6; cursor: wait; }
.doc-loaded { font-size: 13px; color: #059669; display: flex; align-items: center; gap: 6px; }
.doc-actions { display: flex; gap: 8px; }
.ghost { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text-soft); border-radius: 7px; padding: 6px 12px; font-size: 12px; cursor: pointer; display: inline-flex; gap: 5px; align-items: center; }
.ghost.danger { color: #dc2626; }
.panel-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; gap: 12px; flex-wrap: wrap; }
.hint { font-size: 12px; color: var(--c-text-mute); }
button.primary { border: 0; background: var(--c-primary); color: #fff; border-radius: 9px; padding: 11px 22px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; }
button.primary:disabled { opacity: 0.65; cursor: wait; }

.gen-panel { display: flex; flex-direction: column; gap: 18px; }
.gen-head h2 { margin: 0; font-size: 18px; display: flex; align-items: center; gap: 8px; }
.gen-head .spin { animation: ppt-spin 1s linear infinite; }
@keyframes ppt-spin { to { transform: rotate(360deg); } }
.gen-stat { font-size: 13px; color: var(--c-text-mute); }
.gen-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 8px; }
.gen-cell { border: 1px solid var(--c-border); border-radius: 9px; padding: 9px 10px; display: flex; align-items: center; justify-content: space-between; font-size: 12px; background: var(--c-bg-soft); }
.gen-cell.running { color: var(--c-text-mute); }
.gen-cell.done { border-color: #059669; color: #059669; }
.gen-cell.failed { border-color: #dc2626; color: #dc2626; }
.gen-idx { font-weight: 700; }
.gen-status { display: inline-flex; align-items: center; gap: 3px; }
.gen-tip { margin: 0; font-size: 12px; color: var(--c-text-mute); }

.editor-layout { display: grid; grid-template-columns: 190px minmax(0, 1fr) 300px; gap: 14px; align-items: stretch; }
.slide-list { background: var(--c-card); border: 1px solid var(--c-border); border-radius: 12px; display: flex; flex-direction: column; min-height: 520px; max-height: calc(100vh - 200px); }
.list-head { padding: 10px 12px; font-size: 12px; font-weight: 600; color: var(--c-text-soft); border-bottom: 1px solid var(--c-border); }
.list-body { overflow: auto; padding: 8px; display: flex; flex-direction: column; gap: 8px; }
.slide-item { border: 2px solid transparent; background: var(--c-bg-soft); border-radius: 9px; padding: 6px; cursor: pointer; text-align: left; position: relative; }
.slide-item.active { border-color: var(--c-primary); }
.slide-idx { position: absolute; top: 10px; left: 12px; z-index: 2; font-size: 10px; background: rgba(0, 0, 0, 0.55); color: #fff; border-radius: 4px; padding: 1px 5px; }
.slide-thumb { border-radius: 5px; overflow: hidden; pointer-events: none; }
.slide-name { display: block; font-size: 11px; color: var(--c-text-mute); margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.edited-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--c-primary); margin-left: 4px; }

.preview-col { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.preview-tools { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mode-toggle { display: inline-flex; border: 1px solid var(--c-border); border-radius: 8px; overflow: hidden; }
.mode-toggle button { border: 0; background: var(--c-card); color: var(--c-text-mute); padding: 7px 13px; font-size: 12px; cursor: pointer; }
.mode-toggle button.active { background: var(--c-primary); color: #fff; }
.page-nav { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--c-text-soft); }
.page-nav button { border: 1px solid var(--c-border); background: var(--c-card); color: var(--c-text); border-radius: 7px; padding: 5px 8px; cursor: pointer; }
.page-nav button:disabled { opacity: 0.4; cursor: not-allowed; }
.export { margin-left: auto; border: 0; background: #059669; color: #fff; border-radius: 8px; padding: 9px 18px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.export:disabled { opacity: 0.6; cursor: wait; }
.preview-body { background: var(--c-bg-soft); border: 1px solid var(--c-border); border-radius: 12px; padding: 16px; overflow: auto; max-height: calc(100vh - 240px); display: flex; flex-direction: column; gap: 12px; }
.scroll-page { cursor: pointer; border: 2px solid transparent; border-radius: 8px; position: relative; }
.scroll-page.current { border-color: var(--c-primary); }
.scroll-idx { position: absolute; top: 8px; left: 8px; z-index: 2; font-size: 11px; background: rgba(0, 0, 0, 0.55); color: #fff; border-radius: 4px; padding: 1px 6px; }
.big-canvas { box-shadow: 0 10px 32px rgba(30, 30, 60, 0.14); border-radius: 6px; overflow: hidden; }
.notes { margin: 0; font-size: 12px; color: var(--c-text-mute); background: var(--c-card); border: 1px solid var(--c-border); border-radius: 8px; padding: 9px 12px; display: flex; gap: 6px; align-items: flex-start; line-height: 1.6; }
.preview-empty { margin: auto; text-align: center; color: var(--c-text-mute); font-size: 13px; padding: 60px 0; }
.preview-empty .el-icon { font-size: 34px; }

.inspector-col { background: var(--c-card); border: 1px solid var(--c-border); border-radius: 12px; padding: 12px; min-height: 520px; max-height: calc(100vh - 200px); display: flex; flex-direction: column; }

@media (max-width: 1100px) {
  .editor-layout { grid-template-columns: 1fr; }
  .slide-list { max-height: 260px; }
  .inspector-col { max-height: none; }
  .preview-body { max-height: none; }
}
@media (max-width: 720px) {
  .panel-grid { grid-template-columns: 1fr; }
  .count-row { flex-wrap: wrap; }
}
</style>
