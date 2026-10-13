<script setup lang="ts"></script>

<template>
  <div class="container-page py-24 text-center">
    <div class="text-7xl font-extrabold text-gradient mb-4">404</div>
    <p class="text-text-soft mb-6">你访问的页面不存在或已被移除</p>
    <div class="flex items-center justify-center gap-3">
      <RouterLink to="/" class="btn-primary">返回首页</RouterLink>
      <RouterLink to="/tools" class="btn-ghost !border !border-border">工具大全</RouterLink>
    </div>
  </div>
</template>
