from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers import feeds, contents, summary, translate, settings, discover, tts, daily_picks

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
        return FileResponse(static_dir / "index.html")

    # SPA fallback - 所有非API路由返回index.html
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
else:
    @app.get("/")
    def root():
        return {"message": "Content Aggregator API is running!"}
