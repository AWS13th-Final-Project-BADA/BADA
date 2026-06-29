import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import check_db_connection, init_db
from .errors import register_error_handlers
from .logging_config import setup_logging
from .middleware import SecurityHeadersMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_id import RequestIdMiddleware
from .middleware.prometheus import PrometheusMiddleware
from .routers import ai_chat, analysis, auth, cases, community, evidences, gps, kakao, notifications

setup_logging(level=os.environ.get("LOG_LEVEL", "INFO"))

if settings.database_auto_create:
    init_db()  # MVP 자동 테이블 생성. 운영/마이그레이션 도입 후 false 권장.

app = FastAPI(title="BADA API", description="상담 준비용 증거 정리 도구 - 법률자문 아님", version="0.1.0")

# ─── CORS: 허용 오리진 제한 (SECURITY-08) ────────────────────────────────────
_allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
if not _allowed_origins or _allowed_origins == [""]:
    # 기본값: 로컬 개발 + 프로덕션 도메인
    _allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://badasoft.com",
        "https://www.badasoft.com",
        "https://api.badasoft.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PrometheusMiddleware)
register_error_handlers(app)

app.include_router(cases.router)
app.include_router(evidences.router)
app.include_router(analysis.router)
app.include_router(gps.router)
app.include_router(ai_chat.router)
app.include_router(auth.router)
app.include_router(kakao.router)
app.include_router(community.router)
app.include_router(notifications.router)

_STATIC = Path(__file__).parent / "static"
_UPLOADS = Path(settings.upload_dir)
_UPLOADS.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(_UPLOADS)), name="files")
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


# PWA: manifest·서비스워커는 루트 scope에서 서빙해야 앱 전체를 제어할 수 있음.
@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(_STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(_STATIC / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    return check_db_connection()


@app.get("/version")
def version():
    return {"name": "BADA", "version": "0.1.0", "auth_mode": settings.auth_mode,
            "storage_mode": settings.storage_mode}


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")
