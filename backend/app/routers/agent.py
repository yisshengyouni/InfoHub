"""
Agent 专用 API —— 本地 AI Agent（WorkBuddy）作为大脑的读写通道。

架构约定（2026-10-11 与主公定调）：
- 调度、抓取、价值判断、路由决策全部由外部 AI Agent 负责；
- 本服务只做存储与展示，不主动抓取、不主动调用 AI；
- Agent 通过本模块：拉订阅源清单（GET /feeds）、推送已筛选的内容（POST /ingest）。

鉴权：若设置了环境变量 INFOHUB_AGENT_TOKEN，则请求头须带 X-Agent-Token；
未设置视为本地模式，不校验（仅监听 localhost 时安全）。
"""
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.database import get_db

router = APIRouter()


def verify_agent_token(x_agent_token: Optional[str] = Header(default=None)):
    expected = os.getenv("INFOHUB_AGENT_TOKEN", "")
    if expected and x_agent_token != expected:
        raise HTTPException(status_code=401, detail="Invalid agent token")


class AgentFeedItem(BaseModel):
    id: int
    name: str
    url: str
    type: str
    category: Optional[str] = None
    tags: Optional[str] = None


class AgentIngestItem(BaseModel):
    """单条待入库内容。value_score 0~10；status: reading(阅读流) / archive(归档)，缺省 reading。"""
    feed_id: Optional[int] = None
    feed_url: Optional[str] = None  # 未带 feed_id 时按 url 匹配订阅源
    title: str
    link: str
    author: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    ai_summary: Optional[str] = None  # Agent 的一句话推荐理由
    value_score: Optional[float] = None
    status: str = "reading"
    tags: Optional[str] = None


class AgentIngestRequest(BaseModel):
    items: List[AgentIngestItem]


@router.get("/feeds", response_model=List[AgentFeedItem])
def agent_list_feeds(agent_token: None = Depends(verify_agent_token)):
    """Agent 拉取订阅源清单（含 homepage 等类型），据此决定抓什么。"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, url, type, category, tags FROM feeds ORDER BY id"
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@router.post("/ingest")
def agent_ingest(req: AgentIngestRequest, agent_token: None = Depends(verify_agent_token)):
    """Agent 推送筛选后的内容入库。按 link 去重；同时刷新对应订阅源的 last_fetched。"""
    if not req.items:
        return {"inserted": 0, "skipped": 0, "ids": [], "message": "empty items"}

    conn = get_db()
    cursor = conn.cursor()
    inserted, skipped, ids = 0, 0, []

    for item in req.items:
        # 去重：link 唯一
        cursor.execute("SELECT id FROM contents WHERE link = ?", (item.link,))
        if cursor.fetchone():
            skipped += 1
            continue

        feed_id = item.feed_id
        if feed_id is None and item.feed_url:
            cursor.execute("SELECT id FROM feeds WHERE url = ?", (item.feed_url,))
            row = cursor.fetchone()
            feed_id = row["id"] if row else None

        cursor.execute(
            """
            INSERT INTO contents
                (feed_id, title, link, author, published, summary, content,
                 ai_summary, value_score, status, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feed_id, item.title, item.link, item.author, item.published,
                item.summary, item.content, item.ai_summary,
                item.value_score, item.status, item.tags,
            ),
        )
        inserted += 1
        ids.append(cursor.lastrowid)

        if feed_id is not None:
            cursor.execute(
                "UPDATE feeds SET last_fetched = datetime('now', 'localtime') WHERE id = ?",
                (feed_id,),
            )

    conn.commit()
    conn.close()
    return {"inserted": inserted, "skipped": skipped, "ids": ids}
