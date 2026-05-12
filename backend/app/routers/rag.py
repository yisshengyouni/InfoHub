from fastapi import APIRouter, HTTPException
from app.database import get_db
from pydantic import BaseModel
from typing import List, Optional
import requests
import os

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    top_k: int = 5  # 检索多少篇文章作为上下文
    provider: Optional[str] = None  # 可选覆盖默认AI provider

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[dict]  # 引用的文章
    context_tokens: int  # 上下文token数估算

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

# === RAG 核心：检索 ===

def search_relevant_articles(query: str, top_k: int = 5):
    """使用FTS5全文搜索找到与问题相关的文章"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Step 1: FTS5 全文搜索
    cursor.execute("""
        SELECT rowid, rank FROM contents_fts 
        WHERE contents_fts MATCH ?
        ORDER BY rank LIMIT ?
    """, (query, top_k))
    fts_results = cursor.fetchall()
    
    article_ids = [r["rowid"] for r in fts_results]
    
    if not article_ids:
        # FTS5 没命中，fallback 到 LIKE 标题搜索
        cursor.execute("""
            SELECT id FROM contents 
            WHERE title LIKE ? OR summary LIKE ?
            ORDER BY published DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", top_k))
        article_ids = [r["id"] for r in cursor.fetchall()]
    
    if not article_ids:
        conn.close()
        return []
    
    # Step 2: 获取完整文章信息（只取需要的字段）
    placeholders = ",".join(["?"] * len(article_ids))
    cursor.execute(f"""
        SELECT c.id, c.title, c.summary, c.content, c.ai_summary, 
               c.translated_summary, c.link, c.published, f.name as feed_name
        FROM contents c
        LEFT JOIN feeds f ON c.feed_id = f.id
        WHERE c.id IN ({placeholders})
    """, article_ids)
    
    rows = cursor.fetchall()
    conn.close()
    
    # 按原始搜索顺序排列
    articles = []
    for aid in article_ids:
        for row in rows:
            if row["id"] == aid:
                articles.append(dict(row))
                break
    
    return articles

# === RAG 核心：构建上下文 ===

def build_context(articles: List[dict]) -> str:
    """将相关文章拼接成AI可理解的上下文"""
    context_parts = []
    for i, article in enumerate(articles, 1):
        # 优先使用已有摘要，其次是原文摘要，最后是标题
        content = article.get("ai_summary") or article.get("summary") or article.get("content", "")[:500]
        source = f"""
[{i}] 📰 {article['title']}
来源: {article.get('feed_name', '未知')} | {article.get('published', '')}
{content}
"""
        context_parts.append(source)
    
    return "\n---\n".join(context_parts)

# === AI 问答生成 ===

def get_ai_config():
    """获取AI配置，优先用settings表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ai_provider, ai_api_key, ai_model FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row and row["ai_api_key"]:
        return dict(row)
    
    # 环境变量fallback
    return {
        "ai_provider": os.getenv("AI_PROVIDER", "kimi"),
        "ai_api_key": os.getenv("KIMI_API_KEY", os.getenv("AI_API_KEY", "")),
        "ai_model": os.getenv("AI_MODEL", "kimi-k2.5")
    }

def call_ai_api(system_prompt: str, user_prompt: str, config: dict) -> str:
    """调用AI API生成回答"""
    provider = config.get("ai_provider", "kimi")
    api_key = config.get("ai_api_key", "")
    model = config.get("ai_model", "kimi-k2.5")
    
    if not api_key:
        return "⚠️ 未配置AI API密钥。请在设置中添加Kimi/OpenAI/DeepSeek的API Key后再试。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 统一使用OpenAI兼容格式
    base_url = "https://api.moonshot.cn/v1" if provider == "kimi" else \
               "https://api.deepseek.com/v1" if provider == "deepseek" else \
               "https://api.openai.com/v1"
    
    if provider == "deepseek":
        model = model or "deepseek-chat"
    elif provider == "openai":
        model = model or "gpt-3.5-turbo"
    else:
        model = model or "kimi-k2.5"
    
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=60
        )
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        return f"API返回异常: {data.get('error', data)}"
    except Exception as e:
        return f"调用AI API失败: {str(e)}"

# === API 接口 ===

@router.post("/search")
def rag_search(req: SearchRequest):
    """仅检索：根据问题找到相关文章"""
    articles = search_relevant_articles(req.query, req.top_k)
    return {
        "query": req.query,
        "count": len(articles),
        "articles": articles
    }

@router.post("/ask")
def rag_ask(req: AskRequest):
    """RAG问答：检索 + AI生成回答"""
    # 1. 检索相关文章
    articles = search_relevant_articles(req.question, req.top_k)
    
    if not articles:
        return AskResponse(
            question=req.question,
            answer="根据你的订阅库，没有找到与这个问题相关的文章。\n\n💡 建议：\n1. 添加更多相关订阅源\n2. 换个问法试试\n3. 检查AI API Key是否已配置",
            sources=[],
            context_tokens=0
        )
    
    # 2. 构建上下文
    context = build_context(articles)
    context_tokens = len(context) // 2  # 粗略估算（中文约2字符=1token）
    
    # 3. 构建System Prompt
    system_prompt = f"""你是一个基于用户订阅文章库的智能助手。请根据以下检索到的文章上下文，回答用户的问题。

要求：
1. 如果上下文中有足够信息，直接回答
2. 如果信息不足，说明清楚并给出你的理解
3. 引用文章时请标注来源编号，如"根据[1]..."
4. 保持简洁，控制在300字以内
5. 如果涉及多个观点，请对比说明

--- 上下文 ---
{context}
"""
    
    user_prompt = f"问题：{req.question}\n\n请基于以上上下文回答。"
    
    # 4. 调用AI生成回答
    config = get_ai_config()
    if req.provider:
        config["ai_provider"] = req.provider
    
    answer = call_ai_api(system_prompt, user_prompt, config)
    
    # 5. 精简sources（去掉content等冗余字段）
    sources = []
    for a in articles:
        sources.append({
            "id": a["id"],
            "title": a["title"],
            "feed_name": a.get("feed_name", "未知"),
            "published": a.get("published", ""),
            "link": a.get("link", ""),
            "summary": (a.get("ai_summary") or a.get("summary") or "")[:200] + "..."
        })
    
    return AskResponse(
        question=req.question,
        answer=answer,
        sources=sources,
        context_tokens=context_tokens
    )
