"""面试题库后端模块

使用 Python 内置 sqlite3 存储题目数据，零额外依赖。
数据库文件位于 server/data/interview.db（自动创建 data 目录）。

提供接口（统一前缀 /api/interview）：
- GET    /questions            题目列表（支持分类/标签/难度/关键词检索、分页）
- GET    /questions/{id}       单题详情
- POST   /questions            新增题目
- PUT    /questions/{id}       更新题目
- DELETE /questions/{id}       删除题目
- POST   /import               批量导入（JSON 数组）
- GET    /quiz                 随机出题（按分类/标签/难度/数量筛选）
- GET    /stats                分类与难度统计
"""

from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/interview", tags=["interview"])

_DB_DIR = Path(__file__).resolve().parent / "data"
_DB_PATH = _DB_DIR / "interview.db"

# 合法分类与难度（与前端 types/interview.ts 对齐）
_VALID_CATEGORIES = {
    "frontend", "backend", "database", "algorithm",
    "ai", "os", "network", "devops", "other"
}
_VALID_DIFFICULTIES = {"easy", "medium", "hard"}

# 分类/难度中英文别名（导入与 AI 生成时归一化）
_CATEGORY_ALIASES = {
    "frontend": "frontend", "前端": "frontend",
    "backend": "backend", "后端": "backend", "服务端": "backend",
    "database": "database", "数据库": "database", "db": "database",
    "algorithm": "algorithm", "算法": "algorithm", "数据结构": "algorithm", "数据结构与算法": "algorithm",
    "ai": "ai", "大模型": "ai", "人工智能": "ai", "llm": "ai",
    "os": "os", "操作系统": "os",
    "network": "network", "网络": "network",
    "devops": "devops", "运维": "devops",
    "other": "other", "其他": "other", "综合": "other",
}
_DIFFICULTY_ALIASES = {
    "easy": "easy", "简单": "easy",
    "medium": "medium", "中等": "medium", "中": "medium",
    "hard": "hard", "困难": "hard", "难": "hard",
}
_CATEGORY_ZH = {
    "frontend": "前端", "backend": "后端", "database": "数据库",
    "algorithm": "数据结构与算法", "ai": "AI/大模型", "os": "操作系统",
    "network": "网络", "devops": "运维/DevOps", "other": "综合",
}
_DIFFICULTY_ZH = {"easy": "简单", "medium": "中等", "hard": "困难"}


def _norm_category(v: Any) -> str:
    s = str(v or "").strip()
    return _CATEGORY_ALIASES.get(s) or _CATEGORY_ALIASES.get(s.lower()) or "other"


def _norm_difficulty(v: Any, default: str = "medium") -> str:
    s = str(v or "").strip()
    return _DIFFICULTY_ALIASES.get(s) or _DIFFICULTY_ALIASES.get(s.lower()) or default


def _get_conn() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                title TEXT NOT NULL,
                answer TEXT NOT NULL DEFAULT '',
                difficulty TEXT NOT NULL DEFAULT 'medium',
                source TEXT,
                favorite INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_q_category ON questions(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_q_difficulty ON questions(difficulty)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_q_favorite ON questions(favorite)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_records (
                id TEXT PRIMARY KEY,
                question_id TEXT NOT NULL,
                user_answer TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL DEFAULT -1,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_r_question ON quiz_records(question_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_r_score ON quiz_records(score)")
    _seed_if_empty()


def _seed_if_empty() -> None:
    """首次使用时注入少量示例题目，方便用户上手（可随时删除）"""
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
        if count > 0:
            return
        now = int(time.time() * 1000)
        seeds = [
            ("frontend", json.dumps(["Vue"]), "Vue 中 computed 和 watch 的区别是什么？",
             "computed 是计算属性，依赖响应式数据自动缓存，只有依赖变化才重新计算，适合派生值；watch 是侦听器，监听数据变化执行副作用（如请求、操作 DOM），适合异步或开销大的操作。computed 默认有缓存，watch 没有。",
             "easy", "内置示例"),
            ("frontend", json.dumps(["JavaScript"]), "let、const、var 的区别？",
             "var 是函数作用域，存在变量提升；let/const 是块级作用域，有暂时性死区；const 声明常量，声明时必须赋值且不能重新赋值（但对象属性可改）。推荐优先使用 const，需要重新赋值时用 let。",
             "easy", "内置示例"),
            ("backend", json.dumps(["Java", "Spring"]), "Spring Bean 的生命周期？",
             "实例化 → 属性赋值 → Aware 接口回调 → BeanPostProcessor 前置处理 → 初始化（@PostConstruct / InitializingBean / init-method）→ BeanPostProcessor 后置处理 → 使用 → 销毁（@PreDestroy / DisposableBean / destroy-method）。",
             "medium", "内置示例"),
            ("database", json.dumps(["MySQL"]), "MySQL 索引的底层数据结构？为什么用 B+ 树？",
             "InnoDB 使用 B+ 树。相比 B 树，B+ 树非叶子节点只存键不存数据，单页能存更多键，树更矮；叶子节点通过双向链表连接，范围查询效率高；数据都在叶子节点，查询稳定。",
             "medium", "内置示例"),
            ("database", json.dumps(["Redis"]), "Redis 缓存穿透、击穿、雪崩的区别与解决方案？",
             "穿透：查询不存在的数据，每次打 DB。用布隆过滤器或缓存空值。击穿：热点 key 过期瞬间大量请求打 DB。用互斥锁或永不过期。雪崩：大量 key 同时过期或 Redis 宕机。用过期时间加随机值、多级缓存、熔断限流。",
             "hard", "内置示例"),
            ("algorithm", json.dumps(["动态规划"]), "动态规划的核心思想与解题步骤？",
             "核心：把复杂问题分解为重叠子问题，通过记忆化避免重复计算。步骤：1) 定义状态 dp[i] 的含义；2) 推导状态转移方程；3) 确定初始值和遍历顺序；4) 考虑空间优化。关键是找到「最优子结构」和「重叠子问题」。",
             "medium", "内置示例"),
            ("ai", json.dumps(["LLM", "RAG"]), "RAG（检索增强生成）的基本流程？",
             "1) 文档分块；2) 向量化（Embedding）并存入向量数据库；3) 用户提问时将问题向量化；4) 在向量库中检索 Top-K 相关文档块；5) 将检索结果与问题拼接成 Prompt 输入 LLM；6) LLM 基于检索内容生成回答。RAG 缓解幻觉并提供可溯源的最新知识。",
             "medium", "内置示例"),
        ]
        for cat, tags, title, answer, diff, src in seeds:
            qid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO questions (id, category, tags, title, answer, difficulty, source, favorite, created_at, updated_at) VALUES (?,?,?,?,?,?,?,0,?,?)",
                (qid, cat, tags, title, answer, diff, src, now, now)
            )
        conn.commit()


_init_db()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    try:
        d["tags"] = json.loads(d.get("tags") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["tags"] = []
    d["favorite"] = bool(d.get("favorite", 0))
    return d


def _normalize_tags(tags: Any) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    return []


# ---------- 请求模型 ----------

class QuestionCreate(BaseModel):
    category: str
    tags: list[str] = Field(default_factory=list)
    title: str
    answer: str = ""
    difficulty: str = "medium"
    source: str = ""
    favorite: bool = False


class QuestionUpdate(BaseModel):
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    title: Optional[str] = None
    answer: Optional[str] = None
    difficulty: Optional[str] = None
    source: Optional[str] = None
    favorite: Optional[bool] = None


class ImportItem(BaseModel):
    category: Optional[str] = None
    tags: Optional[Any] = None
    title: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    difficulty: Optional[str] = None
    source: Optional[str] = None


class ImportPayload(BaseModel):
    items: list[ImportItem]


# ---------- 路由 ----------

@router.get("/questions")
def list_questions(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    difficulty: Optional[str] = None,
    keyword: Optional[str] = None,
    favorite: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    clauses: list[str] = []
    params: list[Any] = []
    if category and category in _VALID_CATEGORIES:
        clauses.append("category = ?")
        params.append(category)
    if difficulty and difficulty in _VALID_DIFFICULTIES:
        clauses.append("difficulty = ?")
        params.append(difficulty)
    if favorite is not None:
        clauses.append("favorite = ?")
        params.append(1 if favorite else 0)
    if keyword:
        clauses.append("(title LIKE ? OR answer LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    with _get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM questions {where}", params).fetchone()["c"]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM questions {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()
    items = [_row_to_dict(r) for r in rows]
    # tag 过滤在内存做（tags 是 JSON 数组，SQL 过滤不便）
    if tag:
        items = [q for q in items if tag in q.get("tags", [])]
        total = len(items)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/questions/{qid}")
def get_question(qid: str):
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="题目不存在")
    return _row_to_dict(row)


@router.post("/questions")
def create_question(payload: QuestionCreate):
    if payload.category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"非法分类：{payload.category}")
    if payload.difficulty not in _VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"非法难度：{payload.difficulty}")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="题干不能为空")
    now = int(time.time() * 1000)
    qid = str(uuid.uuid4())
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO questions (id, category, tags, title, answer, difficulty, source, favorite, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (qid, payload.category, json.dumps(_normalize_tags(payload.tags), ensure_ascii=False),
             payload.title.strip(), payload.answer, payload.difficulty, payload.source,
             1 if payload.favorite else 0, now, now)
        )
        conn.commit()
    return get_question(qid)


@router.put("/questions/{qid}")
def update_question(qid: str, payload: QuestionUpdate):
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="题目不存在")
        cur = dict(row)
        updates: dict[str, Any] = {}
        if payload.category is not None:
            if payload.category not in _VALID_CATEGORIES:
                raise HTTPException(status_code=400, detail=f"非法分类：{payload.category}")
            updates["category"] = payload.category
        if payload.tags is not None:
            updates["tags"] = json.dumps(_normalize_tags(payload.tags), ensure_ascii=False)
        if payload.title is not None:
            if not payload.title.strip():
                raise HTTPException(status_code=400, detail="题干不能为空")
            updates["title"] = payload.title.strip()
        if payload.answer is not None:
            updates["answer"] = payload.answer
        if payload.difficulty is not None:
            if payload.difficulty not in _VALID_DIFFICULTIES:
                raise HTTPException(status_code=400, detail=f"非法难度：{payload.difficulty}")
            updates["difficulty"] = payload.difficulty
        if payload.source is not None:
            updates["source"] = payload.source
        if payload.favorite is not None:
            updates["favorite"] = 1 if payload.favorite else 0
        if not updates:
            return _row_to_dict(row)
        updates["updated_at"] = int(time.time() * 1000)
        sets = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE questions SET {sets} WHERE id = ?", list(updates.values()) + [qid])
        conn.commit()
    return get_question(qid)


@router.delete("/questions/{qid}")
def delete_question(qid: str):
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="题目不存在")
    return {"ok": True}


def _insert_items(items: list[dict]) -> tuple[int, int]:
    """共享插入逻辑（手动导入 / 文件导入 / AI 出题确认均走此路径）"""
    now = int(time.time() * 1000)
    inserted = 0
    skipped = 0
    with _get_conn() as conn:
        for item in items:
            title = str(item.get("title") or item.get("question") or "").strip()
            if not title:
                skipped += 1
                continue
            category = _norm_category(item.get("category"))
            difficulty = _norm_difficulty(item.get("difficulty"))
            tags = _normalize_tags(item.get("tags"))
            qid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO questions (id, category, tags, title, answer, difficulty, source, favorite, created_at, updated_at) VALUES (?,?,?,?,?,?,?,0,?,?)",
                (qid, category, json.dumps(tags, ensure_ascii=False), title,
                 str(item.get("answer") or ""), difficulty, str(item.get("source") or ""), now, now)
            )
            inserted += 1
        conn.commit()
    return inserted, skipped


def _parse_text_questions(text: str) -> list[dict]:
    """解析纯文本题库：空行分题，首行题干，「答：」开头为答案，可标注 分类/标签/难度"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    out: list[dict] = []
    for block in blocks:
        title = ""
        answer = ""
        category = ""
        difficulty = ""
        tags: list[str] = []
        for line in block.splitlines():
            line = line.rstrip()
            m = re.match(r"^(分类|category|类别|tag|标签|难度|difficulty)[:：]\s*(.+)$", line, re.IGNORECASE)
            if m:
                key = m.group(1).lower()
                val = m.group(2).strip()
                if key in ("分类", "category", "类别"):
                    category = val
                elif key in ("tag", "标签"):
                    tags += [t.strip() for t in re.split(r"[,，]", val) if t.strip()]
                else:
                    difficulty = val
                continue
            if re.match(r"^(答|答案|answer)[:：]", line, re.IGNORECASE):
                answer += re.sub(r"^(答|答案|answer)[:：]\s*", "", line, flags=re.IGNORECASE) + "\n"
            elif not title:
                title = line
            else:
                answer += line + "\n"
        if title.strip():
            item: dict = {"title": title.strip(), "answer": answer.strip()}
            if category:
                item["category"] = category
            if tags:
                item["tags"] = tags
            if difficulty:
                item["difficulty"] = difficulty
            out.append(item)
    return out


@router.post("/import")
def import_questions(payload: ImportPayload):
    inserted, skipped = _insert_items([item.model_dump() for item in payload.items])
    return {"inserted": inserted, "skipped": skipped}


@router.post("/import-file")
async def import_file(file: UploadFile = File(...)):
    """上传 .json / .txt / .md 文件批量导入（JSON 数组或纯文本格式）"""
    raw = await file.read()
    text: Optional[str] = None
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="无法识别文件编码，请使用 UTF-8 编码的 .json / .txt 文件")
    name = (file.filename or "").lower()
    items: list[dict] = []
    if name.endswith(".json") or text.strip().startswith("["):
        try:
            arr = json.loads(text)
            if isinstance(arr, list):
                items = [x for x in arr if isinstance(x, dict)]
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON 解析失败，请检查文件格式（应为题目对象数组）")
    else:
        items = _parse_text_questions(text)
    if not items:
        raise HTTPException(status_code=400, detail="未从文件解析到有效题目（文本需空行分题，「答：」开头为答案）")
    inserted, skipped = _insert_items(items)
    return {"inserted": inserted, "skipped": skipped}


@router.get("/quiz")
def quiz(
    categories: Optional[str] = None,
    tags: Optional[str] = None,
    difficulties: Optional[str] = None,
    count: int = Query(10, ge=1, le=100),
):
    """随机出题。categories/tags/difficulties 为逗号分隔字符串。"""
    clauses: list[str] = []
    params: list[Any] = []
    if categories:
        cats = [c for c in categories.split(",") if c in _VALID_CATEGORIES]
        if cats:
            placeholders = ",".join("?" * len(cats))
            clauses.append(f"category IN ({placeholders})")
            params.extend(cats)
    if difficulties:
        diffs = [d for d in difficulties.split(",") if d in _VALID_DIFFICULTIES]
        if diffs:
            placeholders = ",".join("?" * len(diffs))
            clauses.append(f"difficulty IN ({placeholders})")
            params.extend(diffs)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with _get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM questions {where}", params).fetchall()
    items = [_row_to_dict(r) for r in rows]
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            items = [q for q in items if any(t in q.get("tags", []) for t in tag_list)]
    if not items:
        return {"items": [], "total": 0}
    random.shuffle(items)
    picked = items[: min(count, len(items))]
    return {"items": picked, "total": len(picked)}


@router.get("/stats")
def stats():
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
        by_category = {r["category"]: r["c"] for r in conn.execute(
            "SELECT category, COUNT(*) AS c FROM questions GROUP BY category").fetchall()}
        by_difficulty = {r["difficulty"]: r["c"] for r in conn.execute(
            "SELECT difficulty, COUNT(*) AS c FROM questions GROUP BY difficulty").fetchall()}
        favorites = conn.execute("SELECT COUNT(*) AS c FROM questions WHERE favorite = 1").fetchone()["c"]
    return {
        "total": total,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "favorites": favorites
    }


# ---------------- 批量操作 ----------------

class BatchIdsPayload(BaseModel):
    ids: list[str]


class BatchUpdatePayload(BaseModel):
    ids: list[str]
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    difficulty: Optional[str] = None
    favorite: Optional[bool] = None
    source: Optional[str] = None


@router.post("/questions/batch-delete")
def batch_delete(payload: BatchIdsPayload):
    ids = [i for i in payload.ids if i]
    if not ids:
        raise HTTPException(status_code=400, detail="未选择题目")
    placeholders = ",".join("?" * len(ids))
    with _get_conn() as conn:
        cur = conn.execute(f"DELETE FROM questions WHERE id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM quiz_records WHERE question_id IN ({placeholders})", ids)
        conn.commit()
    return {"deleted": cur.rowcount}


@router.post("/questions/batch-update")
def batch_update(payload: BatchUpdatePayload):
    ids = [i for i in payload.ids if i]
    if not ids:
        raise HTTPException(status_code=400, detail="未选择题目")
    updates: dict[str, Any] = {}
    if payload.category is not None:
        if payload.category not in _VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"非法分类：{payload.category}")
        updates["category"] = payload.category
    if payload.tags is not None:
        updates["tags"] = json.dumps(_normalize_tags(payload.tags), ensure_ascii=False)
    if payload.difficulty is not None:
        if payload.difficulty not in _VALID_DIFFICULTIES:
            raise HTTPException(status_code=400, detail=f"非法难度：{payload.difficulty}")
        updates["difficulty"] = payload.difficulty
    if payload.favorite is not None:
        updates["favorite"] = 1 if payload.favorite else 0
    if payload.source is not None:
        updates["source"] = payload.source
    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    updates["updated_at"] = int(time.time() * 1000)
    placeholders = ",".join("?" * len(ids))
    sets = ", ".join(f"{k} = ?" for k in updates)
    with _get_conn() as conn:
        cur = conn.execute(
            f"UPDATE questions SET {sets} WHERE id IN ({placeholders})",
            list(updates.values()) + ids
        )
        conn.commit()
    return {"updated": cur.rowcount}


# ---------------- 导出 ----------------

@router.get("/export")
def export_questions(
    format: str = "json",
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """按筛选条件导出题目（json 可回导；text 与前端粘贴导入格式互通）"""
    clauses: list[str] = []
    params: list[Any] = []
    if category and category in _VALID_CATEGORIES:
        clauses.append("category = ?")
        params.append(category)
    if difficulty and difficulty in _VALID_DIFFICULTIES:
        clauses.append("difficulty = ?")
        params.append(difficulty)
    if keyword:
        clauses.append("(title LIKE ? OR answer LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with _get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM questions {where} ORDER BY category, updated_at DESC", params).fetchall()
    items = [_row_to_dict(r) for r in rows]

    stamp = time.strftime("%Y%m%d_%H%M%S")
    if format == "text":
        parts: list[str] = []
        for q in items:
            block = q["title"] + "\n"
            if q.get("answer"):
                block += "答：" + q["answer"].replace("\n", "\n") + "\n"
            block += f"分类：{_CATEGORY_ZH.get(q['category'], q['category'])}\n"
            if q.get("tags"):
                block += "标签：" + "、".join(q["tags"]) + "\n"
            block += f"难度：{_DIFFICULTY_ZH.get(q['difficulty'], q['difficulty'])}\n"
            parts.append(block)
        content = "\n\n".join(parts)
        fname = f"interview_bank_{stamp}.txt"
        media = "text/plain; charset=utf-8"
    else:
        export_list = [
            {"title": q["title"], "answer": q["answer"], "category": q["category"],
             "tags": q["tags"], "difficulty": q["difficulty"], "source": q.get("source") or ""}
            for q in items
        ]
        content = json.dumps(export_list, ensure_ascii=False, indent=2)
        fname = f"interview_bank_{stamp}.json"
        media = "application/json"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(fname)}"},
    )


# ---------------- 问答记录（错题本） ----------------

class RecordItem(BaseModel):
    question_id: str
    user_answer: str = ""
    score: int = -1


class RecordsPayload(BaseModel):
    items: list[RecordItem]


@router.post("/records")
def save_records(payload: RecordsPayload):
    now = int(time.time() * 1000)
    saved = 0
    with _get_conn() as conn:
        for r in payload.items:
            if not r.question_id:
                continue
            conn.execute(
                "INSERT INTO quiz_records (id, question_id, user_answer, score, created_at) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()), r.question_id, r.user_answer, r.score, now)
            )
            saved += 1
        conn.commit()
    return {"saved": saved}


@router.get("/records")
def list_records(
    scope: str = "wrong",
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """问答记录列表。scope: wrong(score<=1) / mastered(score>=2) / all"""
    clauses: list[str] = []
    params: list[Any] = []
    if scope == "wrong":
        clauses.append("r.score <= 1")
    elif scope == "mastered":
        clauses.append("r.score >= 2")
    if category and category in _VALID_CATEGORIES:
        clauses.append("q.category = ?")
        params.append(category)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    base_sql = "FROM quiz_records r JOIN questions q ON r.question_id = q.id"
    with _get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c {base_sql} {where}", params).fetchone()["c"]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT r.id AS rid, r.question_id, r.user_answer, r.score, r.created_at, q.* {base_sql} {where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()
    items = []
    for row in rows:
        d = dict(row)
        rid = d.pop("rid")
        q = _row_to_dict({k: d[k] for k in d.keys() & {"id", "category", "tags", "title", "answer", "difficulty", "source", "favorite", "created_at", "updated_at"}})
        q["id"] = d["question_id"]
        items.append({
            "id": rid,
            "questionId": d["question_id"],
            "userAnswer": d["user_answer"],
            "score": d["score"],
            "createdAt": d["created_at"],
            "question": q,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/records/stats")
def records_stats():
    with _get_conn() as conn:
        by_score = {str(r["score"]): r["c"] for r in conn.execute(
            "SELECT score, COUNT(*) AS c FROM quiz_records GROUP BY score").fetchall()}
        wrong_by_category = {r["category"]: r["c"] for r in conn.execute(
            "SELECT q.category AS category, COUNT(*) AS c FROM quiz_records r JOIN questions q ON r.question_id = q.id WHERE r.score <= 1 GROUP BY q.category").fetchall()}
        total = conn.execute("SELECT COUNT(*) AS c FROM quiz_records").fetchone()["c"]
    return {"total": total, "by_score": by_score, "wrong_by_category": wrong_by_category}


@router.delete("/records/{rid}")
def delete_record(rid: str):
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM quiz_records WHERE id = ?", (rid,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


# ---------------- AI 智能出题 ----------------

_LLM_CACHE = None


def _get_llm():
    global _LLM_CACHE
    if not os.getenv("LLM_API_KEY"):
        raise HTTPException(status_code=503, detail="后端未配置 LLM：请在 server/.env 中设置 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL")
    if _LLM_CACHE is not None:
        return _LLM_CACHE
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise HTTPException(status_code=503, detail="后端缺少依赖：请先 pip install langgraph langchain-openai")
    _LLM_CACHE = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL") or None,
        temperature=0.8,
        timeout=180,
        max_retries=2,
    )
    return _LLM_CACHE


def _extract_json_array(text: str) -> Optional[list]:
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("[")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
        start = text.find("[", start + 1)
    return None


class AiGeneratePayload(BaseModel):
    category: str = "other"
    difficulty: str = "medium"
    count: int = Field(5, ge=1, le=30)
    topic: str = ""
    extra: str = ""


@router.post("/ai-generate")
def ai_generate(payload: AiGeneratePayload):
    """AI 生成题目（仅返回预览数据，前端确认后调用 /import 入库）"""
    if payload.category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"非法分类：{payload.category}")
    if payload.difficulty not in _VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"非法难度：{payload.difficulty}")
    llm = _get_llm()
    cat_name = _CATEGORY_ZH.get(payload.category, payload.category)
    diff_name = _DIFFICULTY_ZH.get(payload.difficulty, payload.difficulty)
    topic = payload.topic.strip() or f"{cat_name}面试高频考点"
    prompt = (
        f"你是一名资深的{cat_name}技术面试官。请围绕主题「{topic}」出 {payload.count} 道面试题，整体难度「{diff_name}」。\n"
        + (f"补充要求：{payload.extra.strip()}\n" if payload.extra.strip() else "")
        + "要求：题目具体不空泛、贴近真实面试；参考答案准确、结构化、300字以内；每题配 1-3 个技术标签。\n"
        '严格只输出 JSON 数组，禁止输出任何解释文字或 markdown 标记，格式：\n'
        '[{"title":"题干","answer":"参考答案","difficulty":"easy|medium|hard","tags":["标签1","标签2"]}]'
    )
    try:
        resp = llm.invoke(prompt)
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}")
    arr = _extract_json_array(text)
    items: list[dict] = []
    if isinstance(arr, list):
        for a in arr:
            if not isinstance(a, dict):
                continue
            title = str(a.get("title") or "").strip()
            if not title:
                continue
            diff = a.get("difficulty") if a.get("difficulty") in _VALID_DIFFICULTIES else payload.difficulty
            items.append({
                "title": title,
                "answer": str(a.get("answer") or "").strip(),
                "category": payload.category,
                "difficulty": diff,
                "tags": _normalize_tags(a.get("tags")),
                "source": "AI 生成",
            })
    if not items:
        raise HTTPException(status_code=502, detail=f"AI 返回内容无法解析为题目，请重试或调整主题。原始返回片段：{text[:150]}")
    return {"items": items}
