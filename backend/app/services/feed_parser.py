import feedparser
import html
import requests
from app.database import get_db
from datetime import datetime

def _clean_html(text):
    """清除HTML标签"""
    if not text:
        return ""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, "html.parser").get_text(strip=True)
    except:
        return text

def fetch_feed(feed_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
    feed = cursor.fetchone()
    if not feed:
        conn.close()
        return {"error": "Feed not found"}
    conn.close()
    
    feed_type = feed["type"] or "rss"
    
    if feed_type == "wechat_search":
        return _fetch_wechat_feed(feed)
    elif feed_type == "weibo_search":
        return _fetch_weibo_feed(feed)
    elif feed_type in ("podcast", "rss", "douyin", "xiaohongshu"):
        return _fetch_rss_feed(feed)
    else:
        return _fetch_rss_feed(feed)

def _fetch_rss_feed(feed):
    conn = get_db()
    cursor = conn.cursor()
    feed_id = feed["id"]
    
    parsed = feedparser.parse(feed["url"])
    new_count = 0
    
    for entry in parsed.entries:
        link = entry.get("link", "")
        
        cursor.execute("SELECT id FROM contents WHERE link = ?", (link,))
        if cursor.fetchone():
            continue
        
        title = html.unescape(str(entry.get("title", "无标题")))
        summary = html.unescape(str(entry.get("summary", entry.get("description", ""))))
        content_raw = entry.get("content", [{"value": ""}])
        content = str(content_raw[0].get("value", summary)) if content_raw else summary
        author = str(entry.get("author", ""))
        # 解析 published 为 ISO 8601 格式，便于数据库排序
        published_raw = entry.get("published", entry.get("updated", ""))
        published_iso = ""
        if published_raw:
            try:
                # feedparser 提供 parsed 时间元组
                pp = entry.get("published_parsed") or entry.get("updated_parsed")
                if pp:
                    published_iso = datetime(*pp[:6]).isoformat()
                else:
                    published_iso = str(published_raw)
            except Exception:
                published_iso = str(published_raw)
        else:
            published_iso = datetime.now().isoformat()
        published = published_iso
        
        # 提取播客/媒体文件（通用）
        audio_url = None
        media_type = None
        enclosures = entry.get("enclosures", [])
        if not enclosures:
            for lnk in entry.get("links", []):
                if lnk.get("rel") == "enclosure":
                    enclosures.append(lnk)
        
        if enclosures:
            enc = enclosures[0]
            audio_url = str(enc.get("href", enc.get("url", "")))
            media_type = str(enc.get("type", "audio/mpeg"))
        
        cursor.execute('''
            INSERT INTO contents 
            (feed_id, title, link, author, published, summary, content, audio_url, media_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (feed_id, title, link, author, published, summary, content, audio_url, media_type))
        new_count += 1
    
    cursor.execute(
        "UPDATE feeds SET last_fetched = ? WHERE id = ?",
        (datetime.now().isoformat(), feed_id)
    )
    conn.commit()
    conn.close()
    
    return {"feed_id": feed_id, "new_items": new_count, "total": len(parsed.entries)}

def _fetch_wechat_feed(feed):
    """微信公众号 - 优先 Wechat2RSS 全文订阅，回退搜狗搜索摘要"""
    conn = get_db()
    cursor = conn.cursor()
    feed_id = feed["id"]
    url = feed["url"]
    
    # 情况1: URL 是 wechat2rss 的 RSS 地址 → 直接用 RSS 解析获取全文
    if "wechat2rss" in url or url.endswith(".xml"):
        print(f"[Wechat] Feed {feed_id} 使用 Wechat2RSS 全文订阅")
        conn.close()
        # 复用 RSS 解析器，但返回 wechat 类型标记
        result = _fetch_rss_feed(feed)
        result["type"] = "wechat2rss"
        return result
    
    # 情况2: wechat:// 前缀 → 先尝试 Wechat2RSS，未收录再搜狗搜索
    keyword = url.replace("wechat://", "") if url.startswith("wechat://") else url
    
    try:
        from app.services.wechat2rss import get_wechat2rss_feed_url
        rss_url = get_wechat2rss_feed_url(keyword)
        if rss_url:
            print(f"[Wechat] Feed {feed_id} Wechat2RSS 已收录: {keyword}")
            # 更新 feed URL 为 RSS 地址
            cursor.execute("UPDATE feeds SET url = ?, type = ? WHERE id = ?", (rss_url, "wechat_search", feed_id))
            conn.commit()
            # 使用 RSS 解析
            feed["url"] = rss_url
            conn.close()
            result = _fetch_rss_feed(feed)
            result["type"] = "wechat2rss"
            result["message"] = "通过 Wechat2RSS 获取全文"
            return result
    except Exception as e:
        print(f"[Wechat] Wechat2RSS 查询失败: {e}")
    
    conn.close()
    
    # 情况3: 搜狗搜索抓取（只有列表和摘要）
    try:
        from bs4 import BeautifulSoup
        search_url = f"https://weixin.sogou.com/weixin?type=2&query={requests.utils.quote(keyword)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        articles = soup.select("ul.news-list li")
        new_count = 0
        
        conn = get_db()
        cursor = conn.cursor()
        
        for article in articles[:10]:
            try:
                title_elem = article.select_one("h3 a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link_raw = title_elem.get("href", "")
                if link_raw.startswith("/"):
                    link = f"https://weixin.sogou.com{link_raw}"
                else:
                    link = link_raw
                
                summary_elem = article.select_one("p")
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                from_elem = article.select_one("div.s-p")
                author = ""
                published = datetime.now().isoformat()
                if from_elem:
                    author_elem = from_elem.select_one("a.account")
                    if author_elem:
                        author = author_elem.get_text(strip=True)
                    time_elem = from_elem.select_one("span.s2 script")
                    if time_elem and time_elem.string:
                        import re
                        ts_match = re.search(r"(\d+)", time_elem.string)
                        if ts_match:
                            published = datetime.fromtimestamp(int(ts_match.group(1))).isoformat()
                
                cursor.execute("SELECT id FROM contents WHERE link = ?", (link,))
                if cursor.fetchone():
                    continue
                
                cursor.execute('''
                    INSERT INTO contents 
                    (feed_id, title, link, author, published, summary, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (feed_id, title, link, author, published, summary, summary))
                new_count += 1
                
            except Exception as e:
                continue
        
        cursor.execute(
            "UPDATE feeds SET last_fetched = ? WHERE id = ?",
            (datetime.now().isoformat(), feed_id)
        )
        conn.commit()
        conn.close()
        
        return {"feed_id": feed_id, "new_items": new_count, "total": len(articles), "type": "wechat", "source": "sogou"}
        
    except Exception as e:
        return {"feed_id": feed_id, "new_items": 0, "total": 0, "type": "wechat", "source": "sogou", "error": str(e)}

def _fetch_weibo_feed(feed):
    """微博 - 支持多种抓取方式，失败时提供友好提示"""
    conn = get_db()
    cursor = conn.cursor()
    feed_id = feed["id"]
    
    keyword = feed["url"]
    if keyword.startswith("weibo://"):
        keyword = keyword.replace("weibo://", "")
    
    # 尝试方式1: 微博移动端搜索API
    try:
        search_url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{requests.utils.quote(keyword)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        resp = requests.get(search_url, headers=headers, timeout=15)
        if resp.status_code == 200 and resp.text:
            data = resp.json()
            cards = data.get("data", {}).get("cards", [])
            new_count = 0
            
            for card in cards:
                if card.get("card_type") != 9:
                    continue
                mblog = card.get("mblog", {})
                if not mblog:
                    continue
                
                weibo_id = str(mblog.get("id", ""))
                link = f"https://weibo.com/{mblog.get('user', {}).get('id', '')}/{weibo_id}"
                title = _clean_html(mblog.get("text", "")[:60] + "..." if len(mblog.get("text", "")) > 60 else mblog.get("text", ""))
                content = _clean_html(mblog.get("text", ""))
                author = mblog.get("user", {}).get("screen_name", "")
                created_at = mblog.get("created_at", "")
                try:
                    published = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").isoformat()
                except:
                    published = datetime.now().isoformat()
                
                cursor.execute("SELECT id FROM contents WHERE link = ?", (link,))
                if cursor.fetchone():
                    continue
                
                pics = mblog.get("pics", [])
                image_urls = [p.get("large", {}).get("url", p.get("url", "")) for p in pics if p]
                video_url = None
                if mblog.get("page_info", {}).get("type") == "video":
                    video_url = mblog["page_info"].get("media_info", {}).get("stream_url", "")
                
                summary = content[:200] + "..." if len(content) > 200 else content
                
                cursor.execute('''
                    INSERT INTO contents 
                    (feed_id, title, link, author, published, summary, content, audio_url, media_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (feed_id, title, link, author, published, summary, content, 
                      video_url or (image_urls[0] if image_urls else None),
                      "video" if video_url else ("image" if image_urls else None)))
                new_count += 1
            
            cursor.execute(
                "UPDATE feeds SET last_fetched = ? WHERE id = ?",
                (datetime.now().isoformat(), feed_id)
            )
            conn.commit()
            conn.close()
            return {"feed_id": feed_id, "new_items": new_count, "total": len(cards), "type": "weibo"}
    except Exception:
        pass
    
    # 方式1失败，尝试方式2: 微博网页搜索（需要Cookie）
    try:
        search_url = f"https://s.weibo.com/weibo?q={requests.utils.quote(keyword)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html",
        }
        resp = requests.get(search_url, headers=headers, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 5000:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select('div[action-type="feed_list_item"]')
            if cards:
                new_count = 0
                for card in cards[:10]:
                    text_elem = card.select_one('p[node-type="feed_list_content"]')
                    if not text_elem:
                        continue
                    content = text_elem.get_text(strip=True)
                    title = content[:60] + "..." if len(content) > 60 else content
                    link = "https://s.weibo.com"  # 简化链接
                    author_elem = card.select_one('a.name')
                    author = author_elem.get_text(strip=True) if author_elem else ""
                    
                    cursor.execute("SELECT id FROM contents WHERE link = ?", (link,))
                    if cursor.fetchone():
                        continue
                    
                    cursor.execute('''
                        INSERT INTO contents 
                        (feed_id, title, link, author, published, summary, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (feed_id, title, link, author, datetime.now().isoformat(), content, content))
                    new_count += 1
                
                cursor.execute(
                    "UPDATE feeds SET last_fetched = ? WHERE id = ?",
                    (datetime.now().isoformat(), feed_id)
                )
                conn.commit()
                conn.close()
                return {"feed_id": feed_id, "new_items": new_count, "total": len(cards), "type": "weibo"}
    except Exception:
        pass
    
    conn.close()
    # 所有方式都失败，返回提示信息
    return {
        "feed_id": feed_id, 
        "new_items": 0, 
        "total": 0, 
        "type": "weibo", 
        "error": "微博抓取受限。建议：1) 通过 RSSHub 获取微博RSS: https://rsshub.app/weibo/user/{用户ID} 然后作为RSS订阅；2) 或将微博用户ID发给系统管理员手动添加"
    }

def fetch_all_feeds():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM feeds")
    feeds = cursor.fetchall()
    conn.close()
    
    results = []
    for feed in feeds:
        results.append(fetch_feed(feed["id"]))
    
    return results
