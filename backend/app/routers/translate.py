from fastapi import APIRouter, HTTPException
from app.schemas import TranslateRequest, TranslateResponse
from app.database import get_db

router = APIRouter()

@router.post("/", response_model=TranslateResponse)
def translate(req: TranslateRequest):
    from app.services.translator import translate_text
    
    try:
        translated = translate_text(req.text, target_language=req.target_language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE contents SET translated_summary = ? WHERE id = ?",
        (translated, req.content_id)
    )
    conn.commit()
    conn.close()
    
    return TranslateResponse(content_id=req.content_id, translated_text=translated)
