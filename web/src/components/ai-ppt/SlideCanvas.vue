<script setup lang="ts">
/**
 * 幻灯片渲染画布：把一页 Slide JSON 按版式渲染为 HTML
 * 设计基准 960x540（16:9），外层按容器宽度等比缩放，缩略图与大预览共用
 */
import { onMounted, onBeforeUnmount, ref } from 'vue'
import type { PptTheme, Slide } from '@/types/aiPpt'

const props = withDefaults(
  defineProps<{
    slide: Slide
    theme: PptTheme
    /** 隐藏演讲备注水印等细节（缩略图用） */
    mini?: boolean
  }>(),
  { mini: false }
)

const wrap = ref<HTMLDivElement | null>(null)
const scale = ref(1)
let ro: ResizeObserver | null = null

onMounted(() => {
  if (!wrap.value) return
  const update = () => {
    if (wrap.value) scale.value = wrap.value.clientWidth / 960
  }
  update()
  ro = new ResizeObserver(update)
  ro.observe(wrap.value)
})

onBeforeUnmount(() => ro?.disconnect())

const fontSerif = () => (props.theme.font === 'serif' ? 'Georgia, "Times New Roman", serif' : '"Microsoft YaHei", "PingFang SC", sans-serif')
</script>

<template>
  <div ref="wrap" class="slide-wrap">
    <div
      class="slide"
      :style="{
        transform: `scale(${scale})`,
        '--p': theme.primary,
        '--bg': theme.bg,
        '--t': theme.text,
        '--m': theme.mute,
        fontFamily: fontSerif()
      }"
    >
      <!-- 封面 / 结束页 -->
      <template v-if="slide.layout === 'cover' || slide.layout === 'end'">
        <div class="cover">
          <div class="cover-line"></div>
          <h1>{{ slide.title }}</h1>
          <p v-if="slide.subtitle">{{ slide.subtitle }}</p>
        </div>
      </template>

      <!-- 金句页 -->
      <template v-else-if="slide.layout === 'quote'">
        <div class="quote">
          <div class="quote-bar"></div>
          <div class="quote-body">
            <h1>“{{ slide.title }}”</h1>
            <p v-if="slide.subtitle">{{ slide.subtitle }}</p>
          </div>
        </div>
      </template>

      <!-- 目录 / 内容 / 双栏 -->
      <template v-else>
        <header class="head">
          <div class="head-bar"></div>
          <h2>{{ slide.title }}</h2>
        </header>
        <div class="items" :class="{ cols2: slide.layout === 'two-column' || (slide.layout === 'toc' && slide.items.length > 5) }">
          <div v-for="(it, i) in slide.items" :key="i" class="item">
            <div class="item-tick"></div>
            <div class="item-text">
              <strong v-if="it.title">{{ slide.layout === 'toc' ? `${i + 1}. ${it.title}` : it.title }}</strong>
              <p v-if="it.detail">{{ it.detail }}</p>
            </div>
          </div>
        </div>
      </template>

      <footer v-if="!mini" class="pageno">{{ slide.index }}</footer>
    </div>
  </div>
</template>

<style scoped>
.slide-wrap {
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  position: relative;
}
.slide {
  width: 960px;
  height: 540px;
  transform-origin: top left;
  background: var(--bg);
  color: var(--t);
  position: absolute;
  top: 0;
  left: 0;
}
.head { position: absolute; top: 44px; left: 40px; right: 40px; display: flex; align-items: center; gap: 14px; }
.head-bar { width: 8px; height: 34px; background: var(--p); border-radius: 2px; }
.head h2 { margin: 0; font-size: 30px; font-weight: 700; }
.items { position: absolute; top: 118px; left: 40px; right: 40px; bottom: 34px; overflow: hidden; }
.items.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 28px; align-content: start; }
.item { display: flex; gap: 12px; padding: 10px 0; }
.item-tick { width: 6px; min-height: 24px; background: var(--p); border-radius: 2px; margin-top: 4px; flex-shrink: 0; }
.item-text strong { font-size: 19px; display: block; line-height: 1.35; }
.item-text p { margin: 5px 0 0; font-size: 14px; color: var(--m); line-height: 1.5; }
.cover { position: absolute; inset: 0; background: var(--p); color: #fff; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 0 90px; }
.cover-line { width: 64px; height: 5px; background: rgba(255, 255, 255, 0.85); border-radius: 3px; margin-bottom: 34px; }
.cover h1 { margin: 0; font-size: 56px; line-height: 1.25; font-weight: 700; }
.cover p { margin: 22px 0 0; font-size: 22px; color: rgba(255, 255, 255, 0.88); }
.quote { position: absolute; inset: 0; display: flex; align-items: center; padding: 0 80px; gap: 34px; }
.quote-bar { width: 8px; height: 60%; background: var(--p); border-radius: 4px; flex-shrink: 0; }
.quote-body h1 { margin: 0; font-size: 36px; line-height: 1.5; font-style: italic; font-weight: 600; }
.quote-body p { margin: 20px 0 0; font-size: 17px; color: var(--m); }
.pageno { position: absolute; right: 18px; bottom: 10px; font-size: 12px; color: var(--m); opacity: 0.7; }
</style>
