import os
import requests
from app.database import get_db

def get_api_config():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ai_provider, ai_api_key, ai_model FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {
        "ai_provider": os.getenv("AI_PROVIDER", "openai"),
        "ai_api_key": os.getenv("AI_API_KEY", ""),
        "ai_model": os.getenv("AI_MODEL", "gpt-3.5-turbo")
    }

def generate_summary(text: str, max_length: int = 200) -> str:
    config = get_api_config()
    provider = config["ai_provider"]
    api_key = config["ai_api_key"]
    model = config["ai_model"]
    
    if not api_key:
        return "⚠️ 未配置AI API密钥，请在设置中添加。"
    
    prompt = f"请用{max_length}字以内总结以下内容：\n\n{text[:3000]}"
    
    if provider == "openai":
        return _call_openai(api_key, model, prompt)
    elif provider == "deepseek":
        return _call_deepseek(api_key, model, prompt)
    elif provider == "kimi":
        return _call_kimi(api_key, model, prompt)
    else:
        return _call_openai(api_key, model, prompt)

def _call_kimi(api_key: str, model: str, prompt: str) -> str:
    resp = requests.post(
        "https://api.moonshot.cn/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model or "kimi-k2.5", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]

def _call_openai(api_key: str, model: str, prompt: str) -> str:
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]

def _call_deepseek(api_key: str, model: str, prompt: str) -> str:
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]
