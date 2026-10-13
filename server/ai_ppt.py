"""AI 生成 PPT 模块（FastAPI 子路由，前缀 /api/ai-ppt）

流程：
1. POST /api/ai-ppt/outline          根据主题/背景/长文档生成 PPT 大纲（langgraph 编排：起草 → 结构自检）
2. POST /api/ai-ppt/outline/revise   按用户反馈修改大纲（可指定某一页 focus_index），支持多轮
3. POST /api/ai-ppt/generate         用户确认大纲后，创建并发生成任务（进程内队列，asyncio.Semaphore）
4. GET  /api/ai-ppt/tasks/{task_id}  轮询任务进度与每页 JSON 结果
5. POST /api/ai-ppt/page/fix         对单页反馈问题，AI 重新生成该页

LLM 配置读取 server/.env（OpenAI 兼容）：LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional, TypedDict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("suyong-ai-ppt")

router = APIRouter(prefix="/api/ai-ppt")

# ---- .env 加载（server/.env，容错处理）----
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:  # pragma: no cover
    pass

LAYOUTS = {"cover", "toc", "content", "two-column", "quote", "end"}
DEFAULT_CONCURRENCY = int(os.getenv("AI_PPT_CONCURRENCY", "4"))

_llm = None
_outline_graph = None


def _llm_configured() -> bool:
    return bool(os.getenv("LLM_API_KEY"))


def _get_llm():
    global _llm
    if _llm is not None:
        return _llm
    if not _llm_configured():
        raise HTTPException(status_code=503, detail="后端未配置 LLM：请在 server/.env 中设置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL")
    try:
        from langchain_openai import ChatOpenAI

        _llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL") or None,
            temperature=0.6,
            timeout=180,
            max_retries=2,
        )
        return _llm
    except ImportError:
        raise HTTPException(status_code=503, detail="后端缺少依赖：请先 pip install langgraph langchain-openai")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 初始化失败：{e}")


# ---------------- JSON 提取与校验 ----------------

def _extract_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取第一个平衡的 JSON 对象（兼容 markdown 代码块）"""
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None


def _normalize_outline(data: dict, page_count_hint: int) -> dict:
    """校验并修正大纲结构：标题/页列表/版式合法性，页数不符合提示时截断或补页"""
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise HTTPException(status_code=502, detail="AI 返回的大纲缺少 pages 列表，请重试")
    norm: list[dict] = []
    for i, p in enumerate(pages):
        if not isinstance(p, dict):
            continue
        title = str(p.get("title") or "").strip()
        if not title:
            continue
        layout = str(p.get("layout") or "content").strip()
        if layout not in LAYOUTS:
            layout = "end" if i == len(pages) - 1 else "content"
        norm.append({"index": len(norm) + 1, "title": title, "layout": layout, "brief": str(p.get("brief") or "").strip()})
    if len(norm) < 3:
        raise HTTPException(status_code=502, detail="AI 返回的大纲页数过少，请重试或调整页数要求")
    # 页数对齐：超出截断，不足提示用户（不强行编造）
    if page_count_hint and len(norm) > page_count_hint + 2:
        norm = norm[: page_count_hint]
    for i, p in enumerate(norm):
        p["index"] = i + 1
        if i == 0 and p["layout"] not in ("cover",):
            p["layout"] = "cover"
        if i == len(norm) - 1 and p["layout"] not in ("end",):
            p["layout"] = "end"
    return {
        "title": str(data.get("title") or "未命名演示").strip(),
        "subtitle": str(data.get("subtitle") or "").strip(),
        "pages": norm,
    }


def _normalize_page(data: dict, index: int, layout_hint: str) -> dict:
    """校验并修正单页内容 JSON"""
    layout = str(data.get("layout") or layout_hint).strip()
    if layout not in LAYOUTS:
        layout = layout_hint if layout_hint in LAYOUTS else "content"
    items_raw = data.get("items")
    items: list[dict] = []
    if isinstance(items_raw, list):
        for it in items_raw:
            if isinstance(it, dict):
                items.append({"title": str(it.get("title") or "").strip(), "detail": str(it.get("detail") or "").strip()})
            elif isinstance(it, str) and it.strip():
                items.append({"title": it.strip(), "detail": ""})
    return {
        "index": index,
        "layout": layout,
        "title": str(data.get("title") or "").strip() or "未命名页",
        "subtitle": str(data.get("subtitle") or "").strip(),
        "items": items[:8],
        "notes": str(data.get("notes") or "").strip(),
    }


# ---------------- langgraph 大纲图 ----------------

class OutlineState(TypedDict):
    topic: str
    background: str
    page_count: int
    raw: str
    outline: dict


_OUTLINE_PROMPT = """你是一位资深 PPT 策划师。请根据下面信息设计一份中文演示文稿大纲。

主题：{topic}
补充背景：{background}
要求页数：约 {page_count} 页（首页为封面 cover，末页为结束页 end，中间可安排目录 toc、内容 content、双栏 two-column、金句 quote）

只输出一个 JSON 对象，不要任何多余文字，格式：
{{
  "title": "演示总标题",
  "subtitle": "副标题或一句话定位",
  "pages": [
    {{"index": 1, "title": "页面标题", "layout": "cover|toc|content|two-column|quote|end", "brief": "这一页要讲什么、包含哪些要点（1-2句）"}}
  ]
}}"""


async def _draft_node(state: OutlineState) -> dict:
    llm = _get_llm()
    prompt = _OUTLINE_PROMPT.format(
        topic=state["topic"] or "未命名主题",
        background=(state["background"] or "无")[:6000],
        page_count=state["page_count"],
    )
    resp = await llm.ainvoke(prompt)
    return {"raw": str(resp.content)}


async def _review_node(state: OutlineState) -> dict:
    data = _extract_json(state["raw"])
    if not data:
        raise HTTPException(status_code=502, detail="AI 输出无法解析为大纲 JSON，请重试")
    outline = _normalize_outline(data, state["page_count"])
    return {"outline": outline}


def _get_outline_graph():
    global _outline_graph
    if _outline_graph is not None:
        return _outline_graph
    try:
        from langgraph.graph import END, StateGraph

        g = StateGraph(OutlineState)
        g.add_node("draft", _draft_node)
        g.add_node("review", _review_node)
        g.set_entry_point("draft")
        g.add_edge("draft", "review")
        g.add_edge("review", END)
        _outline_graph = g.compile()
        return _outline_graph
    except ImportError:
        raise HTTPException(status_code=503, detail="后端缺少依赖：请先 pip install langgraph langchain-openai")


# ---------------- 请求/响应模型 ----------------

class OutlineReq(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    background: str = ""
    page_count: int = Field(default=10, ge=4, le=20)


class OutlineItem(BaseModel):
    index: int
    title: str
    layout: str = "content"
    brief: str = ""


class Outline(BaseModel):
    title: str = ""
    subtitle: str = ""
    pages: list[OutlineItem]


class ReviseReq(BaseModel):
    outline: Outline
    feedback: str = Field(min_length=1, max_length=2000)
    focus_index: Optional[int] = None


class GenerateReq(BaseModel):
    outline: Outline


class PageFixReq(BaseModel):
    page: dict
    deck_title: str = ""
    feedback: str = ""


# ---------------- 接口 ----------------

@router.post("/outline")
async def gen_outline(req: OutlineReq):
    """生成大纲（langgraph：draft → review）"""
    graph = _get_outline_graph()
    t0 = time.time()
    final = await graph.ainvoke(
        {"topic": req.topic.strip(), "background": req.background.strip(), "page_count": req.page_count, "raw": "", "outline": {}}
    )
    logger.info("outline generated in %.1fs, pages=%s", time.time() - t0, len(final["outline"].get("pages", [])))
    return {"outline": final["outline"]}


@router.post("/outline/revise")
async def revise_outline(req: ReviseReq):
    """按反馈修改大纲；focus_index 指定时优先只改那一页"""
    llm = _get_llm()
    focus_note = ""
    if req.focus_index:
        target = next((p for p in req.outline.pages if p.index == req.focus_index), None)
        if target:
            focus_note = f"\n用户重点要求只调整第 {req.focus_index} 页（当前标题：{target.title}），其他页保持不变，除非反馈明确涉及整体结构。"
    prompt = f"""这是当前 PPT 大纲（JSON）：
{req.outline.model_dump_json()}

用户修改反馈：{req.feedback}{focus_note}

请输出修改后的完整大纲 JSON（结构与输入完全一致：title/subtitle/pages，pages 每项含 index/title/layout/brief），不要输出任何多余文字。"""
    resp = await llm.ainvoke(prompt)
    data = _extract_json(str(resp.content))
    if not data:
        raise HTTPException(status_code=502, detail="AI 输出无法解析为大纲 JSON，请重试")
    return {"outline": _normalize_outline(data, len(req.outline.pages))}


@router.post("/page/fix")
async def fix_page(req: PageFixReq):
    """单页修复/重新生成"""
    llm = _get_llm()
    page = req.page
    layout = str(page.get("layout") or "content")
    feedback = req.feedback.strip() or "这页效果不理想，请在保持主题一致的前提下重新生成更优质的内容。"
    prompt = f"""演示文稿《{req.deck_title or "未命名"}》中，下面这一页需要修复。

当前页面 JSON：
{json.dumps(page, ensure_ascii=False)}

用户反馈的问题：{feedback}

请重新生成这一页，保持 layout 为 "{layout}"（除非反馈要求更换版式）。只输出该页 JSON 对象，格式：
{{"index": {page.get("index", 1)}, "layout": "{layout}", "title": "...", "subtitle": "", "items": [{{"title": "要点", "detail": "展开说明"}}], "notes": "演讲者备注"}}
不要输出任何多余文字。"""
    resp = await llm.ainvoke(prompt)
    data = _extract_json(str(resp.content))
    if not data:
        raise HTTPException(status_code=502, detail="AI 输出无法解析为页面 JSON，请重试")
    return {"page": _normalize_page(data, int(page.get("index", 1)), layout)}


# ---------------- 并发生成任务（进程内队列） ----------------

class _TaskInfo:
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.status = "running"  # running | done
        self.pages: dict[int, dict] = {}
        self.created_at = time.time()


_TASKS: dict[str, _TaskInfo] = {}
_SEM = asyncio.Semaphore(max(1, DEFAULT_CONCURRENCY))


def _page_prompt(deck_title: str, subtitle: str, p: dict, total: int) -> str:
    return f"""你是一位专业 PPT 文案专家。为演示文稿《{deck_title}》（副标题：{subtitle or "无"}）撰写第 {p["index"]}/{total} 页的完整内容。

页面大纲：{p["title"]}（版式 {p["layout"]}）——{p.get("brief") or ""}

要求：内容具体、有信息量、每条要点 30 字以内；detail 是对该要点的 1-2 句展开。
只输出该页 JSON 对象，不要任何多余文字，格式：
{{"index": {p["index"]}, "layout": "{p["layout"]}", "title": "页标题", "subtitle": "仅封面/结束页需要", "items": [{{"title": "要点", "detail": "展开说明"}}], "notes": "演讲者备注（1-3句）"}}"""


async def _gen_one_page(task_id: str, deck: dict, p: dict, total: int) -> None:
    info = _TASKS[task_id]
    idx = int(p["index"])
    info.pages[idx] = {"status": "running", "data": None, "error": None}
    try:
        async with _SEM:
            llm = _get_llm()
            resp = await llm.ainvoke(_page_prompt(deck["title"], deck.get("subtitle", ""), p, total))
            data = _extract_json(str(resp.content))
            if not data:
                raise ValueError("AI 输出无法解析为页面 JSON")
            info.pages[idx] = {"status": "done", "data": _normalize_page(data, idx, p["layout"]), "error": None}
            info.completed += 1
    except Exception as e:  # noqa: BLE001
        logger.warning("page %s failed: %s", idx, e)
        info.pages[idx] = {"status": "failed", "data": None, "error": str(e)[:200]}
        info.failed += 1
    if info.completed + info.failed >= info.total:
        info.status = "done"


@router.post("/generate")
async def generate(req: GenerateReq):
    """创建并发生成任务，立即返回 task_id"""
    if not _llm_configured():
        raise HTTPException(status_code=503, detail="后端未配置 LLM：请在 server/.env 中设置 LLM_API_KEY")
    deck = req.outline.model_dump()
    pages = deck["pages"]
    if not pages:
        raise HTTPException(status_code=400, detail="大纲为空，无法生成")
    task_id = uuid.uuid4().hex[:12]
    info = _TaskInfo(total=len(pages))
    _TASKS[task_id] = info
    # 清理超过 2 小时的旧任务，避免内存膨胀
    now = time.time()
    for k in [k for k, v in _TASKS.items() if now - v.created_at > 7200]:
        _TASKS.pop(k, None)
    for p in pages:
        asyncio.create_task(_gen_one_page(task_id, deck, p, len(pages)))
    return {"task_id": task_id, "total": len(pages), "concurrency": DEFAULT_CONCURRENCY}


@router.get("/tasks/{task_id}")
async def task_status(task_id: str):
    info = _TASKS.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    pages = [dict(v, index=k) for k, v in sorted(info.pages.items())]
    return {
        "task_id": task_id,
        "status": info.status,
        "total": info.total,
        "completed": info.completed,
        "failed": info.failed,
        "pages": pages,
    }
