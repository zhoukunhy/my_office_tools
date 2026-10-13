# 速用工具箱（Suyong Tools）

> 一站式、纯前端为主的个人轻量办公工具合集。**所有本地处理型功能均不会上传你的文件**，仅当你主动开启并配置后端时，才会把需要服务端能力的操作（PDF 强力压缩 / Word ↔ PDF / OCR）交给指定后端。

项目采用 **pnpm workspace Monorepo**：

| 目录 | 说明 | 启动命令 |
|---|---|---|
| `web/`     | 前端：Vue 3 + Vite + Element Plus + Tailwind + Pinia + PWA + Monaco | `pnpm dev:web`（根目录） |
| `server/`  | 后端：FastAPI（PDF 强力压缩、Word ↔ PDF、OCR 等可选能力） | `pnpm dev:server` 或直接 Python uvicorn |

> 注意：`需求设计.md` 位于仓库根目录，为最初的需求蓝图。

---

## 一、快速上手（仅前端，P0 + P1 绝大多数能力）

```bash
# 1) 安装依赖（pnpm 9.x）
pnpm install

# 2) 启动前端开发服务器（默认 http://localhost:5173）
pnpm dev:web
```

前端会通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`（未启动后端不影响本地处理工具）。

### 前端功能一览（纯前端本地处理）

- PDF：合并 / 拆分 / 转图片 / 删页与旋转 / 压缩（本地简化版 / 后端强力版二选一） / 水印检测与去除（后端） / Markdown 转 PDF（后端）
- 图片：无损+有损压缩 / PNG·JPG·WebP 格式互转 / 批量改尺寸、重命名 / 文字、Logo 水印 / 长图拼接 / 截图美化 / AI 一键抠图（`@imgly/background-removal`，CPU 本地推理） / AI 局部消除（后端 OpenCV Inpaint）
- 音视频：视频压缩 / 提取音频（后端 FFmpeg）/ GIF 制作
- 文本/开发：JSON 格式化+压缩（**Monaco 编辑器**，行号、折叠、Ctrl+F/H 查找替换） / 二维码生成与解析 / 时间戳与日期互转 / 批量文本处理 / Markdown 编辑器
- 工作室模块：**简历制作**（/resume，纯前端） / **AI 生成 PPT**（/ai-ppt，需后端 + LLM，见下文三）
- OCR、Word ↔ PDF、PDF 强力压缩、文档文字提取：默认关闭；在「个人中心 → 后端加速」开启后可用（下方四）

### 前端设置与个性化

**Tab 导航栏（首页 / 工具 / 收藏 / 我的）**：桌面端通过顶栏菜单、移动端（md 以下）底部 4 Tab 常驻。

**个人中心（/me）**：
1. **浅 / 深色模式切换**：沿用之前实现 + 持久化
2. **主题色**：6 套预设（星辰蓝 / 薄荷绿 / 暖阳橙 / 玫瑰粉 / 黑曜紫 / 墨黑），随切随生效
3. **整体字号**：紧凑 / 标准 / 舒适 / 大字号 四档
4. **后端加速**：开关 + 地址配置 + 一键连通性检测（请求 `/api/health`）
5. **关于本站 / 系统效率推荐**：作为二级链接仍可跳转（不暴露于顶栏/底部Tab）
6. **本地数据管理**：收藏、最近使用、一键清空

所有偏好均使用 `pinia-plugin-persistedstate` 持久化到浏览器 localStorage。

---

## 二、工作室模块：简历制作 & AI 生成 PPT

### 2.1 简历制作（/resume，纯前端，无需后端）

- **6 套模板**：Clean / Editorial / Mono / Harbor（通栏侧栏）/ Classic（经典居中）/ Pulse（时间线），点击卡片弹出大图预览并同时切换选中
- **分步填写**：基本信息 → 经历（工作 / 项目 / 教育，可增删条目与模块）→ 完成，右侧实时预览
- **简历导入**：上传 `.docx / .doc / .pdf / .txt` 自动提取并填充（txt 本地解码；Word/PDF 走后端 `/api/doc/extract-text`，启发式解析后可继续手动修改）
- **导出**：浏览器打印为 PDF。打印时通过 `@page { margin: 0 }` + `:has()` 自动隐藏全部站点壳层，输出干净的单页 A4 纸张（无页眉页脚、无网址、无第二页杂项），文件名为「姓名+个人简历」

### 2.2 AI 生成 PPT（/ai-ppt，需后端 + LLM）

全流程四步：

1. **输入**：主题 + 结构化补充（背景与场合 / 主要内容 / 风格要求，自动增高的文本域）+ 长文档投喂（docx/pdf/txt 提取作为素材）+ 目标页数
2. **大纲**：后端 langgraph 图（起草 → 结构自检）生成逐页大纲；可手动增删改页，也可输入反馈让 AI 修改（可聚焦某一页，支持多轮）
3. **并发生成**：确认大纲后创建生成任务，进程内队列（`asyncio.Semaphore`，默认并发 4）同时生成每页内容 JSON，前端轮询进度，先完成的页可先看先编辑
4. **预览编辑导出**：左侧页面列表 / 中间单页预览或滚动检查 / 右侧编辑面板（内容、6 种版式、6 套主题色自定义）；对单页可让 AI 按反馈修复；最终 `pptxgenjs` 导出真 `.pptx`（16:9，含演讲者备注）

**LLM 配置（必须）**：编辑 `server/.env`（OpenAI 兼容接口，DeepSeek/通义/Kimi/OpenAI 均可）：

```bash
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-你的key
LLM_MODEL=deepseek-chat
AI_PPT_CONCURRENCY=4        # 并发生成页数，可选
```

未配置 Key 时 AI PPT 接口返回 503 + 友好提示，其余功能不受影响。`/api/config` 的 `capabilities.ai_ppt` 可判断是否就绪。

### 2.3 前端核心文件

| 文件 | 说明 |
|---|---|
| `web/src/views/ResumeView.vue` / `views/AiPptView.vue` | 两个工作室主页面 |
| `web/src/components/common/ResumePaper.vue` | 简历纸张渲染（6 版式） |
| `web/src/components/ai-ppt/` | SlideCanvas（页面渲染）/ OutlineEditor / SlideInspector |
| `web/src/composables/useResumeParse.ts` / `useAiPpt.ts` | 简历解析、AI PPT 状态与轮询 |
| `web/src/utils/pptxExport.ts` / `web/src/types/aiPpt.ts` | PPTX 导出映射、共享类型与主题预设 |
| `web/src/components/common/AutoTextarea.vue` | 自动增高文本域（内容多时完整展开） |

---

## 三、启用可选后端（PDF 强力压缩 / Word ↔ PDF / OCR / 视频处理 / AI 生成 PPT）

### 3.1 安装 Python 依赖

```bash
cd server
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 安装系统级二进制（按你想要的功能；缺失时对应 API 会返回 503 + 友好提示）

| 功能 | 需要的可执行文件 | 常见安装方式（示例） |
|---|---|---|
| Word ↔ PDF | `soffice`（LibreOffice） | Windows：官网安装 + 把路径加入 PATH；macOS：`brew install --cask libreoffice`；Linux：`apt install libreoffice` |
| PDF 强力压缩 | `gs`（Ghostscript） | Windows：官网安装后 `gswin64c` 起别名 `gs` 或改代码；macOS：`brew install ghostscript`；Linux：`apt install ghostscript` |
| OCR | `tesseract` + 语言包 `chi_sim eng` | Windows：UB-Mannheim/tesseract 安装包；macOS：`brew install tesseract tesseract-lang`；Linux：`apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng` |
| 视频压缩 / 提取音频 | `ffmpeg` | Windows：`winget install Gyan.FFmpeg` 或官网下载后加入 PATH；macOS：`brew install ffmpeg`；Linux：`apt install ffmpeg` |

> 可在前端「个人中心 → 后端加速」里点击 **连通性检测**，或直接访问：
> `curl http://127.0.0.1:8000/api/health`
> 响应的 `capabilities` 字段会告诉你三项能力是否就绪。

### 2.3 启动后端

```bash
# 在仓库根目录（推荐，配合 monorepo 脚本）
pnpm dev:server

# 或直接在 server/ 下：
cd server
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

### 3.4 连接前端到后端

**场景 A：本机开发 / 同源部署** — 最简单。前端默认 Vite 代理 `/api` → `http://127.0.0.1:8000`，**无需填后端地址**：

1. 打开 `http://localhost:5173/me`
2. 「后端加速」**开关打开**，**后端地址留空**（留空 = 走 `/api` 相对路径）
3. 点「连通性检测」看到绿色「连接成功」即完成

**场景 B：后端独立部署在另一个域名（https://api.example.com）**：

1. 后端 CORS 允许前端域名：启动前设置环境变量 `CORS_ORIGINS=https://web.example.com`（多个用逗号分隔）。
2. 个人中心里填写 `https://api.example.com`，打开开关即可。前端会直接跨域请求 `https://api.example.com/api/**`。

### 3.5 后端 API 一览

所有接口都挂在 `/api` 前缀下。

| Method | Path | 说明 | 输入（FormData） | 成功输出 |
|---|---|---|---|---|
| GET | `/api/health` | 健康检查 + 能力披露（版本、各能力是否可用） | — | JSON |
| GET | `/api/config` | 配置说明（上限、capabilities、依赖安装说明） | — | JSON |
| GET | `/api/check-url` | URL 连通性检测 | `url` 查询参数 | JSON |
| POST | `/api/ocr` | 图片 OCR，返回文本 txt | `file`：图片；`lang` 默认 `chi_sim+eng` | `text/plain` UTF-8，文件名 `{原文件名}.txt` |
| POST | `/api/pdf/compress` | PDF 强力压缩（Ghostscript） | `file`：PDF；`quality`：1(激进)~5(轻)，默认 3 | `application/pdf`，文件名 `{原文件名}.min.pdf` |
| POST | `/api/convert/word-to-pdf` | DOC/DOCX → PDF | `file`：.doc/.docx | `application/pdf` |
| POST | `/api/convert/pdf-to-word` | PDF → DOCX | `file`：.pdf | DOCX（office 对应 MIME） |
| POST | `/api/pdf/watermark-detect` | PDF 水印检测 | `file`：PDF | JSON |
| POST | `/api/pdf/watermark-remove` | PDF 水印去除 | `file`：PDF + 参数 | `application/pdf` |
| POST | `/api/md-to-pdf` | Markdown → PDF | `file` 或文本字段 | `application/pdf` |
| POST | `/api/image/inpaint` | 图片局部消除（OpenCV Inpaint） | `file`：图片 + 蒙版参数 | 图片 |
| POST | `/api/doc/extract-text` | 文档文字提取（docx/doc/pdf，简历导入 / AI PPT 投喂共用） | `file`：文档 | `text/plain` UTF-8 |
| POST | `/api/video/compress` | 视频压缩（FFmpeg） | `file`：视频 + 压缩参数 | 视频文件 |
| POST | `/api/video/extract-audio` | 视频提取音频（FFmpeg） | `file`：视频 | 音频文件 |

AI 生成 PPT 接口（JSON 请求体，见 `server/ai_ppt.py`）：

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/ai-ppt/outline` | 根据主题/背景/文档生成大纲（langgraph：起草 → 结构自检） |
| POST | `/api/ai-ppt/outline/revise` | 按反馈修改大纲，支持 `focus_index` 聚焦单页 |
| POST | `/api/ai-ppt/generate` | 创建并发生成任务，返回 `task_id` |
| GET | `/api/ai-ppt/tasks/{task_id}` | 轮询任务进度与每页 JSON |
| POST | `/api/ai-ppt/page/fix` | 单页按反馈重新生成 |

面试题库接口（JSON 请求体 + 文件上传，见 `server/interview.py`；数据存 `server/data/interview.db` SQLite）：

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/interview/questions` | 题目列表（分类/标签/难度/关键词/收藏筛选 + 分页） |
| GET | `/api/interview/questions/{id}` | 单题详情 |
| POST | `/api/interview/questions` | 新增题目 |
| PUT | `/api/interview/questions/{id}` | 更新题目（含收藏切换） |
| DELETE | `/api/interview/questions/{id}` | 删除题目 |
| POST | `/api/interview/questions/batch-delete` | 批量删除（`ids` 数组） |
| POST | `/api/interview/questions/batch-update` | 批量改分类/标签/难度/收藏 |
| POST | `/api/interview/import` | 批量导入（JSON 数组，自动归一化分类/难度） |
| POST | `/api/interview/import-file` | 文件上传导入（.json / .txt / .md，UTF-8/GBK 自动识别） |
| GET | `/api/interview/export` | 导出题目（`format=json` 可回导 / `format=text` 与粘贴导入互通） |
| GET | `/api/interview/quiz` | 随机出题（分类/标签/难度/数量） |
| GET | `/api/interview/stats` | 分类与难度统计 |
| POST | `/api/interview/records` | 保存答题记录（错题本持久化） |
| GET | `/api/interview/records` | 答题记录列表（`scope=wrong/mastered/all`） |
| DELETE | `/api/interview/records/{id}` | 删除单条记录 |
| GET | `/api/interview/records/stats` | 答题统计（按得分/错题分类） |
| POST | `/api/interview/ai-generate` | AI 智能出题（复用 LLM 配置，未配置返回 503 提示） |

所有下载接口返回 `Content-Disposition: attachment; filename*=UTF-8''...`，保证中文文件名。

#### 单文件上限

默认 200MB，可用环境变量覆盖：

```bash
MAX_UPLOAD_MB=400 uvicorn app:app
```

---

## 四、目录结构速览

```
.
├─ package.json              Monorepo root 脚本（dev:web / dev:server / build:web / type-check）
├─ pnpm-workspace.yaml
├─ 需求设计.md
│
├─ web/                       Vue3 前端工程
│  ├─ package.json            @suyong/web（含 pptxgenjs）
│  ├─ vite.config.ts          带 /api 代理、Monaco worker、chunk 拆分
│  ├─ tailwind.config.js / postcss.config.js / tsconfig*.json / env.d.ts / .env.example
│  └─ src/
│     ├─ App.vue              挂 AppHeader + AppTabBar(移动) + RouterView + AppFooter(桌面非Tab页)
│     ├─ main.ts              注册 pinia + pinia-persistedstate、init theme/preference
│     ├─ router/index.ts      / /tools /favorites /me /tool/:slug /resume /ai-ppt（/about /system 保留但隐藏入口）
│     ├─ stores/
│     │  ├─ theme.ts          深浅色 + 6 套主题色 + 4 档字号，apply 写 CSS 变量/Element 变量
│     │  └─ preference.ts     收藏/最近使用/后端地址+开关
│     ├─ components/
│     │  ├─ layout/           AppHeader / AppTabBar(4Tab) / AppFooter
│     │  ├─ common/           ProcessSteps · FileDropZone · BatchFileList · JsonEditor(monaco) · ToolCard · ThemeToggle
│     │  │                    · ResumePaper(简历纸张6版式) · AutoTextarea(自动增高文本域)
│     │  ├─ ai-ppt/           SlideCanvas(页面渲染) · OutlineEditor(大纲) · SlideInspector(编辑面板)
│     │  └─ tools/ToolHeader.vue
│     ├─ views/
│     │  ├─ HomeView / ToolsView / FavoritesView / MeView / ToolRunnerView / NotFound / About / System
│     │  ├─ ResumeView.vue    简历制作（模板/分步/导入/打印导出）
│     │  ├─ AiPptView.vue     AI 生成 PPT（四步流程）
│     │  └─ tools/
│     │     ├─ PdfMergeView (已升级流程条+BatchList)
│     │     ├─ PdfCompressView (本地+后端双模式，需后端会给出引导)
│     │     ├─ WordToPdfView / PdfToWordView (后端驱动)
│     │     ├─ OcrView （后端开启走高精度，否则降级提示）
│     │     ├─ JsonFormatView （Monaco 懒加载 + 行号/折叠/查找替换/深浅色跟随）
│     │     └─ ... 其它工具：pdf-split/pdf-to-image/pdf-pages/ image-*/qrcode/timestamp/ video-*/gif 等
│     ├─ composables/
│     │  ├─ useResumeParse.ts 简历文件导入解析（txt 本地 / docx·pdf 走后端）
│     │  └─ useAiPpt.ts       AI PPT 全流程状态、任务轮询、本地缓存
│     ├─ types/aiPpt.ts       页面/大纲/主题类型 + 主题预设
│     ├─ utils/
│     │  ├─ file.ts / pdf.ts / image.ts
│     │  ├─ pptxExport.ts     页面 JSON → pptxgenjs 导出
│     │  └─ api.ts            getBackendStatus / resolveApiUrl / backendFetch / backendPostJson / backendGetJson
│     └─ config/ tools.ts + tool-registry.ts
│
└─ server/                    FastAPI 后端
   ├─ app.py                  health · config · ocr · pdf/compress · convert · watermark · md-to-pdf
   │                          · image/inpaint · doc/extract-text · video/*
   ├─ ai_ppt.py               AI 生成 PPT 子路由（langgraph 大纲图 + 进程内并发生成队列）
   ├─ interview.py            面试题库子路由（SQLite 存储：题库 CRUD/导入导出/批量/答题记录/AI 出题）
   ├─ package.json            @suyong/server，dev:server 用 pnpm --filter 调起
   ├─ requirements.txt        fastapi / uvicorn / python-multipart / python-dotenv / langgraph / langchain-openai
   └─ .env.example            HOST/PORT/MAX_UPLOAD_MB/CORS_ORIGINS/LOG_LEVEL
                              LLM_BASE_URL / LLM_API_KEY / LLM_MODEL / AI_PPT_CONCURRENCY
```

---

## 五、类型检查 / 构建 / 验证

```bash
# 前端类型检查（vue-tsc）
pnpm type-check

# 前端生产构建
pnpm build:web
```

> 默认 monorepo 没有安装依赖前，需要先执行 `pnpm install`；如果 Windows 权限碰到 EPERM 之类，仓库根已经在 `.npmrc` 里把 pnpm store 固定到 `D:/ai/mytools/.pnpm-store`。

---

## 六、小提示

- **PDF 压缩**：本地简化版只做对象流重写 + 元数据清理，对纯文本/表单 PDF 通常省 10~25%。如果是扫描版，建议开启后端「强力模式」（Ghostscript）。
- **Word ↔ PDF / OCR / 视频处理**：纯前端没有稳定实现，都依赖显式开启后端；未开启时页面会给出醒目的引导卡片 + 跳转「个人中心」按钮。
- **Monaco JSON 编辑器**：首次进入 JSON 工具才会加载 Monaco worker，首屏无需担心。
- **AI 抠图**：`@imgly/background-removal` 会在首次使用时按需下载模型（数十 MB 级别），并在前端提示。
- **数据本地**：收藏/最近使用/外观/后端配置都保存在浏览器 localStorage，用户可在「个人中心 → 数据管理」随时清空。
- **简历打印**：点「生成简历」后选「另存为 PDF」即可；打印样式会自动隐藏站点壳层与浏览器页眉页脚，文件名为「姓名+个人简历」。
- **AI 生成 PPT**：需在 `server/.env` 配置 LLM Key 并重启后端；DeepSeek 生成 10 页约 1~3 分钟（并发 4）；重启后端会丢进行中的生成任务，但大纲与已生成页面有本地缓存。
- **面试题库**：题目与答题记录存于 `server/data/interview.db`（SQLite，自动创建），删除该文件即重置数据；AI 智能出题复用 AI PPT 的 LLM 配置，未配置时点击生成会给出 503 提示；导出的 JSON 可直接通过「文件导入」回导。
