import requests
import re
from datetime import datetime, timedelta

# Wechat2RSS 收录数据缓存
_wechat2rss_cache = {
    "data": {},  # {公众号名称: RSS地址}
    "last_fetch": None,
    "ttl_hours": 24
}

def _fetch_wechat2rss_list():
    """从 GitHub 获取 Wechat2RSS 收录的公众号列表"""
    try:
        # 获取公开的收录列表
        url = "https://raw.githubusercontent.com/ttttmr/Wechat2RSS/master/list/all.md"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        resp.raise_for_status()
        
        content = resp.text
        
        # 解析 Markdown 链接格式: [公众号名称](https://wechat2rss.xlab.app/feed/{id}.xml)
        pattern = r'\[([^\]]+)\]\((https://wechat2rss\.xlab\.app/feed/[^)]+\.xml)\)'
        matches = re.findall(pattern, content)
        
        result = {}
        for name, rss_url in matches:
            # 清理名称
            clean_name = name.strip()
            result[clean_name] = rss_url
        
        return result
    except Exception as e:
        print(f"[Wechat2RSS] 获取列表失败: {e}")
        return {}

def get_wechat2rss_list(force_refresh=False):
    """获取 Wechat2RSS 收录列表（带缓存）"""
    global _wechat2rss_cache
    
    now = datetime.now()
    cache_valid = (
        _wechat2rss_cache["last_fetch"] and 
        _wechat2rss_cache["data"] and
        (now - _wechat2rss_cache["last_fetch"] < timedelta(hours=_wechat2rss_cache["ttl_hours"]))
    )
    
    if not force_refresh and cache_valid:
        return _wechat2rss_cache["data"]
    
    data = _fetch_wechat2rss_list()
    if data:
        _wechat2rss_cache["data"] = data
        _wechat2rss_cache["last_fetch"] = now
        print(f"[Wechat2RSS] 已更新收录列表: {len(data)} 个公众号")
    
    return _wechat2rss_cache["data"]

def search_wechat2rss(keyword: str, limit: int = 10):
    """搜索 Wechat2RSS 收录的公众号"""
    data = get_wechat2rss_list()
    if not data:
        return []
    
    keyword_lower = keyword.lower()
    results = []
    
    for name, rss_url in data.items():
        if keyword_lower in name.lower():
            results.append({
                "name": name,
                "rss_url": rss_url,
                "source": "wechat2rss"
            })
        if len(results) >= limit:
            break
    
    return results

def get_wechat2rss_feed_url(name: str):
    """获取指定公众号的 Wechat2RSS 订阅地址"""
    data = get_wechat2rss_list()
    # 精确匹配
    if name in data:
        return data[name]
    # 模糊匹配
    for n, url in data.items():
        if name.lower() in n.lower() or n.lower() in name.lower():
            return url
    return None
