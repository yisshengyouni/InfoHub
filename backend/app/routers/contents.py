from fastapi import APIRouter, Query, HTTPException
from app.database import get_db
from app.schemas import Content, ContentUpdate
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()

# === 合并初始化API：一次请求返回所有页面所需数据 ===

@router.get("/init-data")
def get_init_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """一次性返回页面初始化所需所有数据，减少前端请求数"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. 订阅源列表
    cursor.execute("SELECT * FROM feeds ORDER BY created_at DESC")
    feeds = [dict(r) for r in cursor.fetchall()]
    
    # 2. 订阅源统计（使用索引COUNT）
    feed_stats = []
    for feed in feeds:
        cursor.execute("SELECT COUNT(*) FROM contents WHERE feed_id = ?", (feed["id"],))
        article_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM contents WHERE feed_id = ? AND is_read = 0",
            (feed["id"],)
        )
        unread_count = cursor.fetchone()[0]
        feed_stats.append({
            "id": feed["id"],
            "name": feed["name"],
            "type": feed["type"],
            "category": feed["category"],
            "tags": feed["tags"],
            "article_count": article_count,
            "unread_count": unread_count
        })
    
    # 3. 全局统计
    cursor.execute("SELECT COUNT(*) FROM contents")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM contents WHERE is_read = 0")
    unread = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM contents WHERE is_starred = 1")
    starred = cursor.fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM contents WHERE fetched_at >= ?", (today,))
    today_count = cursor.fetchone()[0]
    
    # 4. 文章列表第一页（最新50篇，使用索引）
    cursor.execute("""
        SELECT id, feed_id, title, link, author, published,
               summary, ai_summary, ai_summary_short, ai_summary_long,
               translated_title, translated_summary, language,
               is_read, is_starred, tags, read_progress, audio_url
        FROM contents
        ORDER BY published DESC
        LIMIT ? OFFSET ?
    """, (page_size, (page - 1) * page_size))
    contents = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "feeds": feeds,
        "feed_stats": feed_stats,
        "stats": {
            "total": total,
            "unread": unread,
            "starred": starred,
            "today": today_count
        },
        "contents": contents,
        "page": page,
        "page_size": page_size
    }

@router.get("/", response_model=list[Content])
def list_contents(
    feed_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    is_starred: Optional[bool] = None,
    search: Optional[str] = None,
    date_range: Optional[str] = None,  # today, week, month
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tags: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    conn = get_db()
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if feed_id:
        conditions.append("c.feed_id = ?")
        params.append(feed_id)
    if is_read is not None:
        conditions.append("c.is_read = ?")
        params.append(1 if is_read else 0)
    if is_starred is not None:
        conditions.append("c.is_starred = ?")
        params.append(1 if is_starred else 0)
    if tags:
        conditions.append("c.tags LIKE ?")
        params.append(f"%{tags}%")
    
    # 时间维度过滤 - 使用 >= 比较而非date()函数，确保索引生效
    if date_range:
        now = datetime.now()
        if date_range == "today":
            start = now.strftime("%Y-%m-%d")
            conditions.append("c.published >= ?")
            params.append(start)
        elif date_range == "week":
            start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            conditions.append("c.published >= ?")
            params.append(start)
        elif date_range == "month":
            start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            conditions.append("c.published >= ?")
            params.append(start)
    
    if start_date:
        conditions.append("c.published >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("c.published <= ?")
        params.append(end_date + " 23:59:59")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # 如果有搜索关键词，使用 FTS5
    if search and search.strip():
        search_term = search.strip()
        # 先查 FTS5 获取匹配的文章ID
        try:
            cursor.execute("""
                SELECT rowid FROM contents_fts 
                WHERE contents_fts MATCH ?
            """, (search_term,))
            matched_ids = [r[0] for r in cursor.fetchall()]
            
            if matched_ids:
                placeholders = ",".join(["?"] * len(matched_ids))
                # 结合其他条件从主表查询（只取需要的字段，排除content大字段）
                extra_where = f"AND {' AND '.join(conditions)}" if conditions else ""
                query = f"""
                    SELECT c.id, c.feed_id, c.title, c.link, c.author, c.published,
                           c.summary, c.ai_summary, c.ai_summary_short, c.ai_summary_long,
                           c.translated_title, c.translated_summary, c.language,
                           c.is_read, c.is_starred, c.tags, c.read_progress, c.audio_url
                    FROM contents c
                    WHERE c.id IN ({placeholders}) {extra_where}
                    ORDER BY c.published DESC LIMIT ? OFFSET ?
                """
                cursor.execute(query, matched_ids + params + [page_size, (page - 1) * page_size])
            else:
                # FTS5 没匹配到，fallback 到 LIKE
                conditions.append("(c.title LIKE ? OR c.summary LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
                where_clause = "WHERE " + " AND ".join(conditions)
                cursor.execute(
                    f"""SELECT c.id, c.feed_id, c.title, c.link, c.author, c.published,
                            c.summary, c.ai_summary, c.ai_summary_short, c.ai_summary_long,
                            c.translated_title, c.translated_summary, c.language,
                            c.is_read, c.is_starred, c.tags, c.read_progress, c.audio_url
                        FROM contents c {where_clause} ORDER BY c.published DESC LIMIT ? OFFSET ?""",
                    params + [page_size, (page - 1) * page_size]
                )
        except Exception:
            # FTS5 出错，fallback 到 LIKE
            conditions.append("(c.title LIKE ? OR c.summary LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])
            where_clause = "WHERE " + " AND ".join(conditions)
            cursor.execute(
                f"""SELECT c.id, c.feed_id, c.title, c.link, c.author, c.published,
                        c.summary, c.ai_summary, c.ai_summary_short, c.ai_summary_long,
                        c.translated_title, c.translated_summary, c.language,
                        c.is_read, c.is_starred, c.tags, c.read_progress, c.audio_url
                    FROM contents c {where_clause} ORDER BY c.published DESC LIMIT ? OFFSET ?""",
                params + [page_size, (page - 1) * page_size]
            )
    else:
        cursor.execute(
            f"""SELECT c.id, c.feed_id, c.title, c.link, c.author, c.published,
                    c.summary, c.ai_summary, c.ai_summary_short, c.ai_summary_long,
                    c.translated_title, c.translated_summary, c.language,
                    c.is_read, c.is_starred, c.tags, c.read_progress, c.audio_url
                FROM contents c {where_clause} ORDER BY c.published DESC LIMIT ? OFFSET ?""",
            params + [page_size, (page - 1) * page_size]
        )
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/{content_id}", response_model=Content)
def get_content(content_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    return dict(row)

@router.patch("/{content_id}")
def update_content(content_id: int, update: ContentUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    params = []
    if update.is_read is not None:
        updates.append("is_read = ?")
        params.append(1 if update.is_read else 0)
    if update.is_starred is not None:
        updates.append("is_starred = ?")
        params.append(1 if update.is_starred else 0)
    if update.tags is not None:
        updates.append("tags = ?")
        params.append(update.tags)
    if update.read_progress is not None:
        updates.append("read_progress = ?")
        params.append(max(0, min(100, update.read_progress)))
        # 如果进度超过90%，自动标记为已读
        if update.read_progress >= 90:
            updates.append("is_read = 1")
    
    if not updates:
        conn.close()
        return {"message": "No changes"}
    
    query = f"UPDATE contents SET {', '.join(updates)} WHERE id = ?"
    params.append(content_id)
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return {"message": "Updated"}

@router.patch("/{content_id}/read")
def mark_read(content_id: int, progress: Optional[float] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    if progress is not None:
        prog = max(0, min(100, progress))
        is_read = 1 if prog >= 90 else 0
        cursor.execute(
            "UPDATE contents SET is_read = ?, read_progress = ? WHERE id = ?",
            (is_read, prog, content_id)
        )
    else:
        cursor.execute("UPDATE contents SET is_read = 1, read_progress = 100 WHERE id = ?", (content_id,))
    
    conn.commit()
    conn.close()
    return {"message": "Marked as read"}

@router.patch("/{content_id}/star")
def toggle_star(content_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET is_starred = NOT is_starred WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()
    return {"message": "Star toggled"}

@router.delete("/{content_id}")
def delete_content(content_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contents WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()
    return {"message": "Content deleted"}

@router.get("/stats/overview")
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM contents")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contents WHERE is_read = 0")
    unread = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contents WHERE is_starred = 1")
    starred = cursor.fetchone()[0]
    
    # 今日新增 - 使用 >= 比较，利用索引
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM contents WHERE fetched_at >= ?", (today,))
    today_count = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total": total,
        "unread": unread,
        "starred": starred,
        "today": today_count
    }


def get_bilingual(content_id: int):
    """获取原文+译文对照"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, content, ai_summary, translated_title, translated_summary FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {
        "content_id": content_id,
        "original": {
            "title": row["title"],
            "summary": row["summary"] or row["content"] or "",
            "ai_summary": row["ai_summary"]
        },
        "translated": {
            "title": row["translated_title"],
            "summary": row["translated_summary"]
        },
        "has_translation": bool(row["translated_summary"])
    }
