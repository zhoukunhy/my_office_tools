<script setup lang="ts">
import { SECTION_LABELS } from '@/composables/useResumeParse'
import type { ResumeItem, ResumeProfile, ResumeSection } from '@/composables/useResumeParse'

defineProps<{
  profile: ResumeProfile
  sections: Record<ResumeSection, ResumeItem[]>
  visibleKeys: ResumeSection[]
  accent: string
  layout: string
}>()
</script>

<template>
  <div class="paper" :class="`paper-${layout}`" :style="{ '--accent': accent }">
    <header class="paper-header">
      <div class="paper-id">
        <h1>{{ profile.name }}</h1>
        <h2>{{ profile.role }}</h2>
      </div>
      <div class="paper-contact">
        {{ profile.email }}<br />
        {{ profile.phone }}<br />
        {{ profile.location }}
      </div>
    </header>
    <p v-if="profile.summary" class="paper-summary">{{ profile.summary }}</p>
    <section v-for="section in visibleKeys" :key="section" v-show="sections[section].length" class="paper-section">
      <h3>{{ SECTION_LABELS[section] }}</h3>
      <article v-for="item in sections[section]" :key="item.id">
        <div class="paper-entry-head">
          <strong>{{ item.title }}</strong>
          <span>{{ item.period }}</span>
        </div>
        <div class="paper-org">{{ item.organization }}</div>
        <p class="paper-desc">{{ item.description }}</p>
      </article>
    </section>
    <footer class="paper-footer">RESUME / {{ profile.name.toUpperCase() }}</footer>
  </div>
</template>

<style scoped>
.paper {
  background: #fff;
  min-height: 640px;
  padding: 42px 40px;
  color: #26333a;
  box-shadow: 0 8px 25px rgba(41, 32, 23, 0.13);
  font-size: 10px;
}
.paper-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid var(--accent);
  padding-bottom: 17px;
}
.paper-header h1 {
  font: 27px Georgia, serif;
  margin: 0 0 6px;
  color: var(--accent);
}
.paper-header h2 {
  font: 600 11px Arial, sans-serif;
  margin: 0;
  letter-spacing: 0.08em;
}
.paper-contact {
  color: #77807c;
  text-align: right;
  line-height: 1.7;
}
.paper-summary {
  line-height: 1.65;
  color: #596560;
  margin: 18px 0 21px;
}
.paper-section {
  margin-top: 18px;
}
.paper-section > h3 {
  color: var(--accent);
  font: 700 10px Arial, sans-serif;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border-bottom: 1px solid #e0e5df;
  padding-bottom: 6px;
  margin: 0 0 10px;
}
.paper-section article {
  margin-bottom: 12px;
}
.paper-entry-head {
  display: flex;
  justify-content: space-between;
}
.paper-entry-head strong {
  font-size: 11px;
}
.paper-entry-head span {
  color: #86908a;
}
.paper-org {
  color: var(--accent);
  margin-top: 3px;
}
.paper-desc {
  color: #68736e;
  line-height: 1.55;
  margin: 4px 0 0;
  white-space: pre-line;
}
.paper-footer {
  border-top: 1px solid #e0e5df;
  color: #a2aaa4;
  font-size: 8px;
  letter-spacing: 0.13em;
  margin-top: 28px;
  padding-top: 10px;
}
/* 版式：editorial 蓝调编辑 */
.paper-editorial .paper-header {
  border-bottom: 0;
}
.paper-editorial .paper-header h1 {
  font-style: italic;
}
/* 版式：mono 极简 */
.paper-mono {
  font-family: 'Courier New', monospace;
}
.paper-mono .paper-header h1 {
  font-family: 'Courier New', monospace;
  font-size: 21px;
}
/* 版式：sidebar 通栏侧栏感 */
.paper-sidebar .paper-header {
  display: block;
  background: color-mix(in srgb, var(--accent) 9%, #fff);
  border-bottom: 0;
  margin: -42px -40px 0;
  padding: 28px 40px 20px;
}
.paper-sidebar .paper-header h1 {
  font-size: 30px;
}
.paper-sidebar .paper-contact {
  text-align: left;
  margin-top: 12px;
}
.paper-sidebar .paper-section > h3 {
  border-bottom: 0;
  border-left: 3px solid var(--accent);
  padding-left: 8px;
}
/* 版式：classic 经典居中 */
.paper-classic .paper-header {
  flex-direction: column;
  align-items: center;
  text-align: center;
  border-bottom: 3px double var(--accent);
}
.paper-classic .paper-contact {
  text-align: center;
  margin-top: 8px;
}
.paper-classic .paper-section > h3 {
  text-align: center;
  letter-spacing: 0.3em;
  border-bottom: 0;
}
/* 版式：timeline 时间线 */
.paper-timeline .paper-section article {
  position: relative;
  padding-left: 14px;
  border-left: 2px solid color-mix(in srgb, var(--accent) 25%, #fff);
}
.paper-timeline .paper-section article::before {
  content: '';
  position: absolute;
  left: -5px;
  top: 3px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}
@media (max-width: 600px) {
  .paper {
    padding: 28px 24px;
    min-height: 550px;
  }
  .paper-header {
    display: block;
  }
  .paper-contact {
    text-align: left;
    margin-top: 10px;
  }
  .paper-sidebar .paper-header {
    margin: -28px -24px 0;
    padding: 22px 24px 16px;
  }
}
@media print {
  .paper {
    box-shadow: none;
    min-height: 0;
    max-width: none;
  }
}
</style>
