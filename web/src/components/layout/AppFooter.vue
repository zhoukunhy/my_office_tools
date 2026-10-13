<script setup lang="ts">
const year = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-border bg-surface">
    <div class="container-page py-8 grid gap-4 md:grid-cols-3 text-sm">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <img src="/favicon.svg" alt="logo" class="w-5 h-5" />
          <span class="font-semibold">速用工具箱</span>
        </div>
        <p class="text-text-soft leading-relaxed">
          一站式免费办公工具合集，所有文件浏览器本地处理，无上传、无广告、无付费、隐私安全。
        </p>
      </div>
      <div>
        <div class="font-medium mb-2">工具分类</div>
        <ul class="space-y-1 text-text-soft">
          <li><RouterLink to="/tools?cat=pdf" class="hover:text-primary">PDF 工具</RouterLink></li>
          <li><RouterLink to="/tools?cat=image" class="hover:text-primary">图片工具</RouterLink></li>
          <li><RouterLink to="/tools?cat=dev" class="hover:text-primary">开发 / 通用</RouterLink></li>
        </ul>
      </div>
      <div>
        <div class="font-medium mb-2">关于</div>
        <ul class="space-y-1 text-text-soft">
          <li><RouterLink to="/about" class="hover:text-primary">关于本站</RouterLink></li>
          <li><RouterLink to="/system" class="hover:text-primary">系统效率推荐</RouterLink></li>
          <li><span class="text-text-mute">支持离线使用 · 可部署至 GitHub Pages</span></li>
        </ul>
      </div>
    </div>
    <div class="border-t border-border-soft">
      <div
        class="container-page py-3 text-xs text-text-mute flex flex-col sm:flex-row items-center justify-between gap-1"
      >
        <span>© {{ year }} 速用工具箱 · 个人自用工具合集</span>
        <span>本地运行 · 无后端依赖 · 隐私优先</span>
      </div>
    </div>
  </footer>
</template>
