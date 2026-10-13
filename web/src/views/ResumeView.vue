<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ResumePaper from '@/components/common/ResumePaper.vue'
import { extractResumeText, isSupportedResumeFile, parseResumeText } from '@/composables/useResumeParse'
import type { ParsedEntry, ParsedResume, ResumeItem, ResumeSection } from '@/composables/useResumeParse'

const templates = [
  { id: 'signal', name: 'Signal 信号', label: '理性清晰', accent: '#4f6eff', layout: 'clean' },
  { id: 'atelier', name: 'Atelier 工作室', label: '蓝调编辑', accent: '#3268b8', layout: 'editorial' },
  { id: 'mono', name: 'Mono 极简', label: '克制高级', accent: '#263c78', layout: 'mono' },
  { id: 'harbor', name: 'Harbor 通栏', label: '通用 · 稳重', accent: '#0f766e', layout: 'sidebar' },
  { id: 'classic', name: 'Classic 经典', label: '通用 · 正式', accent: '#8a4b2d', layout: 'classic' },
  { id: 'pulse', name: 'Pulse 时间线', label: '通用 · 经历导向', accent: '#6d28d9', layout: 'timeline' }
]

const activeTemplate = ref('signal')
const step = ref(1)
const nextId = ref(4)
const visibleSections = reactive<Record<ResumeSection, boolean>>({
  experience: true,
  projects: true,
  education: true
})

const profile = reactive({
  name: '林晓',
  role: '产品设计师',
  email: 'hello@linxiao.design',
  phone: '138 0000 0000',
  location: '上海 · 可远程',
  summary: '专注于将复杂问题转化为清晰、好用的数字体验，擅长从 0 到 1 构建产品与设计系统。'
})

const sections = reactive<Record<ResumeSection, ResumeItem[]>>({
  experience: [
    { id: 1, title: '高级产品设计师', organization: '澄明科技', period: '2022.03 — 至今', description: '负责企业协作产品体验，推动设计系统落地，帮助核心流程转化率提升 32%。' },
    { id: 2, title: '产品设计师', organization: '方寸工作室', period: '2019.07 — 2022.02', description: '参与 B 端与 C 端项目全流程，从用户研究到交付建立统一的体验标准。' }
  ],
  projects: [
    { id: 3, title: '协作空间 2.0', organization: '产品设计 · 体验策略', period: '2023', description: '重新设计信息架构与协作流程，覆盖 6 个核心场景，发布后周活提升 41%。' }
  ],
  education: [
    { id: 4, title: '视觉传达设计 · 学士', organization: '东海大学', period: '2015 — 2019', description: '主修品牌系统、交互设计与信息可视化。' }
  ]
})

const active = computed(() => templates.find((item) => item.id === activeTemplate.value) || templates[0])

const previewTemplateId = ref<string | null>(null)
const previewingTemplate = computed(() => templates.find((item) => item.id === previewTemplateId.value) || null)

function openPreview(id: string) {
  activeTemplate.value = id
  previewTemplateId.value = id
}

function usePreviewTemplate() {
  previewTemplateId.value = null
}

const importing = ref(false)
const importInput = ref<HTMLInputElement | null>(null)

function applyImported(parsed: ParsedResume): number {
  const p = parsed.profile
  if (p.name) profile.name = p.name
  if (p.role) profile.role = p.role
  if (p.email) profile.email = p.email
  if (p.phone) profile.phone = p.phone
  if (p.location) profile.location = p.location
  if (p.summary) profile.summary = p.summary
  const grouped: Record<ResumeSection, ParsedEntry[]> = {
    experience: parsed.experience,
    projects: parsed.projects,
    education: parsed.education
  }
  let count = 0
  ;(Object.keys(grouped) as ResumeSection[]).forEach((key) => {
    const list = grouped[key]
    if (!list.length) return
    visibleSections[key] = true
    sections[key] = list.map((entry) => ({ id: nextId.value++, ...entry }))
    count += list.length
  })
  return count
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || importing.value) return
  if (!isSupportedResumeFile(file.name)) {
    ElMessage.error('仅支持 .docx / .doc / .pdf / .txt 格式的简历文件')
    return
  }
  importing.value = true
  try {
    const text = await extractResumeText(file)
    const parsed = parseResumeText(text)
    const count = applyImported(parsed)
    if (!count && !parsed.profile.name && !parsed.profile.email && !parsed.profile.phone) {
      ElMessage.warning('未能自动识别出简历内容，请手动检查或填写')
    } else {
      goStep(1)
      ElMessage.success(`导入成功，已识别 ${count} 段经历，请核对并修改`)
    }
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '简历解析失败，请重试或手动填写')
  } finally {
    importing.value = false
  }
}
const enabledSectionCount = computed(() => Object.values(visibleSections).filter(Boolean).length)
const sectionKeys: ResumeSection[] = ['experience', 'projects', 'education']
const visibleSectionKeys = computed(() => sectionKeys.filter((section) => visibleSections[section]))

function addItem(section: ResumeSection) {
  sections[section].push({ id: nextId.value++, title: '新的经历标题', organization: '组织名称', period: '时间段', description: '补充你做了什么，以及它带来了怎样的结果。' })
  ElMessage.success('已新增一段内容')
}

function removeItem(section: ResumeSection, id: number) {
  sections[section] = sections[section].filter((item) => item.id !== id)
}

function addSection() {
  const hidden = (Object.keys(visibleSections) as ResumeSection[]).find((key) => !visibleSections[key])
  if (hidden) {
    visibleSections[hidden] = true
    ElMessage.success(`已恢复${sectionLabel(hidden)}模块`)
  } else {
    ElMessage.info('当前模板已包含全部推荐模块')
  }
}

function sectionLabel(section: ResumeSection) {
  return { experience: '工作经历', projects: '项目经历', education: '教育背景' }[section]
}

function goStep(target: number) {
  step.value = Math.max(1, Math.min(3, target))
}

function generateResume() {
  // 打印期间改标题：避免页眉出现"简历制作 通用工具箱"，另存 PDF 的默认文件名变成姓名
  // （壳层隐藏由全局打印样式的 :has(.resume-page) 规则自动完成，不依赖 JS 挂类）
  const originalTitle = document.title
  const name = profile.name?.trim()
  document.title = name ? `${name}的个人简历` : '个人简历'
  window.print()
  document.title = originalTitle
}
</script>

<template>
  <div class="resume-page">
    <section class="resume-hero">
      <div class="container-page resume-hero-inner">
        <div>
          <p class="resume-kicker">RESUME STUDIO / 01</p>
          <h1>把经历，整理成一份<br /><em>值得被看见的简历。</em></h1>
          <p class="resume-lead">挑一个适合你的版式，按步骤填入内容。所有编辑都在浏览器本地完成。</p>
        </div>
        <div class="resume-hero-note"><span>6</span><small>套精选模板<br />即时预览</small></div>
      </div>
    </section>

    <main class="container-page resume-main">
      <section class="template-section">
        <div class="section-heading"><div><span class="eyebrow">01 / START WITH A SHAPE</span><h2>选择你的模板</h2></div><span class="heading-note">点击卡片查看大图预览</span></div>
        <div class="template-grid">
          <button v-for="template in templates" :key="template.id" class="template-card" :class="{ selected: activeTemplate === template.id }" @click="openPreview(template.id)">
            <div class="template-thumb" :class="`thumb-${template.layout}`" :style="{ '--accent': template.accent }"><div class="thumb-name">林晓</div><div class="thumb-line"></div><div class="thumb-columns"><i></i><i></i><i></i></div></div>
            <div class="template-meta"><span><strong>{{ template.name }}</strong><small>{{ template.label }}</small></span><span class="template-check"><el-icon v-if="activeTemplate === template.id"><Check /></el-icon><el-icon v-else><ZoomIn /></el-icon></span></div>
          </button>
        </div>
      </section>

      <div class="studio-layout">
        <section class="editor-panel">
          <div class="section-heading editor-heading"><div><span class="eyebrow">02 / TELL YOUR STORY</span><h2>填写简历内容</h2></div><button class="text-action" @click="addSection"><el-icon><Plus /></el-icon>新增模块</button></div>
          <div class="step-tabs"><button v-for="item in [{ n: 1, label: '基本信息' }, { n: 2, label: '经历内容' }, { n: 3, label: '检查完成' }]" :key="item.n" :class="{ active: step === item.n, done: step > item.n }" @click="goStep(item.n)"><span>{{ item.n }}</span>{{ item.label }}</button></div>

          <div v-show="step === 1" class="form-content">
            <div class="import-bar">
              <div class="import-bar-text">
                <h3>已有简历？一键导入</h3>
                <p>支持 .docx / .doc / .pdf / .txt，自动识别并填充到下方表单，识别结果可继续修改。</p>
              </div>
              <button class="btn-secondary import-btn" :disabled="importing" @click="importInput?.click()">
                <el-icon v-if="!importing"><Upload /></el-icon>
                <el-icon v-else class="is-loading"><Loading /></el-icon>
                {{ importing ? '解析中…' : '导入简历文件' }}
              </button>
              <input ref="importInput" type="file" accept=".docx,.doc,.pdf,.txt" hidden @change="handleImportFile" />
            </div>
            <div class="form-intro"><h3>先让招聘者认识你</h3><p>保持简洁，把最重要的信息放在第一眼能看到的位置。</p></div>
            <div class="form-grid"><label>姓名<input v-model="profile.name" /></label><label>目标职位<input v-model="profile.role" /></label><label>邮箱<input v-model="profile.email" /></label><label>电话<input v-model="profile.phone" /></label><label class="full">所在地<input v-model="profile.location" /></label><label class="full">一句话介绍<textarea v-model="profile.summary" rows="3" /></label></div>
          </div>

          <div v-show="step === 2" class="form-content">
            <div class="form-intro"><h3>选择性地展示你的优势</h3><p>每个模块都可以删除，也可以继续新增多段经历。</p></div>
            <div v-for="section in sectionKeys" v-show="visibleSections[section]" :key="section" class="editor-section">
              <div class="subheading"><h3>{{ sectionLabel(section) }}</h3><button class="icon-action" :title="`删除${sectionLabel(section)}模块`" @click="visibleSections[section] = false"><el-icon><Delete /></el-icon></button></div>
              <div v-for="item in sections[section]" :key="item.id" class="entry-form"><div class="entry-fields"><input v-model="item.title" placeholder="职位 / 项目名称" /><input v-model="item.organization" placeholder="公司 / 组织" /><input v-model="item.period" placeholder="时间" /><textarea v-model="item.description" rows="2" placeholder="描述你的贡献与成果" /></div><button class="remove-entry" title="删除这段内容" @click="removeItem(section, item.id)"><el-icon><Close /></el-icon></button></div>
              <button class="add-entry" @click="addItem(section)"><el-icon><Plus /></el-icon>新增一段{{ sectionLabel(section) }}</button>
            </div>
          </div>

          <div v-show="step === 3" class="form-content complete-content"><div class="complete-mark"><el-icon><Check /></el-icon></div><h3>你的简历已经准备好了</h3><p>检查右侧预览中的信息，确认无误后即可生成 PDF。</p><div class="complete-stats"><span>{{ enabledSectionCount }} 个内容模块</span><span>本地实时预览</span><span>打印为 PDF</span></div></div>
          <div class="editor-footer"><button v-if="step > 1" class="btn-secondary" @click="goStep(step - 1)"><el-icon><ArrowLeft /></el-icon>上一步</button><button v-if="step < 3" class="btn-primary" @click="goStep(step + 1)">下一步<el-icon><ArrowRight /></el-icon></button><button v-else class="btn-primary" @click="generateResume"><el-icon><Download /></el-icon>生成简历</button></div>
        </section>

        <aside class="preview-panel"><div class="preview-toolbar"><div><span class="eyebrow">LIVE PREVIEW</span><h2>实时预览</h2></div><span class="preview-status"><i></i>自动保存</span></div><ResumePaper :profile="profile" :sections="sections" :visible-keys="visibleSectionKeys" :accent="active.accent" :layout="active.layout" /></aside>
      </div>
    </main>

    <el-dialog
      :model-value="!!previewingTemplate"
      width="760px"
      :title="previewingTemplate ? `${previewingTemplate.name} · ${previewingTemplate.label}` : ''"
      append-to-body
      @close="previewTemplateId = null"
    >
      <div v-if="previewingTemplate" class="preview-dialog-body">
        <ResumePaper
          :profile="profile"
          :sections="sections"
          :visible-keys="visibleSectionKeys"
          :accent="previewingTemplate.accent"
          :layout="previewingTemplate.layout"
        />
      </div>
      <template #footer>
        <button class="btn-secondary" @click="previewTemplateId = null">关闭</button>
        <button class="btn-primary" @click="usePreviewTemplate"><el-icon><Check /></el-icon>使用此模板</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.resume-page { min-height: 100vh; color: var(--c-text); background: var(--c-bg); }
.resume-hero { background: #172d62; color: #f6f8ff; position: relative; overflow: hidden; }
.resume-hero::after { content: ''; position: absolute; width: 38vw; height: 38vw; border: 1px solid rgba(238,198,126,.35); border-radius: 50%; right: 8%; top: -60%; }
.resume-hero-inner { min-height: 278px; display: flex; align-items: center; justify-content: space-between; padding-top: 36px; padding-bottom: 36px; position: relative; z-index: 1; }
.resume-kicker, .eyebrow { font-size: 10px; letter-spacing: .14em; font-weight: 700; color: var(--c-primary); }
.resume-hero h1 { font: 600 clamp(2rem, 4vw, 3.8rem)/1.08 Georgia, 'Times New Roman', serif; letter-spacing: 0; margin: 14px 0; }
.resume-hero h1 em { color: #9cb4ff; font-style: italic; }
.resume-lead { color: #c2cce8; max-width: 470px; line-height: 1.7; font-size: 14px; }
.resume-hero-note { display: flex; gap: 13px; align-items: center; color: #b4c6ff; border-left: 1px solid rgba(156,180,255,.5); padding-left: 20px; margin-right: 8%; }.resume-hero-note span { font: 55px Georgia, serif; }.resume-hero-note small { color: #c2cce8; line-height: 1.6; }
.resume-main { padding-top: 46px; padding-bottom: 70px; }.section-heading { display: flex; align-items: end; justify-content: space-between; margin-bottom: 18px; }.section-heading h2, .preview-toolbar h2 { font: 600 24px Georgia, serif; letter-spacing: 0; margin: 6px 0 0; }.heading-note { color: #8c918b; font-size: 12px; }
.template-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }.template-card { text-align: left; border: 1px solid #ded9d0; background: #faf8f4; padding: 10px; transition: .2s; cursor: pointer; }.template-card:hover, .template-card.selected { border-color: #b85c38; box-shadow: 0 8px 22px rgba(44,36,28,.1); transform: translateY(-2px); }.template-thumb { height: 130px; background: #fff; padding: 18px; border-bottom: 4px solid var(--accent); color: var(--accent); }.thumb-name { font: 19px Georgia, serif; border-bottom: 1px solid #d8d8d2; padding-bottom: 8px; }.thumb-line { width: 45%; height: 3px; background: var(--accent); margin-top: 13px; }.thumb-columns { display: flex; gap: 7px; margin-top: 13px; }.thumb-columns i { display: block; width: 27%; height: 4px; background: #d9d7d2; }.template-meta { display: flex; align-items: center; justify-content: space-between; padding: 10px 4px 2px; }.template-meta strong { display: block; font-size: 14px; }.template-meta small { color: #898b86; font-size: 11px; }.template-check { width: 22px; height: 22px; display: grid; place-items: center; border: 1px solid #d4cec4; color: #fff; }.selected .template-check { background: #b85c38; border-color: #b85c38; }
.studio-layout { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr); gap: 34px; margin-top: 54px; align-items: start; }.editor-panel, .preview-panel { background: #faf8f4; border-top: 3px solid #183a43; padding: 26px; }.editor-heading { margin-bottom: 23px; }.text-action, .add-entry { color: #a65032; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; background: none; border: 0; cursor: pointer; }.step-tabs { display: flex; gap: 4px; border-bottom: 1px solid #ded9d0; margin: 0 -26px; padding: 0 26px; }.step-tabs button { background: none; border: 0; padding: 12px 8px; color: #999b95; font-size: 12px; border-bottom: 2px solid transparent; cursor: pointer; }.step-tabs button span { border: 1px solid currentColor; width: 19px; height: 19px; border-radius: 50%; display: inline-grid; place-items: center; margin-right: 6px; font-size: 10px; }.step-tabs button.active { color: #a65032; border-bottom-color: #a65032; }.step-tabs button.done { color: #38736d; }.form-content { padding-top: 26px; min-height: 370px; }.form-intro h3, .subheading h3 { font-size: 15px; margin: 0 0 5px; }.form-intro p { color: #888d88; font-size: 12px; margin: 0 0 21px; }.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 12px; }.form-grid label { color: #6f746f; font-size: 11px; }.form-grid .full { grid-column: 1 / -1; }.form-grid input, .form-grid textarea, .entry-fields input, .entry-fields textarea { display: block; width: 100%; margin-top: 6px; border: 1px solid #ded9d0; background: #fff; padding: 10px 11px; color: #26343a; font: 13px inherit; outline: none; resize: vertical; }.form-grid input:focus, .form-grid textarea:focus, .entry-fields input:focus, .entry-fields textarea:focus { border-color: #b85c38; }.editor-section { margin-top: 25px; border-top: 1px solid #e4dfd7; padding-top: 17px; }.subheading { display: flex; justify-content: space-between; align-items: center; }.icon-action, .remove-entry { border: 0; background: none; color: #9a9d97; cursor: pointer; }.icon-action:hover, .remove-entry:hover { color: #b84e38; }.entry-form { display: flex; gap: 8px; margin-top: 12px; padding: 12px; background: #f3f0ea; }.entry-fields { display: grid; grid-template-columns: 1fr 1fr 90px; gap: 7px; flex: 1; }.entry-fields input, .entry-fields textarea { margin-top: 0; padding: 8px; font-size: 12px; }.entry-fields textarea { grid-column: 1 / -1; }.add-entry { margin-top: 12px; }.editor-footer { border-top: 1px solid #e4dfd7; padding-top: 18px; display: flex; justify-content: flex-end; gap: 9px; }.btn-secondary, .btn-primary { border: 0; padding: 10px 15px; display: inline-flex; align-items: center; gap: 7px; cursor: pointer; font-size: 12px; }.btn-secondary { background: #ebe7df; color: #596560; }.btn-primary { background: #183a43; color: #fff; }.btn-primary:hover { background: #2e6065; }.complete-content { text-align: center; padding-top: 55px; }.complete-mark { width: 52px; height: 52px; display: grid; place-items: center; background: #d8e7dd; color: #38736d; border-radius: 50%; margin: auto; font-size: 25px; }.complete-content h3 { font: 22px Georgia, serif; margin: 19px 0 8px; }.complete-content p { color: #888d88; font-size: 13px; }.complete-stats { display: flex; justify-content: center; gap: 13px; margin-top: 25px; color: #38736d; font-size: 11px; }
.preview-panel { background: #e7e1d7; padding: 18px; border-top-color: #b85c38; position: sticky; top: 76px; }.preview-toolbar { display: flex; justify-content: space-between; align-items: end; margin-bottom: 18px; }.preview-toolbar h2 { color: #1c2730; font-size: 18px; }.preview-status { font-size: 10px; color: #69766f; }.preview-status i { width: 6px; height: 6px; display: inline-block; background: #5da37e; border-radius: 50%; margin-right: 5px; }
.template-card:hover, .template-card.selected { border-color: var(--c-primary); box-shadow: 0 8px 22px rgba(44, 56, 105, .12); }
.template-thumb { background: var(--c-card); }.thumb-name { border-color: var(--c-border); }.thumb-columns i { background: var(--c-border); }.template-meta small { color: var(--c-text-mute); }.template-check { border-color: var(--c-border); }.selected .template-check { background: var(--c-primary); border-color: var(--c-primary); }
.editor-panel, .preview-panel { background: var(--c-card); border-top-color: var(--c-primary); }.text-action, .add-entry { color: var(--c-primary); }.step-tabs { border-color: var(--c-border); }.step-tabs button { color: var(--c-text-mute); }.step-tabs button.active { color: var(--c-primary); border-bottom-color: var(--c-primary); }
.form-intro p, .complete-content p { color: var(--c-text-mute); }.form-grid label { color: var(--c-text-soft); }.form-grid input, .form-grid textarea, .entry-fields input, .entry-fields textarea { border-color: var(--c-border); background: var(--c-card); color: var(--c-text); }.form-grid input:focus, .form-grid textarea:focus, .entry-fields input:focus, .entry-fields textarea:focus { border-color: var(--c-primary); }.editor-section, .editor-footer { border-color: var(--c-border); }.icon-action, .remove-entry { color: var(--c-text-mute); }.entry-form { background: var(--c-bg-soft); }.btn-secondary { background: var(--c-bg-soft); color: var(--c-text-soft); }.btn-primary { background: var(--c-primary); }.btn-primary:hover { background: var(--c-primary-hover); }.complete-mark { background: var(--c-primary-soft); color: var(--c-primary); }.complete-stats { color: var(--c-primary); }
.preview-panel { background: var(--c-bg-soft); border-top-color: var(--c-primary); }.preview-toolbar h2 { color: var(--c-text); }
@media (max-width: 900px) { .studio-layout { grid-template-columns: 1fr; }.preview-panel { position: static; } }
@media (max-width: 600px) { .resume-hero-inner { min-height: 250px; }.resume-hero-note { display: none; }.template-grid { grid-template-columns: 1fr; }.template-thumb { height: 110px; }.resume-main { padding-top: 32px; }.studio-layout { margin-top: 38px; }.editor-panel, .preview-panel { padding: 18px; }.step-tabs { margin: 0 -18px; padding: 0 18px; }.step-tabs button { flex: 1; padding-left: 0; padding-right: 0; }.form-grid { grid-template-columns: 1fr; }.form-grid .full { grid-column: auto; }.entry-fields { grid-template-columns: 1fr 1fr; }.entry-fields input:nth-child(3) { grid-column: 1 / -1; }.section-heading { align-items: start; }.heading-note { display: none; } .import-bar { flex-direction: column; align-items: stretch; } .import-btn { width: 100%; justify-content: center; } }
.import-bar { display: flex; justify-content: space-between; align-items: center; gap: 14px; border: 1px dashed var(--c-border); background: var(--c-bg-soft); padding: 14px 16px; margin-bottom: 20px; }.import-bar h3 { font-size: 14px; margin: 0 0 4px; }.import-bar p { color: var(--c-text-mute); font-size: 12px; margin: 0; line-height: 1.5; }.import-btn { flex-shrink: 0; }.import-btn:disabled { opacity: .6; cursor: wait; }
.thumb-sidebar .thumb-name { border-left: 3px solid var(--accent); border-bottom: 0; padding-left: 8px; }
.thumb-classic .thumb-name { text-align: center; }.thumb-classic .thumb-line { margin-left: auto; margin-right: auto; }
.thumb-timeline .thumb-columns { flex-direction: column; gap: 5px; }.thumb-timeline .thumb-columns i { width: 60%; height: 3px; }
.preview-dialog-body { max-height: 62vh; overflow: auto; background: var(--c-bg-soft); padding: 18px; }
</style>

<style>
/* 简历打印样式（全局）：用 :has() 自动检测简历页，点按钮或 Ctrl+P 均只输出简历纸张
   1) @page margin:0 → 浏览器页眉页脚（时间/标题/网址/横线）无渲染空间
   2) 壳层（导航/TabBar/网站页脚）与页面内非纸张区域全部隐藏 → 仅 1 页纸张 */
@page { size: A4; margin: 0; }
@media print {
  html, body { margin: 0 !important; padding: 0 !important; background: #fff !important; }
  /* body 直下：弹窗等传送门元素 */
  body:has(.resume-page) > *:not(#app) { display: none !important; }
  /* App 壳层：只保留 main 链（导航/TabBar/网站页脚全部隐藏） */
  body:has(.resume-page) #app > div > *:not(main) { display: none !important; }
  body:has(.resume-page) #app > div > main { padding: 0 !important; margin: 0 !important; }
  body:has(.resume-page) #app > div > main > *:not(.resume-page) { display: none !important; }
  body:has(.resume-page) #app > div > main > .resume-page { min-height: 0 !important; background: #fff !important; }
  /* 页面内部：只留预览纸张 */
  body:has(.resume-page) .resume-hero,
  body:has(.resume-page) .template-section,
  body:has(.resume-page) .editor-panel,
  body:has(.resume-page) .preview-toolbar,
  body:has(.resume-page) .import-bar { display: none !important; }
  body:has(.resume-page) .resume-main { padding: 0 !important; }
  body:has(.resume-page) .studio-layout { display: block !important; margin: 0 !important; }
  body:has(.resume-page) .preview-panel { display: block !important; position: static !important; padding: 0 !important; background: #fff !important; border: 0 !important; }
  body:has(.resume-page) .paper {
    width: 100% !important;
    min-height: 0 !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    margin: 0 !important;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }
}
</style>