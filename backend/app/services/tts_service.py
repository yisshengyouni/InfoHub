import asyncio
import edge_tts
import os
import tempfile
from pathlib import Path

# TTS 音频缓存目录
TTS_CACHE_DIR = Path(__file__).parent.parent / "static" / "tts_audio"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 语音映射：根据内容语言自动选择
VOICE_MAP = {
    "zh": "zh-CN-XiaoxiaoNeural",      # 中文女声
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "en": "en-US-JennyNeural",         # 英文女声
    "en-US": "en-US-JennyNeural",
    "en-GB": "en-GB-SoniaNeural",
    "ja": "ja-JP-NanamiNeural",        # 日文
    "ko": "ko-KR-SunHiNeural",         # 韩文
}

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


def detect_language(text: str) -> str:
    """简单语言检测：根据中文字符比例判断"""
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    total_chars = len(text.strip())
    
    if total_chars == 0:
        return "zh"
    
    chinese_ratio = chinese_chars / total_chars
    
    if chinese_ratio > 0.3:
        return "zh"
    else:
        return "en"


async def generate_tts_async(text: str, voice: str = None) -> str:
    """生成TTS音频，返回音频文件URL路径"""
    
    # 文本截断：最多3000字符（Edge TTS限制）
    if len(text) > 3000:
        text = text[:3000] + "..."
    
    # 自动选择语音
    if voice is None:
        lang = detect_language(text)
        voice = VOICE_MAP.get(lang, DEFAULT_VOICE)
    
    # 生成缓存文件名
    import hashlib
    cache_key = hashlib.md5(f"{text[:200]}_{voice}".encode()).hexdigest()
    audio_filename = f"{cache_key}.mp3"
    audio_path = TTS_CACHE_DIR / audio_filename
    
    # 如果已缓存，直接返回
    if audio_path.exists():
        return f"/tts_audio/{audio_filename}"
    
    # 生成TTS
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(audio_path))
    
    return f"/tts_audio/{audio_filename}"


def generate_tts(text: str, voice: str = None) -> str:
    """同步接口包装"""
    return asyncio.run(generate_tts_async(text, voice))
