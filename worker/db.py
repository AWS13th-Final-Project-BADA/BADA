"""Worker DB 세션 팩토리 — 2단계 전환용.

DATABASE_URL은 ECS Task Definition에서 Secrets Manager로 주입된다.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _engine_kwargs() -> dict:
    if not _DATABASE_URL or _DATABASE_URL.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}, "pool_pre_ping": True}
    connect_args = {}
    ssl_mode = os.environ.get("DATABASE_SSL_MODE", "")
    if ssl_mode:
        connect_args["sslmode"] = ssl_mode
    return {
        "pool_pre_ping": True,
        "pool_size": 3,
        "max_overflow": 5,
        "connect_args": connect_args,
    }


_engine = create_engine(_DATABASE_URL, **_engine_kwargs()) if _DATABASE_URL else None
_SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False) if _engine else None


def get_session() -> Session:
    """DB 세션 반환. DATABASE_URL 미설정 시 RuntimeError."""
    if _SessionFactory is None:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다 (Worker DB 직접 접근 불가)")
    return _SessionFactory()
