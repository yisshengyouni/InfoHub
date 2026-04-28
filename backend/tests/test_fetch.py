import sys
import os

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db, init_db
from app.services.feed_parser import fetch_feed
from app.routers.feeds import create_feed
from app.schemas import FeedCreate

# 测试用的公开 RSS 源
TEST_FEEDS = [
    {
        "name": "阮一峰的网络日志",
        "url": "https://www.ruanyifeng.com/blog/atom.xml",
        "category": "技术"
    },
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "category": "科技新闻"
    },
    {
        "name": "少数派",
        "url": "https://sspai.com/feed",
        "category": "效率工具"
    }
]

def test_database_init():
    """测试数据库初始化"""
    print("\n🔧 测试数据库初始化...")
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    required_tables = ['feeds', 'contents', 'settings']
    for table in required_tables:
        assert table in tables, f"表 {table} 不存在"
    print(f"  ✅ 数据库表检查通过: {tables}")

def test_add_feed():
    """测试添加订阅"""
    print("\n📡 测试添加订阅...")
    init_db()
    
    for feed_data in TEST_FEEDS:
        try:
            feed = FeedCreate(**feed_data)
            result = create_feed(feed)
            print(f"  ✅ 添加成功: {result['name']} (ID: {result['id']})")
        except Exception as e:
            # URL已存在或其他错误
            print(f"  ⚠️  {feed_data['name']}: {str(e)[:80]}")

def test_fetch_feed():
    """测试单个订阅抓取"""
    print("\n📥 测试单个订阅抓取...")
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, url FROM feeds LIMIT 1")
    feed = cursor.fetchone()
    conn.close()
    
    if not feed:
        print("  ⚠️  没有订阅源，跳过抓取测试")
        return
    
    print(f"  🎯 测试抓取: {feed['name']} ({feed['url'][:50]}...)")
    try:
        result = fetch_feed(feed['id'])
        print(f"  ✅ 抓取成功! 新条目: {result.get('new_items', 0)}, 总条目: {result.get('total', 0)}")
        
        # 验证数据是否写入数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM contents WHERE feed_id = ?", (feed['id'],))
        count = cursor.fetchone()['cnt']
        conn.close()
        print(f"  ✅ 数据库验证: 该订阅共有 {count} 条内容")
        
    except Exception as e:
        print(f"  ❌ 抓取失败: {str(e)}")
        raise

def test_fetch_all_feeds():
    """测试批量抓取"""
    print("\n📥 测试批量抓取所有订阅...")
    init_db()
    from app.services.feed_parser import fetch_all_feeds
    
    try:
        results = fetch_all_feeds()
        total_new = sum(r.get('new_items', 0) for r in results)
        total_entries = sum(r.get('total', 0) for r in results)
        print(f"  ✅ 批量抓取完成! 新条目: {total_new}, 总条目: {total_entries}")
        
        # 验证数据库内容
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM contents")
        total_contents = cursor.fetchone()['cnt']
        conn.close()
        print(f"  ✅ 数据库总内容数: {total_contents}")
        
    except Exception as e:
        print(f"  ❌ 批量抓取失败: {str(e)}")
        raise

def test_content_query():
    """测试内容查询"""
    print("\n🔍 测试内容查询...")
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM contents ORDER BY published DESC LIMIT 3")
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        print(f"  ✅ 查询到 {len(rows)} 条内容:")
        for row in rows:
            title = row['title'][:40] + '...' if len(row['title']) > 40 else row['title']
            print(f"     - {title}")
    else:
        print("  ⚠️  数据库中暂无内容")

def run_all_tests():
    """运行全部测试"""
    print("=" * 60)
    print("🧪 内容聚合器 - 数据抓取功能自动测试")
    print("=" * 60)
    
    try:
        test_database_init()
    except Exception as e:
        print(f"  ❌ 数据库初始化失败: {e}")
        return False
    
    try:
        test_add_feed()
    except Exception as e:
        print(f"  ❌ 添加订阅失败: {e}")
    
    try:
        test_fetch_feed()
    except Exception as e:
        print(f"  ❌ 单源抓取失败: {e}")
        return False
    
    try:
        test_fetch_all_feeds()
    except Exception as e:
        print(f"  ❌ 批量抓取失败: {e}")
        return False
    
    try:
        test_content_query()
    except Exception as e:
        print(f"  ❌ 内容查询失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 全部测试执行完毕!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
