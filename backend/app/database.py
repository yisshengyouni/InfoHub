import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            type TEXT DEFAULT 'rss',
            category TEXT,
            last_fetched TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            author TEXT,
            published TEXT,
            summary TEXT,
            content TEXT,
            ai_summary TEXT,
            translated_title TEXT,
            translated_summary TEXT,
            language TEXT DEFAULT 'zh',
            is_read BOOLEAN DEFAULT 0,
            is_starred BOOLEAN DEFAULT 0,
            tags TEXT,
            read_progress REAL DEFAULT 0,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            audio_url TEXT,
            media_type TEXT,
            FOREIGN KEY (feed_id) REFERENCES feeds(id)
        )
    ''')

    # === 性能优化：添加关键索引 ===
    # 文章列表查询索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_feed_id ON contents(feed_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_published ON contents(published DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_is_read ON contents(is_read)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_is_starred ON contents(is_starred)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_fetched_at ON contents(fetched_at)')
    # 复合索引：按订阅源+时间排序（最常用查询场景）
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_feed_published ON contents(feed_id, published DESC)')
    # FTS5全文搜索索引
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS contents_fts USING fts5(
            title, summary, content,
            content='contents',
            content_rowid='id'
        )
    ''')
    print("[DB] Indexes created/verified")

    # 迁移：为旧表添加新字段
    if not _column_exists(cursor, 'contents', 'tags'):
        cursor.execute("ALTER TABLE contents ADD COLUMN tags TEXT")
    if not _column_exists(cursor, 'contents', 'read_progress'):
        cursor.execute("ALTER TABLE contents ADD COLUMN read_progress REAL DEFAULT 0")

    # 迁移：为旧表添加新字段
    if not _column_exists(cursor, 'contents', 'audio_url'):
        cursor.execute("ALTER TABLE contents ADD COLUMN audio_url TEXT")
    if not _column_exists(cursor, 'contents', 'media_type'):
        cursor.execute("ALTER TABLE contents ADD COLUMN media_type TEXT")
    if not _column_exists(cursor, 'contents', 'tags'):
        cursor.execute("ALTER TABLE contents ADD COLUMN tags TEXT")
    if not _column_exists(cursor, 'contents', 'read_progress'):
        cursor.execute("ALTER TABLE contents ADD COLUMN read_progress REAL DEFAULT 0")
    if not _column_exists(cursor, 'contents', 'ai_summary_short'):
        cursor.execute("ALTER TABLE contents ADD COLUMN ai_summary_short TEXT")
    if not _column_exists(cursor, 'contents', 'ai_summary_long'):
        cursor.execute("ALTER TABLE contents ADD COLUMN ai_summary_long TEXT")
    
    # feeds 标签字段
    if not _column_exists(cursor, 'feeds', 'tags'):
        cursor.execute("ALTER TABLE feeds ADD COLUMN tags TEXT")
        print("[DB MIGRATION] Added feeds.tags column")
    else:
        print("[DB CHECK] feeds.tags column exists")

    # FTS5 全文搜索虚拟表
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS contents_fts USING fts5(
            title, summary, content,
            content='contents', content_rowid='id'
        )
    ''')
    
    # FTS5 触发器：自动同步
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS contents_fts_insert AFTER INSERT ON contents BEGIN
            INSERT INTO contents_fts(rowid, title, summary, content)
            VALUES (new.id, new.title, new.summary, new.content);
        END
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS contents_fts_delete AFTER DELETE ON contents BEGIN
            INSERT INTO contents_fts(contents_fts, rowid, title, summary, content)
            VALUES ('delete', old.id, old.title, old.summary, old.content);
        END
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS contents_fts_update AFTER UPDATE ON contents BEGIN
            INSERT INTO contents_fts(contents_fts, rowid, title, summary, content)
            VALUES ('delete', old.id, old.title, old.summary, old.content);
            INSERT INTO contents_fts(rowid, title, summary, content)
            VALUES (new.id, new.title, new.summary, new.content);
        END
    ''')

    # 为已有数据重建 FTS 索引（如果表是空的或刚创建）
    cursor.execute("SELECT count(*) FROM contents_fts")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO contents_fts(rowid, title, summary, content)
            SELECT id, title, summary, content FROM contents
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            ai_provider TEXT DEFAULT 'openai',
            ai_api_key TEXT,
            ai_model TEXT DEFAULT 'gpt-3.5-turbo',
            translate_provider TEXT DEFAULT 'openai',
            target_language TEXT DEFAULT 'zh'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            title TEXT,
            content_ids TEXT NOT NULL,
            article_count INTEGER DEFAULT 0,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认设置
    cursor.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")

    conn.commit()
    conn.close()
