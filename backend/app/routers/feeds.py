from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.schemas import FeedCreate, Feed
import sqlite3

router = APIRouter()

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
    try:
        cursor.execute(
            "INSERT INTO feeds (name, url, type, category) VALUES (?, ?, ?, ?)",
            (feed.name, feed.url, feed.type, feed.category)
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
