"""OCR provider — 이미지/문서 → 텍스트·엔티티. 카테고리 기준 하이브리드 라우팅(tech.md).

엔진을 나눈 이유 = 강점이 다름:
  - 정형(contract/statement/schedule) → Upstage/Parseur : 표·셀·숫자 정밀
  - 비정형(chat/other/사진/앱캡처)     → Claude Vision     : 맥락·발화자 이해
  - 애매                              → Claude Vision (안전 기본값)

엄격 라우팅 — 강점이 다르므로 자동 강등(정형→Vision) 하지 않는다.
정형 엔진 키가 없으면 그 경로는 실패(ocr_status=failed)로 정직하게 표기한다.

출력: {"raw_text": str, "entities": dict}  (schema.OcrResult 검증 통과본)
판단·계산 금지 — 읽기/구조화만(architecture.md).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import PARSEUR_API_KEY, PROVIDER_MODE, STRUCTURED_ENGINE, UPSTAGE_API_KEY

STRUCTURED = {"contract", "statement", "schedule"}

_SYSTEM = (
    "당신은 임금체불 사건 증거에서 텍스트와 엔티티를 추출하는 도우미입니다. "
    "읽어서 구조화만 하고 위법 여부·금액을 판단하지 마세요. "
    "보이지 않는 값은 지어내지 말고, 불확실하면 confidence를 low로 표기하세요. "
    "반드시 유효한 JSON만 출력하세요."
)


def _instruction(category: str) -> str:
    from llm.prompts import load
    if category == "audio":
        return (
            "카테고리: 음성 녹음 전사본 (전화 통화 또는 대면 대화).\n"
            "아래 텍스트는 음성인식(STT)으로 전사된 대화 원문입니다. "
            "Speaker 0, Speaker 1 등의 화자 라벨이 있을 수 있습니다.\n\n"
            "이 대화에서 다음 엔티티를 추출하세요:\n"
            "- 금액(amounts: label+value) — 언급된 급여, 입금액, 공제 금액 등\n"
            "- 시급(hourly_wage) / 월급(monthly_wage)\n"
            "- 공제항목(deductions: name+amount)\n"
            "- 날짜(dates), 지급일(pay_date)\n"
            "- 근무일수(work_days), 연장근로(overtime_hours), 야간근로(night_hours), 휴일근로(holiday_hours)\n"
            "- 사업장명(workplace_name), 사업주명(employer_name)\n"
            "- 발화 분류(utterances: speaker, text, kind)\n"
            "  kind: wage_promise(지급약속) / work_order(근무지시) / "
            "underpayment_admit(미지급 인정) / evasive(회피) / other\n"
            "- 계약기간(contract_start, contract_end), 서명(signed=null)\n\n"
            "규칙:\n"
            "- raw_text는 전사 원문의 핵심 발화를 800자 이내로 요약하세요.\n"
            "- 금액은 콤마·'원'을 제거한 정수로. 불확실하면 confidence='low'.\n"
            "- 대화에서 직접 언급되지 않은 값은 지어내지 마세요(null).\n"
            "- 반드시 유효한 JSON만 출력하세요."
        )
    if category in ("chat", "other"):
        return (
            "카테고리: 메신저 대화 캡처 (카카오톡, 문자, SNS 등).\n"
            "이 이미지는 사업주와 근로자 간 메신저 대화 스크린샷입니다.\n\n"
            "## 추출 규칙\n"
            "1. raw_text: 이미지에 보이는 모든 대화 텍스트를 그대로 옮기세요 (발신자·시간 포함, 800자 이내).\n"
            "2. utterances: **반드시** 각 말풍선을 하나의 발화로 분리하세요.\n"
            "   - speaker: 발신자 이름 (예: '대표님', '응우옌', 이름 없으면 '발신자'/'수신자')\n"
            "   - text: 해당 말풍선 텍스트 (원문 그대로)\n"
            "   - kind: 아래 기준으로 분류\n"
            "     * wage_promise: 지급 약속 ('이번 주에 보낼게요', '금요일까지 입금')\n"
            "     * work_order: 근무 지시 ('내일 출근해', '야근 해')\n"
            "     * underpayment_admit: 미지급/삭감 인정 ('깜빡했어', '기숙사비 뺀 거')\n"
            "     * evasive: 회피/변명 ('원래 다 그래', '나중에 줄게')\n"
            "     * other: 그 외\n"
            "   - 대화에 말풍선이 있으면 utterances를 **절대 빈 배열로 두지 마세요**.\n"
            "3. 금액 추출: 대화에서 언급된 모든 금액을 amounts에 넣으세요.\n"
            "   - label: 무엇에 대한 금액인지 ('시급', '월급', '기숙사비', '식비', '입금액' 등)\n"
            "   - value: 콤마·'원' 제거한 정수\n"
            "4. hourly_wage: 시급이 언급되면 정수로 (예: '시급 10,030원' → 10030)\n"
            "5. monthly_wage: 월급이 언급되면 정수로\n"
            "6. deductions: 공제 항목이 언급되면 (예: '기숙사비 25만원' → name='기숙사비', amount=250000)\n"
            "7. dates: 대화에 언급된 날짜 (YYYY-MM-DD 형식)\n"
            "8. pay_date: 지급 약속 날짜가 있으면\n"
            "9. workplace_name, employer_name: 언급되면 추출\n"
            "10. signed=null (대화에서는 해당 없음)\n\n"
            "## 핵심 원칙\n"
            "- 대화에 보이는 금액·시급은 **반드시** amounts/hourly_wage에 넣으세요.\n"
            "- 말풍선이 1개라도 있으면 utterances에 넣으세요. 빈 배열 금지.\n"
            "- 불확실한 값은 confidence='low'로 표기하되, 보이는 값은 빠뜨리지 마세요.\n"
            "- 반드시 유효한 JSON만 출력하세요."
        )
    try:
        return load("extraction").replace("{{category}}", category)
    except Exception:
        return (f"카테고리: {category}. 이미지/문서의 모든 텍스트(raw_text)와 엔티티"
                "(dates, amounts[label,value], hourly_wage, monthly_wage, hours, "
                "deductions[name,amount](4대보험은 개별 항목), workplace_name, employer_name, "
                "pay_date, work_days, overtime_hours, night_hours, holiday_hours, "
                "contract_start, contract_end, signed, utterances[speaker,text,kind])를 "
                "JSON으로 추출하세요. 금액은 정수, 안 보이면 null.")


class OcrProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, category: str) -> dict:
        ...


class MockOcr(OcrProvider):
    """로컬 기본값. 실제 이미지 추출 없음 → 빈 결과(숫자는 사용자 입력 경로 사용)."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        return {"raw_text": "", "entities": {}}


class ClaudeVisionOcr(OcrProvider):
    """이미지/PDF → Bedrock Claude Vision(raw_text 추출) → Claude Text(엔티티 구조화). 2-pass."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        from providers import _bedrock

        # --- 1차: Vision으로 이미지에서 텍스트만 추출 ---
        vision_prompt = (
            "이 이미지는 임금체불 사건의 증거입니다. "
            "이미지에 보이는 모든 텍스트를 빠짐없이 그대로 추출하세요. "
            "표, 숫자, 이름, 날짜, 금액 등을 모두 포함하세요. "
            "줄바꿈을 유지하고, 텍스트만 출력하세요. JSON이 아닌 순수 텍스트로 응답하세요."
        )
        blocks = [
            _bedrock.file_block(image_bytes, title=category),
            _bedrock.text_block(vision_prompt),
        ]
        raw_text = _bedrock.invoke(
            "당신은 이미지에서 텍스트를 정확히 읽어내는 OCR 도우미입니다. "
            "보이는 텍스트를 그대로 옮기세요. 판단하지 마세요.",
            blocks, max_tokens=4000
        )

        # --- 2차: 추출된 텍스트에서 엔티티 구조화 ---
        return _structure_text(raw_text.strip(), category)


def _structure_text(text: str, category: str) -> dict:
    """정형문서에서 뽑은 텍스트 → Claude Text로 엔티티 구조화 (Upstage/Parseur 공용)."""
    from providers import _bedrock
    from providers.schema import OcrResult
    blocks = [_bedrock.text_block(_instruction(category) + "\n\n[문서 텍스트]\n" + text)]
    res = _bedrock.extract_json(_SYSTEM, blocks, OcrResult)
    return {"raw_text": text, "entities": res.entities.model_dump()}


class UpstageOcr(OcrProvider):
    """정형문서 → Upstage(텍스트/표) → Claude Text(엔티티 구조화). 2단계."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        from providers import _upstage
        return _structure_text(_upstage.document_parse(image_bytes), category)


class ParseurOcr(OcrProvider):
    """정형문서 → Parseur(텍스트) → Claude Text(엔티티 구조화). 2단계. (스텁)"""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        from providers import _parseur
        return _structure_text(_parseur.parse_document(image_bytes), category)


def _structured_provider() -> OcrProvider:
    # 기본(vision) 또는 키 없음 → Claude Vision. 명시적으로 upstage/parseur + 키 있을 때만 해당 엔진.
    if STRUCTURED_ENGINE == "upstage" and UPSTAGE_API_KEY:
        return UpstageOcr()
    if STRUCTURED_ENGINE == "parseur" and PARSEUR_API_KEY:
        return ParseurOcr()
    return ClaudeVisionOcr()


def get_ocr(category: str) -> OcrProvider:
    if PROVIDER_MODE != "aws":
        return MockOcr()
    # 기본은 전부 Claude Vision. STRUCTURED_ENGINE 설정 시 정형문서만 해당 엔진으로.
    return _structured_provider() if category in STRUCTURED else ClaudeVisionOcr()
