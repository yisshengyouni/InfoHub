from fastapi import APIRouter, HTTPException, Query
from app.database import get_db
from datetime import datetime, timedelta
import json

router = APIRouter()

@router.get("/")
def list_daily_picks(
    limit: int = Query(7, ge=1, le=30),
    offset: int = Query(0, ge=0)
):
    """获取每日精选列表（最新N天）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM daily_picks ORDER BY date DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/today")
def get_today_pick():
    """获取今天的精选（如果没有则返回最近一天的）"""
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("SELECT * FROM daily_picks WHERE date = ?", (today,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("SELECT * FROM daily_picks ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="No daily picks found")
    
    return dict(row)

@router.get("/{date}")
def get_pick_by_date(date: str):
    """获取指定日期的精选"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_picks WHERE date = ?", (date,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"No picks for {date}")
    
    return dict(row)

@router.get("/{date}/articles")
def get_pick_articles(date: str):
    """获取某日精选的完整文章内容"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT content_ids FROM daily_picks WHERE date = ?", (date,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No picks for {date}")
    
    content_ids = row["content_ids"].split(",")
    placeholders = ",".join(["?"] * len(content_ids))
    cursor.execute(
        f"SELECT * FROM contents WHERE id IN ({placeholders}) ORDER BY published DESC",
        content_ids
    )
    articles = cursor.fetchall()
    conn.close()
    
    return {
        "date": date,
        "count": len(articles),
        "articles": [dict(r) for r in articles]
    }

@router.post("/generate")
def generate_daily_pick(force: bool = False):
    """生成今天的每日精选"""
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 检查今天是否已生成
    cursor.execute("SELECT id FROM daily_picks WHERE date = ?", (today,))
    if cursor.fetchone() and not force:
        conn.close()
        return {"message": f"Today's pick ({today}) already exists. Use force=true to regenerate."}
    
    # 精选算法：取最近24小时内容
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    # 评分规则：
    # - 收藏 +10 分
    # - 来源权重（播客/rss 等按类型）
    # - 时间越新越靠前
    cursor.execute("""
        SELECT c.*, f.type as feed_type, f.name as feed_name,
               CASE 
                   WHEN c.is_starred = 1 THEN 10 
                   ELSE 0 
               END as star_score,
               CASE 
                   WHEN f.type = 'podcast' THEN 3
                   WHEN f.type = 'rss' THEN 2
                   ELSE 1
               END as type_score
        FROM contents c
        JOIN feeds f ON c.feed_id = f.id
        WHERE c.published >= ?
        ORDER BY (star_score + type_score) DESC, c.published DESC
        LIMIT 10
    """, (yesterday,))
    
    candidates = cursor.fetchall()
    
    if not candidates:
        #  fallback: 取最近的内容
        cursor.execute("""
            SELECT c.* FROM contents c
            ORDER BY c.published DESC LIMIT 10
        """)
        candidates = cursor.fetchall()
    
    content_ids = [str(r["id"]) for r in candidates[:8]]  # 取TOP 8
    article_count = len(content_ids)
    
    # 生成标题：取第一条的标题作为代表
    title = f"📰 {today} 每日精选 · {article_count} 篇"
    
    # 保存或更新
    if force:
        cursor.execute(
            "UPDATE daily_picks SET title = ?, content_ids = ?, article_count = ?, generated_at = CURRENT_TIMESTAMP WHERE date = ?",
            (title, ",".join(content_ids), article_count, today)
        )
    else:
        cursor.execute(
            "INSERT INTO daily_picks (date, title, content_ids, article_count) VALUES (?, ?, ?, ?)",
            (today, title, ",".join(content_ids), article_count)
        )
    
    conn.commit()
    conn.close()
    
    return {
        "date": today,
        "title": title,
        "article_count": article_count,
        "content_ids": content_ids,
        "message": "Daily pick generated successfully"
    }
