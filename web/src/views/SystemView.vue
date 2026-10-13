<script setup lang="ts">
interface Tool {
  name: string
  desc: string
  tags: string[]
  url: string
  platform: string
}

const tools: Tool[] = [
  {
    name: 'Everything',
    desc: 'Windows 极速文件名搜索工具，毫秒级检索全盘文件',
    tags: ['文件搜索', '极速', 'Windows'],
    url: 'https://www.voidtools.com/zh-cn/',
    platform: 'Windows'
  },
  {
    name: 'Ditto',
    desc: '剪贴板历史管理，记录复制内容，支持搜索与粘贴',
    tags: ['剪贴板', '历史', 'Windows'],
    url: 'https://ditto-cp.sourceforge.io/',
    platform: 'Windows'
  },
  {
    name: 'PowerToys',
    desc: '微软官方效率工具集，含 FancyZones、PowerToys Run、颜色选择器等',
    tags: ['微软官方', '窗口管理', '快速启动'],
    url: 'https://learn.microsoft.com/zh-cn/windows/powertoys/',
    platform: 'Windows'
  },
  {
    name: 'Snipaste',
    desc: '截图 + 贴图利器，截图后可钉在桌面置顶参考',
    tags: ['截图', '贴图', '跨平台'],
    url: 'https://www.snipaste.com/',
    platform: 'Windows / macOS'
  },
  {
    name: 'uTools',
    desc: '新一代效率工具平台，插件化快速搜索、翻译、计算等',
    tags: ['插件化', '全局呼出', '跨平台'],
    url: 'https://u.tools/',
    platform: 'Windows / macOS / Linux'
  },
  {
    name: 'Listary',
    desc: '文件搜索与快速启动器，集成资源管理器，随叫随到',
    tags: ['文件搜索', '快速启动', 'Windows'],
    url: 'https://www.listary.com/',
    platform: 'Windows'
  }
]
</script>

<template>
  <div class="container-page py-10">
    <div class="mb-8">
      <h1 class="text-2xl font-bold">系统效率工具推荐</h1>
      <p class="text-text-soft mt-1">
        纯内容展示页，推荐日常高频使用的电脑效率工具，附简介与官方下载指引。
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <a
        v-for="t in tools"
        :key="t.name"
        :href="t.url"
        target="_blank"
        rel="noopener noreferrer"
        class="card p-5 hover:shadow-md hover:-translate-y-0.5 transition-all"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="font-semibold flex items-center gap-2">
              {{ t.name }}
              <el-icon :size="14" class="text-text-mute"><TopRight /></el-icon>
            </h3>
            <p class="text-sm text-text-soft mt-1">{{ t.desc }}</p>
            <div class="flex flex-wrap gap-1.5 mt-3">
              <span v-for="tag in t.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
          <el-tag size="small" type="info" effect="plain">{{ t.platform }}</el-tag>
        </div>
      </a>
    </div>

    <div class="card p-6 mt-8 text-sm text-text-soft leading-relaxed">
      <el-icon class="text-primary align-middle"><InfoFilled /></el-icon>
      以上推荐均为第三方桌面效率软件，与本站工具无功能冲突。本站工具面向临时性、在线化、跨端处理场景；桌面效率软件面向本地常驻、深度集成场景，二者互补。
    </div>
  </div>
</template>
