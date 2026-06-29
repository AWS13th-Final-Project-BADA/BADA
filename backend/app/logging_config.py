"""구조화 로깅 설정 — JSON 포맷 + request_id correlation.

CloudWatch Logs에서 JSON 파싱 가능, request_id로 한 요청의 로그를 추적.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

# request_id를 저장하는 ContextVar (미들웨어에서 설정, 로그에서 참조)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """로그 레코드에 request_id를 자동 주입하는 필터."""
    def filter(self, record):
        record.request_id = request_id_var.get("-")
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """JSON 로그 포맷터 — 타임스탬프, 레벨, 서비스명 포함."""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = record.created
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = "bada-backend"
        log_record["request_id"] = getattr(record, "request_id", "-")


def setup_logging(level: str = "INFO") -> None:
    """루트 로거를 JSON 구조화 포맷으로 설정."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(logger)s %(request_id)s %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addFilter(RequestIdFilter())

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
