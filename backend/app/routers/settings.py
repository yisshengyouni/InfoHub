from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.schemas import Settings
import sqlite3

router = APIRouter()

@router.get("/")
def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            "ai_provider": "openai",
            "ai_api_key": "",
            "ai_model": "gpt-3.5-turbo",
            "translate_provider": "openai",
            "target_language": "zh"
        }
    return dict(row)

@router.post("/")
def save_settings(settings: Settings):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO settings 
            (id, ai_provider, ai_api_key, ai_model, translate_provider, target_language)
            VALUES (1, ?, ?, ?, ?, ?)
        ''', (
            settings.ai_provider,
            settings.ai_api_key,
            settings.ai_model,
            settings.translate_provider,
            settings.target_language
        ))
        conn.commit()
        conn.close()
        return {"message": "Settings saved"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
