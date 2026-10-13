skill_id: office‑tool‑feature‑iterate
name: 分批迭代开发办公小工具
description: 批量开发单个/多个工具箱工具页面，保持UI统一，本地浏览器运算，处理异常边界
trigger: 需要开发新工具页面、新增工具功能
steps:
  1. 读取rules规则，确认：文件本地处理，禁止上传；复用通用组件模板
  2. 在 tools.ts 添加工具元数据；router/index.ts 注册新路由
  3. 在 src/views/tools/ 创建对应工具Vue组件，复用统一交互UI模板：上传区、参数面板、预览、进度、结果输出、下载复制
  4. 业务逻辑：使用前端本地库，文件全部内存处理；大文件考虑WebWorker；try‑catch捕获全部异常，中文错误提示
  5. 接入localStorage本地缓存输入参数，页面刷新不丢失
  6. 支持批量场景的工具实现批量处理逻辑
  7. 完成后列出改动文件，给出手动验证测试点；提示已知边界限制
output: 新增工具页面可访问，基础功能可用，异常场景有提示；不修改无关业务代码
