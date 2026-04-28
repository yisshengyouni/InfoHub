# Content Aggregator

Vue 3 + Python FastAPI + SQLite 的全栈内容聚合工具，支持 RSS 订阅、AI 智能总结、多语言翻译。

## 🚀 快速启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

浏览器访问 `http://localhost:8000`

## 🏗 项目结构

```
content-aggregator/
├── backend/           # Python FastAPI 后端
│   ├── app/           # 应用代码
│   ├── requirements.txt
│   └── run.py
└── frontend/          # Vue 3 前端（构建产物已集成到 backend/app/static）
```

## ✨ 核心功能

- 📡 RSS / 播客 / 微信公众号 订阅
- 🤖 AI 智能总结（支持 OpenAI / DeepSeek / Kimi）
- 🌐 多语言翻译
- ⭐ 收藏标记 & 已读追踪
- 🔍 全文搜索

## 🛠 技术栈

- **后端**: Python 3.10+, FastAPI, SQLite
- **前端**: Vue 3, Vite, Pinia
- **AI 接口**: OpenAI / DeepSeek / Kimi (Moonshot)

## 📦 部署

支持 Render / Railway / Replit / Vercel 等平台部署。

详见 `render.yaml` 和 `railway.json` 配置文件。
