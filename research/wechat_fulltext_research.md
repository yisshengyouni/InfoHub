# 微信公众号全文抓取方案调研

## 方案对比

### 方案1: Wechat2RSS 公共服务 (推荐) ⭐
**地址**: https://wechat2rss.xlab.app

**优点**:
- 无需自建，开箱即用
- 已收录 300+ 公众号
- RSS格式输出（.atom/.rss/.json），可直接用现有RSS解析器
- 平均6小时时延，全文输出
- 图片视频代理，不怕防盗链

**缺点**:
- 依赖第三方服务
- 公开的公众号有限（未收录的需要走私有部署）

**API示例**:
```bash
# 添加订阅（获取公众号ID后）
POST https://wechat2rss.xlab.app/add/{公众号ID}?k={token}

# RSS订阅地址
GET https://wechat2rss.xlab.app/feed/{公众号ID}.xml

# 列表查询
GET https://wechat2rss.xlab.app/list?page=1&size=20
```

**免费收录的公众号**: 安全/开发类为主，可在 https://wechat2rss.xlab.app/#/ 查看完整列表

---

### 方案2: wewe-rss 自建 (基于微信读书)
**GitHub**: https://github.com/cooderl/wewe-rss

**优点**:
- 私有化部署，数据可控
- 支持任意公众号订阅（只要能分享到微信读书）
- 基于微信读书接口，相对官方稳定
- 支持全文输出、历史文章获取

**缺点**:
- 需要自建（Docker部署）
- 需要微信扫码登录微信读书
- 频繁操作可能触发风控

**部署方式**:
```yaml
# docker-compose.yml
services:
  app:
    image: cooderl/wewe-rss-sqlite:latest
    ports:
      - 4000:4000
    environment:
      - DATABASE_TYPE=sqlite
      - AUTH_CODE=your_auth_code
      - FEED_MODE=fulltext
      - CRON_EXPRESSION="35 5,17 * * *"
    volumes:
      - ./data:/app/data
```

**使用流程**:
1. 部署服务
2. 扫码登录微信读书账号
3. 分享公众号文章链接到服务
4. 获取RSS地址订阅

---

### 方案3: WeRSS (wang-h/hwerss)
**GitHub**: https://github.com/wang-h/hwerss

**特点**:
- 支持 web/api/app 多种采集模式
- 使用 Playwright 浏览器自动化
- 支持 AI 自动标签提取
- 支持热点发现、PDF/Markdown导出

**缺点**:
- 需要维护微信登录态（token/fakeid）
- 部署相对复杂

---

### 方案4: 直接抓取 mp.weixin.qq.com

**技术难点**:
1. 搜狗微信搜索的链接是加密的，需要解析 `/link?url=` 跳转
2. 微信文章页面 `mp.weixin.qq.com` 有反爬（需要处理`biz`、`sn`、`key`等参数）
3. 需要维护 Cookie/Token，容易触发验证码
4. 微信风控严格，频繁抓取会被限制

**优点**:
- 不依赖第三方服务
- 理论上可以抓取任意公众号

---

## 推荐集成方案

### 当前推荐：方案1 + 方案2 混合

**阶段1** - 快速接入 Wechat2RSS 公开服务：
- 新增订阅类型 "wechat2rss"
- 搜索公众号名称 -> 查询 wechat2rss.xlab.app 收录列表 -> 获取RSS地址
- 复用现有 RSS 解析逻辑，无需额外开发
- 适合大部分常见公众号

**阶段2** - 自建 wewe-rss 对接：
- 支持用户填写自己的 wewe-rss 实例地址
- 通过 wewe-rss API 添加公众号 -> 获取RSS地址
- 适合需要订阅小众/未收录公众号的用户

**阶段3** - 直接抓取兜底（可选）：
- 对于无法通过以上方式获取的公众号，尝试直接抓取文章
- 作为实验性功能，提示用户可能不稳定

---

## 具体实施建议

### 短期（本周可完成）
在 `wechat_search` 类型中增强：
1. 搜索时优先尝试从 Wechat2RSS 获取RSS地址
2. 如果 Wechat2RSS 有收录，直接转为 RSS 类型订阅
3. 如果未收录，提示用户 "该公众号未在Wechat2RSS收录，建议：a) 尝试自建wewe-rss b) 关注Wechat2RSS收录"

### 中期（下周）
1. 集成 wewe-rss API 调用能力
2. 前端增加 "私有微信读书RSS" 类型，支持填写自建实例地址

### 长期（可选）
1. 研究直接抓取 mp.weixin.qq.com 的可行性
2. 使用 Playwright/Selenium 作为兜底抓取方案
