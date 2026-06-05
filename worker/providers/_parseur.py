"""Parseur Document Parsing 호출 — 정형문서(명세서 등) 추출 대안(Upstage 대신 선택 가능).

⚠️ 외부 SaaS. 문서가 외부로 전송됨(이미지 마스킹 불가) — Upstage와 동일한 개인정보 고려.
NOTE: Parseur는 메일박스/파서 기반 워크플로라, 사전에 대시보드에서 파서 설정이 필요.
      키 받으면 아래를 실제 API 호출로 구현. (https://help.parseur.com/en/articles/api)
"""
from __future__ import annotations

from config import PARSEUR_API_KEY


def parse_document(file_bytes: bytes, filename: str = "document") -> str:
    """문서 → 평문 텍스트. (구현 지점)

    구현 방향:
      1) POST 문서 to Parseur 파서(mailbox) — requests.post(upload_url, files=..., headers Bearer)
      2) 파싱 결과(필드 JSON 또는 텍스트) 수신
      3) 텍스트로 반환 → 상위에서 Claude로 엔티티 구조화(Upstage 경로와 동일)
    """
    if not PARSEUR_API_KEY:
        raise NotImplementedError("Parseur API 키 미설정 (.env PARSEUR_API_KEY)")
    raise NotImplementedError("Parseur API 연동 구현 필요 (파서 설정 + 업로드/결과 수신)")
