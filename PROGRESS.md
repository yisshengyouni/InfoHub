# Content Aggregator - 订阅源能力扩展战报

## 🔥 本次新增订阅源能力

### ✅ 已支持的订阅源类型

| 平台 | 类型 | 状态 | 说明 |
|------|------|------|------|
| **RSS / Atom** | `rss` | ✅ 原生支持 | 任意标准RSS源：博客、新闻、知乎专栏等 |
| **播客 RSS** | `podcast` | ✅ 原生支持 | 小宇宙、苹果播客、Spotify、泛用型播客RSS |
| **微信公众号** | `wechat_search` | ✅ 搜狗搜索抓取 | 输入公众号名称，自动通过搜狗搜索抓取文章 |
| **微博搜索** | `weibo_search` | ⚠️ 受限 | 微博反爬严格，提供RSSHub桥接建议 |

### 🎙️ 播客支持详情

**已测试通过的播客源：**
- ✅ 放晴早安 — `https://feeds.fireside.fm/sunshine/rss`（358期）
- ✅ 声东击西 — `https://feeds.fireside.fm/shengdongjixi/rss`（412期）
- ✅ 任意 iTunes 播客 — 通过搜索API自动发现RSS地址

**播客特有功能：**
- 自动提取音频 enclosure（mp3/m4a）
- iTunes 搜索发现：输入播客名称，自动返回RSS订阅地址
- 音频URL存储在 `audio_url` 字段，后续可扩展播放器

### 📱 微信公众号支持详情

**抓取方式：** 搜狗微信搜索 (`weixin.sogou.com`)

**已测试：**
- ✅ 搜索"阮一峰" → 成功抓取10篇最新文章
- 每篇文章包含：标题、摘要、来源公众号、发布时间、原文链接

**使用方式：**
1. 选择类型"微信公众号"
2. 输入公众号名称（如"36氪"）
3. 点击"搜索公众号"（可选，用于确认存在）
4. 添加订阅 → 抓取文章

### 📝 微博支持详情

**现状：** 微博反爬机制严格，直接抓取受限。

**推荐方案：**
1. **RSSHub 桥接**（推荐）：`https://rsshub.app/weibo/user/{微博用户ID}`，然后作为普通RSS订阅
2. 在系统中选择"RSS"类型，粘贴RSSHub生成的链接

---

## 📊 当前数据库状态

```
订阅源分布:
  rss           → 3个（36氪、阮一峰、少数派）
  podcast       → 2个（放晴早安358期、声东击西412期）
  wechat_search → 1个（阮一峰公众号10篇文章）
  weibo_search  → 1个（待RSSHub桥接）

内容总计: 441条
播客音频: 358条（带音频URL）
```

---

## 🚀 如何使用

### 浏览器访问
```
http://localhost:8000
```

### API 直接调用
```bash
# iTunes 播客搜索
curl "http://localhost:8000/api/discover/podcast?query=播客名称"

# 微信公众号搜索（搜狗）
curl "http://localhost:8000/api/discover/wechat?query=公众号名称"

# 添加订阅
curl -X POST http://localhost:8000/api/feeds/ \
  -H "Content-Type: application/json" \
  -d '{"name":"测试","url":"wechat://公众号名","type":"wechat_search","category":"测试"}'

# 触发抓取
curl -X POST http://localhost:8000/api/feeds/{feed_id}/fetch
```

---

## 🎯 下一步建议

1. **音频播放器** — 给播客内容卡片加一个内嵌音频播放器
2. **H5移动端适配** — 优化手机端阅读体验
3. **定时自动抓取** — 后台定时任务，自动更新所有订阅源
4. **微博RSSHub引导** — 前端增加RSSHub链接生成器，帮助用户获取微博RSS

---

## 📁 新增/修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/services/feed_parser.py` | 重构为分发器，新增微信公众号/微博/播客解析 |
| `backend/app/routers/discover.py` | 新增 iTunes播客搜索 + 微信公众号搜索 |
| `backend/app/main.py` | 注册 discover 路由 |
| `backend/requirements.txt` | 新增 beautifulsoup4, lxml |
| `frontend/src/views/Feeds.vue` | 重写：平台类型选择 + 播客搜索 + 公众号搜索 |
| `frontend/src/api/index.js` | 新增 discover API |
| `backend/tests/test_fetch.py` | 自动测试脚本 |

队长，多平台订阅源能力已经上车！🔥 要冲音频播放器还是H5适配？
