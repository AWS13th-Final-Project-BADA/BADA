"""법적 가드레일 — 사용자 대면 문장에서 '법률 단정' 표현을 차단·치환(규칙 기반).

LLM 요약·문장이 "불법/체불 확정/무조건 받을 수 있음/바로 신고" 같은 단정을 내면
미인가 법률자문으로 오해될 수 있다. 프롬프트로도 막지만, 출력단에서 한 번 더 거른다.
(product.md 표현 정책의 코드 구현)
"""
from __future__ import annotations

import re

# (패턴, 치환) — 단정 표현 → '의심/확인 필요' 톤
_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"불법(입니다|이에요|이고|이며|임|이다)?"), "확인이 필요한 사항입니다"),
    (re.compile(r"위법(입니다|이에요|임|이다|\s*행위)?"), "확인이 필요한 사항입니다"),
    (re.compile(r"법(을|률)?\s*위반(입니다|했|하였|이다|임)?"), "확인이 필요한 사항입니다"),
    (re.compile(r"체불(임금)?\s*(이|으로|가)?\s*(확정|입증|성립)(됩니다|되었습니다|됨|이다)"), "미지급 의심 항목입니다"),
    (re.compile(r"미지급\s*(이|가)?\s*확정(됩니다|되었습니다|됨|이다)"), "미지급 의심 항목입니다"),
    (re.compile(r"(무조건|반드시|당연히)\s*받(을\s*수\s*있습니다|습니다|아야|을\s*수\s*있어요)"),
     "받을 수 있는지는 전문기관 확인이 필요합니다"),
    (re.compile(r"바로\s*신고(하세요|하면\s*됩니다|하시면\s*됩니다)?"), "상담기관에 문의해 보세요"),
    (re.compile(r"신고하면\s*(이깁니다|이긴다|승소)"), "최종 판단은 전문기관에서 확인해야 합니다"),
    (re.compile(r"사업주(가|는)?\s*(처벌|구속)(됩니다|받습니다|될\s*수\s*있습니다)"), "확인이 필요한 사항입니다"),
]

# 탐지용(검수·테스트): 치환 후에도 남으면 안 되는 위험어.
# 거리 한정(.{0,3}) + '아님/아니' 부정 표현은 제외(예: "확정 아님"은 안전).
_FLAG = re.compile(
    r"불법|위법|법\s*위반"
    r"|(체불|미지급).{0,3}(확정|성립)(?!\s*(아님|아니|되지|되지\s*않))"
    r"|(무조건|반드시)\s*받(을|습)"
    r"|바로\s*신고"
    r"|사업주.{0,3}(처벌|구속)"
)


# 흔한 OCR 오타 보정(인용 정확도). 필요 시 추가.
_TYPO = [("아근수당", "야근수당")]

# 금액·연도 등 '큰 수'(4자리 이상, 콤마 포함) 토큰 추출용.
_AMOUNT = re.compile(r"\d[\d,]{3,}")


def sanitize(text: str) -> str:
    """단정 표현을 안전한 표현으로 치환 + 흔한 OCR 오타 보정한 문장을 반환."""
    if not text:
        return text
    for pat, repl in _RULES:
        text = pat.sub(repl, text)
    for wrong, right in _TYPO:
        text = text.replace(wrong, right)
    return text


def has_forbidden(text: str) -> bool:
    """치환 후에도 위험어가 남아있는지(검수·테스트용). '확정 아님' 등 부정형은 안전 처리."""
    return bool(_FLAG.search(text or ""))


def _amounts(text: str) -> set[str]:
    """문장에서 4자리 이상 숫자(금액·연도)를 정규화(콤마 제거)해 집합으로."""
    return {re.sub(r"[^\d]", "", m) for m in _AMOUNT.findall(text or "")}


def has_foreign_number(candidate: str, source: str) -> bool:
    """LLM 문장(candidate)에 출처(source)에 없는 '큰 수'가 있으면 True(숫자 환각 의심).

    돈·법이 걸린 서비스라, 문장화 과정에서 없던 숫자(예: 9,030)가 생기면 폐기해야 한다.
    날짜·소액(3자리 이하)은 오탐 방지를 위해 검사하지 않는다(4자리 이상만).
    """
    src = _amounts(source)
    return any(a and a not in src for a in _amounts(candidate))


def keep_grounded(candidate: str, source: str) -> str:
    """candidate에 환각 숫자가 있으면 결정론적 원문(source)으로 되돌린다."""
    if candidate and has_foreign_number(candidate, source):
        return source
    return candidate
