"""누락 증거 체크리스트 — 규칙 기반(domain.md). LLM 사용 금지."""
from __future__ import annotations

# 규칙: 어떤 카테고리/정보가 없으면 무엇을 안내할지
RULES = [
    ("payment", "통장 입금내역이 없습니다. 입금일·입금액 확인을 위해 통장 내역이 필요합니다."),
    ("schedule", "근무시간 근거가 없습니다. 출퇴근 기록 또는 근무표가 있으면 차액이 더 정확해집니다."),
    ("contract", "사업장 식별 정보가 부족합니다. 근로계약서 첫 페이지가 있으면 도움이 됩니다."),
    ("chat", "지급 약속 근거가 없습니다. 사업주와의 대화(카톡/문자)가 있으면 도움이 됩니다."),
]


def check_missing(present_categories: set[str]) -> list[dict]:
    """present_categories: 업로드된 증거 카테고리 집합.
    반환: [{"item": 카테고리, "reason": 안내문}]
    """
    missing: list[dict] = []
    for category, reason in RULES:
        if category not in present_categories:
            missing.append({"item": category, "reason": reason})
    return missing
