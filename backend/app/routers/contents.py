from fastapi import APIRouter, Query
from app.database import get_db
from app.schemas import Content
from typing import Optional

router = APIRouter()

@router.get("/", response_model=list[Content])
def list_contents(
    feed_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    is_starred: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    conn = get_db()
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if feed_id:
        conditions.append("feed_id = ?")
        params.append(feed_id)
    if is_read is not None:
        conditions.append("is_read = ?")
        params.append(1 if is_read else 0)
    if is_starred is not None:
        conditions.append("is_starred = ?")
        params.append(1 if is_starred else 0)
    if search:
        conditions.append("(title LIKE ? OR summary LIKE ? OR content LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    cursor.execute(
        f"SELECT * FROM contents {where_clause} ORDER BY published DESC LIMIT ? OFFSET ?",
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

@router.patch("/{content_id}/read")
def mark_read(content_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET is_read = 1 WHERE id = ?", (content_id,))
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

from fastapi import HTTPException
