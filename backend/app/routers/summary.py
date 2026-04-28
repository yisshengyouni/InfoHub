from fastapi import APIRouter, HTTPException
from app.schemas import SummaryRequest, SummaryResponse
from app.database import get_db

router = APIRouter()

@router.post("/", response_model=SummaryResponse)
def summarize(req: SummaryRequest):
    from app.services.ai_summarizer import generate_summary
    
    try:
        summary = generate_summary(req.text, max_length=req.max_length)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET ai_summary = ? WHERE id = ?", (summary, req.content_id))
    conn.commit()
    conn.close()
    
    return SummaryResponse(content_id=req.content_id, summary=summary)
