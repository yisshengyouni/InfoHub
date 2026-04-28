from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.tts_service import generate_tts

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice: str = None  # 可选：指定语音

class TTSResponse(BaseModel):
    audio_url: str
    voice: str
    duration_estimate: int  # 预估时长（秒）

@router.post("/", response_model=TTSResponse)
def create_tts(req: TTSRequest):
    try:
        audio_url = generate_tts(req.text, req.voice)
        # 预估时长： roughly 5 chars per second for Chinese, 15 for English
        duration = max(1, len(req.text) // 5)
        return TTSResponse(
            audio_url=audio_url,
            voice=req.voice or "auto",
            duration_estimate=duration
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS生成失败: {str(e)}")
