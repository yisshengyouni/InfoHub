import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            audio_url TEXT,
            media_type TEXT,
            FOREIGN KEY (feed_id) REFERENCES feeds(id)
        )
    ''')

    # 迁移：为旧表添加新字段
    if not _column_exists(cursor, 'contents', 'audio_url'):
        cursor.execute("ALTER TABLE contents ADD COLUMN audio_url TEXT")
    if not _column_exists(cursor, 'contents', 'media_type'):
        cursor.execute("ALTER TABLE contents ADD COLUMN media_type TEXT")

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

    # 插入默认设置
    cursor.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")

    conn.commit()
    conn.close()
