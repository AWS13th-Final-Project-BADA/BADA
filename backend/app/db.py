from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _engine_kwargs() -> dict:
    if settings.database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": True,
        }

    connect_args = {}
    if settings.database_ssl_mode:
        connect_args["sslmode"] = settings.database_ssl_mode

    return {
        "pool_pre_ping": True,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "connect_args": connect_args,
    }


engine = create_engine(settings.database_url, **_engine_kwargs())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """테이블 자동 생성. 앱 시작 시 호출."""
    from . import models  # noqa: F401  (모델 등록)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


def check_db_connection() -> dict:
    with engine.connect() as conn:
        dialect = conn.dialect.name
        result = conn.execute(text("select 1")).scalar_one()
    return {"ok": result == 1, "dialect": dialect}
