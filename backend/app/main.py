import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .errors import register_error_handlers
from .routers import ai_chat, analysis, cases, evidences, gps

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

init_db()  # SQLite 테이블 자동 생성

app = FastAPI(title="BADA API", description="상담 준비용 증거 정리 도구 - 법률자문 아님", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
register_error_handlers(app)

app.include_router(cases.router)
app.include_router(evidences.router)
app.include_router(analysis.router)
app.include_router(gps.router)
app.include_router(ai_chat.router)

_STATIC = Path(__file__).parent / "static"
_UPLOADS = Path(settings.upload_dir)
_UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(_UPLOADS)), name="files")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"name": "BADA", "version": "0.1.0", "auth_mode": settings.auth_mode,
            "storage_mode": settings.storage_mode}


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")
