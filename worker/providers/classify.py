"""문서 자동 분류 provider — 이미지 → 종류·관련성·신뢰도 (정확도 강화판).

정확도 전략(단일 호출 + 후처리로 비용 X):
  1) 근거(evidence) 강제 — 시각적 단서를 실제로 봤을 때만 적게 → 찍기/할루시네이션 ↓
  2) 헷갈리는 종류 구분 힌트(퓨샷) — 명세서 vs 계약서, 입금내역 vs 명세서
  3) 신뢰도 자동 다운그레이드 — 품질 나쁨·여러 서류 섞임·근거 없음이면 confidence↓
  4) 차선책(alternative) 출력 — 애매한 경계 케이스 식별
원칙: 분류 100% 목표 X. 잘 분류 + 애매하면 low(사람 위임) + 무관이면 relevant=false.
판단·계산 금지, 지어내지 말 것.

출력: {"category","relevant","confidence","reason","evidence","alternative",
       "multiple_docs","readable"}
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from config import PROVIDER_MODE

CATEGORIES = ("contract", "statement", "payment", "schedule", "chat", "other", "irrelevant")


class ClassifyResult(BaseModel):
    category: str                              # CATEGORIES 중 하나
    relevant: bool                             # 임금체불 증거로 쓸 수 있는가
    confidence: str                            # high | medium | low
    reason: str                                # 사람이 읽을 한 줄 근거
    evidence: list[str] = Field(default_factory=list)   # 실제 본 시각적 단서
    alternative: str | None = None             # 두 번째로 가능성 있는 종류
    multiple_docs: bool = False                # 한 이미지에 여러 서류가 섞였나
    readable: bool = True                      # 글자를 읽을 만한 품질인가


_SYSTEM = (
    "당신은 임금체불 사건 자료를 분류하는 도우미입니다. "
    "이미지에서 실제로 보이는 시각적 단서에만 근거해 종류를 판단하세요. "
    "근거(evidence)에는 진짜 본 것만 적고, 못 봤으면 빈 배열로 두세요. 절대 지어내지 마세요. "
    "불확실하거나 잘렸거나 흐리면 confidence를 낮추세요. 반드시 유효한 JSON만 출력하세요."
)

_INSTRUCTION = (
    "이 이미지를 아래 카테고리 중 하나로 분류하세요.\n"
    "- contract: 근로계약서·연봉계약서 (근무조건·임금·서명란이 핵심)\n"
    "- statement: 급여명세서 (이번 달 지급액·수당·공제·실수령액 '표'가 핵심)\n"
    "- payment: 통장 입금내역 (은행 앱/거래내역 — 입출금 '목록' 화면)\n"
    "- schedule: 근무표·출퇴근 기록·스케줄표\n"
    "- chat: 카카오톡·문자 등 대화 캡처 (말풍선)\n"
    "- other: 위에 안 맞지만 임금체불과 관련될 수 있는 자료\n"
    "- irrelevant: 셀카·음식·풍경 등 임금체불과 무관한 이미지\n\n"
    "[헷갈리기 쉬운 구분]\n"
    "· statement(명세서) vs contract(계약서): 명세서는 '지급/공제 금액 표', 계약서는 '근무조건+서명란'.\n"
    "· payment(입금내역) vs statement(명세서): payment는 '은행 거래 목록', statement는 '회사가 준 명세 표'.\n"
    "· 둘 다 애매하면 confidence를 medium/low로, alternative에 두 번째 후보를 적으세요.\n\n"
    "다음 JSON으로만 답하세요:\n"
    "{\n"
    '  "category": <위 카테고리 중 하나>,\n'
    '  "relevant": <true=증거 사용 가능 / false=irrelevant>,\n'
    '  "confidence": "high|medium|low",\n'
    '  "reason": <한국어 한 줄 근거>,\n'
    '  "evidence": [<이미지에서 실제로 본 시각적 단서 1~3개>],\n'
    '  "alternative": <두 번째로 가능성 있는 카테고리 또는 null>,\n'
    '  "multiple_docs": <한 이미지에 서로 다른 서류가 둘 이상 섞였으면 true>,\n'
    '  "readable": <글자를 읽을 만하면 true, 흐리거나 잘려 어려우면 false>\n'
    "}\n"
    "확실(뚜렷한 단서)=high, 비슷한 종류와 헷갈림=medium, 거의 못 읽거나 모호=low."
)


def _postprocess(res: ClassifyResult) -> dict:
    """모델 출력 + 규칙으로 신뢰도 보정(할루시네이션·품질 방어)."""
    cat = res.category if res.category in CATEGORIES else "other"
    conf = res.confidence if res.confidence in ("high", "medium", "low") else "low"
    notes: list[str] = []

    # 1) 품질 나쁨 → 무조건 low
    if not res.readable:
        conf = "low"
        notes.append("글자가 흐리거나 잘려 확실치 않아요")
    # 2) 여러 서류 섞임 → high 금지 + 분할 안내
    if res.multiple_docs:
        conf = "low" if conf == "high" else conf
        notes.append("한 장에 여러 서류가 섞여 보여요(나눠 올리면 정확해요)")
    # 3) 근거를 하나도 못 댐 → 찍었을 가능성 → 신뢰 낮춤
    if not res.evidence:
        conf = "low" if conf == "high" else "low" if conf == "medium" else conf
        notes.append("뚜렷한 근거가 안 보여 확인이 필요해요")

    reason = res.reason or ""
    if notes:
        reason = (reason + " · " if reason else "") + " / ".join(notes)

    return {
        "category": cat,
        "relevant": bool(res.relevant),
        "confidence": conf,
        "reason": reason,
        "evidence": res.evidence,
        "alternative": res.alternative,
        "multiple_docs": res.multiple_docs,
        "readable": res.readable,
    }


def classify(image_bytes: bytes) -> dict:
    """이미지 1장 분류. 로컬(mock)에선 보류값 반환(사람 확인 유도)."""
    if PROVIDER_MODE != "aws":
        return {"category": "other", "relevant": True, "confidence": "low",
                "reason": "로컬 모의 분류(실제 분류는 AWS 모드)", "evidence": [],
                "alternative": None, "multiple_docs": False, "readable": True}
    try:
        from providers import _bedrock
        blocks = [_bedrock.file_block(image_bytes, title="classify"),
                  _bedrock.text_block(_INSTRUCTION)]
        res = _bedrock.extract_json(_SYSTEM, blocks, ClassifyResult)
        return _postprocess(res)
    except Exception as e:  # noqa: BLE001
        # 분류 실패 = 버리지 않는다. other/보류로 두고 사람이 확인.
        return {"category": "other", "relevant": True, "confidence": "low",
                "reason": f"분류 실패, 확인 필요: {str(e)[:120]}", "evidence": [],
                "alternative": None, "multiple_docs": False, "readable": True}
