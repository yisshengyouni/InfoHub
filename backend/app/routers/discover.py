from fastapi import APIRouter, Query
import requests
from app.services.wechat2rss import search_wechat2rss, get_wechat2rss_feed_url

router = APIRouter()

@router.get("/podcast")
def search_podcast(query: str = Query(..., description="播客名称关键词"), limit: int = 10):
    """通过 iTunes API 搜索播客节目"""
    try:
        url = (
            f"https://itunes.apple.com/search"
            f"?term={requests.utils.quote(query)}"
            f"&media=podcast"
            f"&country=CN"
            f"&limit={limit}"
        )
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        results = []
        for item in data.get("results", []):
            results.append({
                "name": item.get("collectionName", ""),
                "artist": item.get("artistName", ""),
                "feed_url": item.get("feedUrl", ""),
                "cover": item.get("artworkUrl600", item.get("artworkUrl100", "")),
                "track_count": item.get("trackCount", 0),
                "genre": item.get("primaryGenreName", ""),
                "podcast_id": item.get("collectionId", ""),
                "url": item.get("collectionViewUrl", "")
            })
        
        return {"query": query, "count": len(results), "results": results}
    except Exception as e:
        return {"query": query, "count": 0, "results": [], "error": str(e)}

@router.get("/wechat")
def search_wechat_account(query: str = Query(..., description="微信公众号名称")):
    """搜索微信公众号 - 优先 Wechat2RSS，回退搜狗搜索"""
    results = []
    
    # 1. 先查 Wechat2RSS 收录
    try:
        w2r_results = search_wechat2rss(query, limit=10)
        for r in w2r_results:
            results.append({
                "name": r["name"],
                "source": "wechat2rss",
                "description": "Wechat2RSS 已收录，可全文订阅",
                "rss_url": r["rss_url"],
                "action": "subscribe_rss"  # 提示前端用 RSS 方式订阅
            })
    except Exception as e:
        pass
    
    # 2. 再查搜狗搜索（微信公众号）
    try:
        search_url = f"https://weixin.sogou.com/weixin?type=1&query={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(search_url, headers=headers, timeout=15)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        
        for item in soup.select("ul.news-list2 li")[:5]:
            name_elem = item.select_one("p.tit a")
            if not name_elem:
                continue
            name = name_elem.get_text(strip=True)
            
            # 如果 Wechat2RSS 已有，跳过
            if any(r["name"] == name for r in results):
                continue
            
            wechat_id = ""
            id_elem = item.select_one("label[name='weixinhao']")
            if id_elem:
                wechat_id = id_elem.get_text(strip=True)
            
            desc = ""
            desc_elem = item.select_one("dl dd")
            if desc_elem:
                desc = desc_elem.get_text(strip=True)
            
            results.append({
                "name": name,
                "wechat_id": wechat_id,
                "source": "sogou",
                "description": desc or "搜狗搜索发现，通过搜狗抓取文章列表",
                "action": "sogou_search"  # 提示前端用搜狗方式订阅
            })
    except Exception as e:
        pass
    
    return {"query": query, "count": len(results), "results": results}

@router.get("/wechat2rss")
def get_wechat2rss_feed(query: str = Query(..., description="微信公众号名称")):
    """直接获取 Wechat2RSS 订阅地址"""
    rss_url = get_wechat2rss_feed_url(query)
    if rss_url:
        return {"found": True, "name": query, "rss_url": rss_url}
    return {"found": False, "name": query, "rss_url": None}

@router.post("/wechat2rss/refresh")
def refresh_wechat2rss_cache():
    """手动刷新 Wechat2RSS 收录缓存"""
    from app.services.wechat2rss import get_wechat2rss_list
    data = get_wechat2rss_list(force_refresh=True)
    return {"count": len(data), "message": "缓存已刷新"}
