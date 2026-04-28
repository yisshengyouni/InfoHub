import os
import requests
from app.database import get_db

def get_translate_config():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT translate_provider, ai_api_key, target_language FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {
        "translate_provider": os.getenv("TRANSLATE_PROVIDER", "openai"),
        "ai_api_key": os.getenv("AI_API_KEY", ""),
        "target_language": os.getenv("TARGET_LANGUAGE", "zh")
    }

def translate_text(text: str, target_language: str = "zh") -> str:
    config = get_translate_config()
    provider = config["translate_provider"]
    api_key = config["ai_api_key"]
    
    if not api_key:
        return "⚠️ 未配置翻译API密钥。"
    
    prompt = f"请将以下内容翻译成{target_language}，保持原意和语气：\n\n{text[:3000]}"
    
    if provider == "openai":
        return _call_openai(api_key, prompt)
    elif provider == "deepseek":
        return _call_deepseek(api_key, prompt)
    elif provider == "kimi":
        return _call_kimi(api_key, prompt)
    else:
        return _call_openai(api_key, prompt)

def _call_kimi(api_key: str, prompt: str) -> str:
    resp = requests.post(
        "https://api.moonshot.cn/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "kimi-k2.5", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]

def _call_openai(api_key: str, prompt: str) -> str:
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]

def _call_deepseek(api_key: str, prompt: str) -> str:
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]
