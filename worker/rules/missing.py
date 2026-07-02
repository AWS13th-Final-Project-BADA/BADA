"""누락 증거 체크리스트 — 규칙 기반(domain.md). LLM 사용 금지."""
from __future__ import annotations

# 규칙: 어떤 카테고리/정보가 없으면 무엇을 안내할지
# reason은 FE i18n 키로 사용됨 (analysis.missingReason.{key})
RULES = [
    ("payment", "payment"),
    ("schedule", "schedule"),
    ("contract", "contract"),
    ("chat", "chat"),
]


def check_missing(present_categories: set[str]) -> list[dict]:
    """present_categories: 업로드된 증거 카테고리 집합.
    반환: [{"item": 카테고리, "reason": i18n 키}]
    """
    missing: list[dict] = []
    for category, reason_key in RULES:
        if category not in present_categories:
            missing.append({"item": category, "reason": reason_key})
    return missing
