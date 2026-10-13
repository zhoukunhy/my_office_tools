skill_id: office‑tool‑bug‑fix‑polish
name: 工具箱bug修复、体验优化、打包部署输出
description: 处理反馈bug、细节打磨、性能优化，输出部署文档README
trigger: 修复bug、优化体验、项目收尾打包部署
steps:
  1. 复现用户描述bug，定位代码位置，遵循最小改动修改；不要大面积重构无关代码
  2. 边界处理：非法输入捕获、大文件卡顿优化、loading状态、防抖
  3. UI细节：移动端样式、hover、空状态提示
  4. 完善Footer隐私声明、帮助弹窗组件
  5. vite构建配置优化，tree‑shaking减小产物体积
  6. 更新README.md，输出：npm build打包命令、Nginx静态托管部署步骤、Vercel部署步骤、后续迭代TODO清单
output: bug修复完成，给出验证步骤；输出完整部署文档；列出下一版本迭代任务
