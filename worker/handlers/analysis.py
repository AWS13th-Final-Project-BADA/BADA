"""분석 handler — analyze_case 메시지 처리.

메시지 형식:
    {"type": "analyze_case", "case_id": "..."}

[1단계 — 현재] 백엔드 분석 API(POST /cases/{case_id}/analyze)를 호출한다.
    분석·DB 저장은 백엔드가 수행하므로 worker에 DB 연결이 없어도 동작한다.
    멱등성: 백엔드 /analyze 가 기존 결과를 삭제 후 재삽입하므로 중복 수신해도 안전.

[2단계 — 추후] worker가 DB에 직접 연결되면, 이 handle() 내부만 교체하여
    백엔드를 거치지 않고 직접 분석 + DB 저장한다. (consumer/인터페이스는 불변)

환경변수:
    BACKEND_BASE_URL  분석 API 베이스 URL (기본: http://localhost:8000)
    ANALYZE_HTTP_TIMEOUT  요청 타임아웃 초 (기본: 300)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
HTTP_TIMEOUT = int(os.environ.get("ANALYZE_HTTP_TIMEOUT", "300"))


def handle(message: dict) -> None:
    """analyze_case 메시지를 처리한다. 실패 시 예외를 올려 consumer가 재시도/DLQ 하게 한다."""
    case_id = message.get("case_id")
    if not case_id:
        raise ValueError("analyze_case: 'case_id' is required")

    url = f"{BACKEND_BASE_URL}/cases/{case_id}/analyze"
    logger.info("analyze_case 시작: case_id=%s → POST %s", case_id, url)

    req = urllib.request.Request(
        url,
        data=b"{}",  # 빈 본문 → 백엔드가 기본 AnalyzeRequest 로 처리
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            status = getattr(resp, "status", resp.getcode())
            resp.read()  # 응답 본문 소비(연결 정리)
            if status >= 400:
                raise RuntimeError(f"backend returned HTTP {status}")
    except urllib.error.HTTPError as e:
        body = e.read()[:300]
        raise RuntimeError(f"backend HTTP {e.code}: {body!r}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"backend unreachable: {e.reason}") from e

    logger.info("analyze_case 완료: case_id=%s (백엔드가 DB 저장)", case_id)
