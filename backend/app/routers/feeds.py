from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.schemas import FeedCreate, Feed, OPMLImport, OPMLExport
import sqlite3
import xml.etree.ElementTree as ET
from typing import List

router = APIRouter()

# === 自动标签映射 ===
AUTO_TAGS = {
    "rss": ["文章"],
    "podcast": ["播客", "音频"],
    "wechat_search": ["公众号", "微信"],
    "weibo_search": ["微博", "社交"],
}

def get_auto_tags(feed_type: str) -> str:
    """根据类型返回自动标签，逗号分隔"""
    tags = AUTO_TAGS.get(feed_type, [])
    return ",".join(tags) if tags else ""

@router.get("/", response_model=list[Feed])
def list_feeds():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feeds ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/", response_model=Feed)
def create_feed(feed: FeedCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    # 自动标签
    auto_tags = get_auto_tags(feed.type)
    
    try:
        cursor.execute(
            "INSERT INTO feeds (name, url, type, category, tags) VALUES (?, ?, ?, ?, ?)",
            (feed.name, feed.url, feed.type, feed.category, auto_tags)
        )
        conn.commit()
        feed_id = cursor.lastrowid
        cursor.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Feed URL already exists")

@router.delete("/{feed_id}")
def delete_feed(feed_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
    cursor.execute("DELETE FROM contents WHERE feed_id = ?", (feed_id,))
    conn.commit()
    conn.close()
    return {"message": "Feed deleted"}

@router.post("/{feed_id}/fetch")
def fetch_feed(feed_id: int):
    from app.services.feed_parser import fetch_feed as do_fetch
    result = do_fetch(feed_id)
    return result

@router.post("/fetch-all")
def fetch_all_feeds():
    from app.services.feed_parser import fetch_all_feeds as do_fetch_all
    return do_fetch_all()

# === Feed 统计：文章数 + 未读数 ===

@router.get("/stats")
def get_feed_stats():
    """返回每个订阅源的文章数和未读数"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            f.id,
            f.name,
            f.type,
            f.category,
            f.tags,
            COUNT(c.id) as article_count,
            SUM(CASE WHEN c.is_read = 0 THEN 1 ELSE 0 END) as unread_count
        FROM feeds f
        LEFT JOIN contents c ON f.id = c.feed_id
        GROUP BY f.id
        ORDER BY f.created_at DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# === Feed 标签管理 ===

@router.patch("/{feed_id}/tags")
def update_feed_tags(feed_id: int, tags: str):
    """更新订阅源标签"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE feeds SET tags = ? WHERE id = ?", (tags, feed_id))
    conn.commit()
    conn.close()
    return {"message": "Tags updated", "feed_id": feed_id, "tags": tags}

@router.post("/{feed_id}/auto-tag")
def auto_tag_feed(feed_id: int):
    """根据类型重新设置自动标签"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM feeds WHERE id = ?", (feed_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Feed not found")
    
    auto_tags = get_auto_tags(row["type"])
    cursor.execute("UPDATE feeds SET tags = ? WHERE id = ?", (auto_tags, feed_id))
    conn.commit()
    conn.close()
    return {"message": "Auto-tagged", "feed_id": feed_id, "tags": auto_tags}

@router.post("/auto-tag-all")
def auto_tag_all_feeds():
    """为所有订阅源批量设置自动标签"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type FROM feeds")
    feeds = cursor.fetchall()
    
    updated = 0
    for feed in feeds:
        auto_tags = get_auto_tags(feed["type"])
        cursor.execute("UPDATE feeds SET tags = ? WHERE id = ?", (auto_tags, feed["id"]))
        updated += 1
    
    conn.commit()
    conn.close()
    return {"message": f"Auto-tagged {updated} feeds"}

# === OPML 导入导出 ===

@router.post("/import-opml")
def import_opml(data: OPMLImport):
    conn = get_db()
    cursor = conn.cursor()
    added = 0
    skipped = 0
    errors = []
    
    for feed in data.feeds:
        try:
            cursor.execute(
                "INSERT INTO feeds (name, url, type, category) VALUES (?, ?, ?, ?)",
                (feed.name, feed.url, feed.type, feed.category)
            )
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as e:
            errors.append({"name": feed.name, "error": str(e)})
    
    conn.commit()
    conn.close()
    return {"added": added, "skipped": skipped, "errors": errors}

@router.get("/export-opml")
def export_opml():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feeds ORDER BY category, name")
    rows = cursor.fetchall()
    conn.close()
    
    feeds = []
    for row in rows:
        feeds.append({
            "name": row["name"],
            "url": row["url"],
            "type": row["type"],
            "category": row["category"] or "默认"
        })
    
    # 生成 OPML XML
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    title = ET.SubElement(head, "title")
    title.text = "Content Aggregator Feeds"
    
    body = ET.SubElement(root, "body")
    for feed in feeds:
        outline = ET.SubElement(body, "outline")
        outline.set("type", "rss")
        outline.set("text", feed["name"])
        outline.set("title", feed["name"])
        outline.set("xmlUrl", feed["url"])
        outline.set("category", feed["category"])
    
    xml_str = ET.tostring(root, encoding="unicode")
    return {"opml": xml_str}

@router.post("/import-opml-file")
def import_opml_file(opml_xml: str):
    """直接接收 OPML XML 字符串，解析并导入"""
    try:
        root = ET.fromstring(opml_xml)
        feeds = []
        
        # 遍历所有 outline
        for outline in root.findall(".//outline"):
            url = outline.get("xmlUrl") or outline.get("xmlurl")
            if url:
                feeds.append(FeedCreate(
                    name=outline.get("text") or outline.get("title") or "未命名",
                    url=url,
                    type="rss",
                    category=outline.get("category") or "默认"
                ))
        
        if not feeds:
            raise HTTPException(status_code=400, detail="No valid feeds found in OPML")
        
        return import_opml(OPMLImport(feeds=feeds))
    except ET.ParseError:
        raise HTTPException(status_code=400, detail="Invalid OPML XML")
