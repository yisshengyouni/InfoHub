from fastapi import APIRouter, HTTPException
from app.schemas import SummaryRequest, SummaryResponse
from app.database import get_db

router = APIRouter()

@router.post("/", response_model=SummaryResponse)
def summarize(req: SummaryRequest):
    from app.services.ai_summarizer import generate_summary
    
    try:
        summary = generate_summary(req.text, length=req.length)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 根据长度存到对应字段
    if req.length == "short":
        cursor.execute("UPDATE contents SET ai_summary_short = ? WHERE id = ?", (summary, req.content_id))
    elif req.length == "long":
        cursor.execute("UPDATE contents SET ai_summary_long = ? WHERE id = ?", (summary, req.content_id))
    else:
        cursor.execute("UPDATE contents SET ai_summary = ? WHERE id = ?", (summary, req.content_id))
    
    conn.commit()
    conn.close()
    
    return SummaryResponse(content_id=req.content_id, summary=summary, length=req.length)
