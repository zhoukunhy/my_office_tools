<script setup lang="ts">
const features = [
  { icon: 'Lock', title: '隐私优先', desc: '所有文件在浏览器本地处理，绝不上传服务器' },
  { icon: 'CircleCloseFilled', title: '无广告无弹窗', desc: '纯净界面，专注工具本身，无第三方跳转' },
  { icon: 'WalletFilled', title: '永久免费', desc: '个人自用工具合集，无付费墙、无水印' },
  { icon: 'Connection', title: '一站式', desc: 'PDF / 图片 / 文本 / 音视频 / 开发工具全覆盖' },
  { icon: 'Cellphone', title: '多端适配', desc: 'PC、手机、平板自适应，支持 PWA 离线' },
  { icon: 'Loading', title: '极速响应', desc: '模块化按需加载，普通文件秒级处理' }
]

const stack = [
  'Vue 3 + Vite', 'TypeScript', 'Element Plus', 'Tailwind CSS',
  'Vue Router + Pinia', 'pdf-lib', 'tesseract.js', 'ffmpeg.wasm',
  'qrcode / jsQR', 'vite-plugin-pwa'
]
</script>

<template>
  <div class="container-page py-12">
    <!-- 介绍 -->
    <section class="text-center max-w-3xl mx-auto mb-12">
      <h1 class="text-3xl font-extrabold tracking-tight mb-4">
        关于<span class="text-gradient">速用工具箱</span>
      </h1>
      <p class="text-text-soft text-lg leading-relaxed">
        日常办公中高频用到 PDF、图片、文本、音视频、开发等各类小工具，
        市面工具广告多、跳转多、收费多、隐私不安全。本站搭建个人轻量化办公工具合集，
        所有工具浏览器本地运行，一站式解决办公效率问题。
      </p>
    </section>

    <!-- 特性 -->
    <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
      <div v-for="f in features" :key="f.title" class="card p-5">
        <el-icon :size="28" class="text-primary mb-3"><component :is="f.icon" /></el-icon>
        <h3 class="font-semibold mb-1">{{ f.title }}</h3>
        <p class="text-sm text-text-soft">{{ f.desc }}</p>
      </div>
    </section>

    <!-- 技术栈 -->
    <section class="card p-8 mb-8">
      <h2 class="text-xl font-bold mb-4">技术栈</h2>
      <div class="flex flex-wrap gap-2">
        <span v-for="s in stack" :key="s" class="tag !px-3 !py-1.5">{{ s }}</span>
      </div>
      <p class="text-sm text-text-mute mt-4 leading-relaxed">
        纯静态前端项目，零后端、零数据库，编译产物可部署至 GitHub Pages、Vercel、Netlify、阿里云 OSS 等任意静态托管，零成本上线。
      </p>
    </section>

    <!-- 部署 -->
    <section class="grid md:grid-cols-2 gap-4">
      <div class="card p-6">
        <h3 class="font-semibold mb-2 flex items-center gap-2">
          <el-icon class="text-primary"><Upload /></el-icon> 部署方式
        </h3>
        <p class="text-sm text-text-soft leading-relaxed">
          <code class="text-primary">pnpm build</code> 后将 <code>dist/</code> 上传至任意静态托管平台即可访问，无需服务器与数据库。
        </p>
      </div>
      <div class="card p-6">
        <h3 class="font-semibold mb-2 flex items-center gap-2">
          <el-icon class="text-primary"><WarnTriangleFilled /></el-icon> 隐私声明
        </h3>
        <p class="text-sm text-text-soft leading-relaxed">
          本站所有文件处理均在本地浏览器完成，无埋点、无数据收集、无广告脚本，使用即代表信任本地计算能力。
        </p>
      </div>
    </section>
  </div>
</template>
