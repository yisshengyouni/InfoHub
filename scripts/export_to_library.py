#!/usr/bin/env python3
"""export_to_library.py — InfoHub 阅读流 → 本地资料库 单向同步

架构定位（主公 2026-10-12 定调）：
- 资料库（~/Documents/资料库）是收藏价值的单一真源；
- InfoHub 阅读流（status=reading）= 资料库的「定时获取」通道，与手动发链接的「主动收藏」互补；
- 本脚本把阅读流条目按 collect 同款格式落盘（<分类>/<作者-短标题>/article.md），并追加 index.md。

查重：以 index.md 中是否已含条目 link 为准（与 collect 约定一致，脚本无状态、可重复跑）。
分类：关键词映射（见 CATEGORY_MAP），未命中归「其它」。
"""
import os
import re
import sqlite3
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO, "backend", "app", "data.db")
LIB = os.path.expanduser("/Users/zhonghaiqin/Documents/资料库")
INDEX = os.path.join(LIB, "index.md")
TODAY = date.today().isoformat()

# 关键词 → 资料库分类（taxonomy.md 现有六类；命中越靠前越优先）
CATEGORY_MAP = [
    (("AI", "Agent", "LLM", "RAG", "MCP", "prompt", "大模型"), "AI与Agent"),
    (("交易", "电商", "履约", "库存", "跨境"), "业务与行业"),
    (("研发效能", "DevOps", "测试", "架构", "后端", "数据库"), "工程实践"),
    (("产品", "交互", "设计"), "产品与设计"),
    (("工具", "开源", "效率"), "工具与资源"),
    # 区块链/安全类暂归其它 —— 待主公裁决是否新增分类后调整
]

def pick_category(tags: str, text: str) -> str:
    hay = f"{tags or ''} {(text or '')[:300]}"
    for keys, cat in CATEGORY_MAP:
        if any(k.lower() in hay.lower() for k in keys):
            return cat
    return "其它"

def short_title(title: str, limit: int = 15) -> str:
    s = re.sub(r"[，。！？、：；「」『』（）\[\]（）\s\"'“”·—…,.:;!?]", "", title or "")
    return s[:limit] or "未命名"

def author_display(author: str) -> str:
    # 库内 author 存 handle；知名作者补注真名（误注已被主公纠正过的不再犯）
    aliases = {"tombkeeper": "tombkeeper（于旸）"}
    return aliases.get(author or "", author or "佚名")

def main() -> int:
    if not os.path.exists(DB_PATH):
        print(f"ERR: db not found: {DB_PATH}")
        return 1
    with open(INDEX, encoding="utf-8") as f:
        index_text = f.read()

    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT id, title, link, author, published, summary, content, ai_summary, value_score, tags"
        " FROM contents WHERE status='reading' ORDER BY id"
    ).fetchall()

    exported, skipped = [], 0
    for r in rows:
        cat = pick_category(r["tags"], r["content"] or r["summary"] or "")
        disp = author_display(r["author"])
        d = os.path.join(LIB, cat, f"{r['author'] or '佚名'}-{short_title(r['title'])}")
        os.makedirs(d, exist_ok=True)
        article = os.path.join(d, "article.md")
        rel = os.path.relpath(article, LIB)
        # 查重：index.md 表格无 URL 列，以「路径」列为准（目录名由作者+标题确定性生成）
        if rel in index_text:
            skipped += 1
            continue
        published = (r["published"] or "unknown")[:10]
        tags = (r["tags"] or "未分类").replace(",", ", ")
        fm = (
            "---\n"
            f"title: {short_title(r['title'], 40) or r['title'][:40]}\n"
            "source: 微博\n"
            f"author: {disp}\n"
            f"published: {published}\n"
            f"url: {r['link']}\n"
            f"category: {cat}\n"
            f"tags: [{tags}]\n"
            f"collected: {TODAY}\n"
            "---\n\n"
        )
        note = (
            "\n\n---\n\n## 无咎注\n\n"
            f"- InfoHub 阅读流自动同步（value_score {r['value_score']}，{TODAY}）。\n"
            f"- 推荐理由：{r['ai_summary'] or '见正文'}\n"
            "- 微博原文如含配图，请移步原文链接查看（图床防盗链，暂未回存）。\n"
        )
        body = (r["content"] or r["summary"] or "").replace("\r\n", "\n")
        with open(article, "w", encoding="utf-8") as f:
            f.write(fm + body + note)
        row = (f"| {TODAY} | {short_title(r['title'], 40)} | {cat} | 微博 | {disp} | {tags} | {rel} |\n")
        with open(INDEX, "a", encoding="utf-8") as f:
            f.write(row)
        exported.append(f"id{r['id']} → {rel}")
        index_text += row  # 本轮内防重

    print(f"exported {len(exported)} / skipped {skipped}")
    for line in exported:
        print(" ", line)
    return 0

if __name__ == "__main__":
    sys.exit(main())
