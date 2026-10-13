---
name: 办公工具箱项目初始化搭建
description: 用于从零初始化办公工具箱Vue3+Vite+TS+Tailwind纯前端项目，只搭建骨架，不写工具业务逻辑，对齐PRD文档
---

skill_id: office‑tool‑init
name: 办公工具箱项目初始化搭建
description: 用于从零初始化办公工具箱Vue3+Vite+TS+Tailwind纯前端项目，只搭建骨架，不写工具业务逻辑，对齐PRD文档
trigger: 新建项目、初始化项目骨架
steps:
  1. 读取PRD文档 canvas:office‑tool‑web‑prd，严格遵守项目约束：纯前端本地运算，不上传文件
  2. 生成完整项目基础配置 vite.config.ts tsconfig.json tailwind.config
  3. 创建目录结构、路由表、主布局组件（侧边栏+导航栏+面包屑）、首页容器
  4. 实现浅色/暗黑主题切换、全局搜索组件、移动端抽屉侧边栏
  5. 创建tools.ts工具元数据配置文件，填入全部工具元信息，路由预留占位
  6. 创建通用公共组件占位（上传区域、进度提示、复制按钮）
  7. 不实现任何工具业务转换逻辑；输出：改动文件清单，告知运行命令 npm run dev，说明当前仅骨架完成
output: 项目骨架完成，可预览布局，工具功能待后续迭代开发