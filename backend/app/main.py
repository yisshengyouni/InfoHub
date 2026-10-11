from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers import feeds, contents, summary, translate, settings, discover, tts, daily_picks, rag, agent

app = FastAPI(title="Content Aggregator API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feeds.router, prefix="/api/feeds", tags=["feeds"])
app.include_router(contents.router, prefix="/api/contents", tags=["contents"])
app.include_router(summary.router, prefix="/api/summary", tags=["summary"])
app.include_router(translate.router, prefix="/api/translate", tags=["translate"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(discover.router, prefix="/api/discover", tags=["discover"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
app.include_router(daily_picks.router, prefix="/api/daily-picks", tags=["daily_picks"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])

from app.scheduler import start_scheduler, stop_scheduler
from app.database import init_db
import os

@app.on_event("startup")
def on_startup():
    init_db()  # 裸 uvicorn 启动也自举建表/迁移，不依赖 run.py
    # 架构转向（2026-10-11）：调度收归本地 AI Agent，内置定时抓取默认关闭。
    # 需要旧的自动抓取行为时，设环境变量 INFOHUB_SCHEDULER=1。
    if os.getenv("INFOHUB_SCHEDULER", "0") == "1":
        start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()

# 挂载静态文件（前端构建产物）
static_dir = Path(__file__).parent / "static"
tts_dir = static_dir / "tts_audio"

if static_dir.exists():
    # 挂载 assets 目录
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    
    # 挂载 TTS 音频目录
    if tts_dir.exists():
        app.mount("/tts_audio", StaticFiles(directory=tts_dir), name="tts_audio")

    @app.get("/")
    def serve_index():
        return FileResponse(
            static_dir / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )

    # SPA fallback - 所有非API路由返回index.html
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(
                file_path,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
        return FileResponse(
            static_dir / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
else:
    @app.get("/")
    def root():
        return {"message": "Content Aggregator API is running!"}
