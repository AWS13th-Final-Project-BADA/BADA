"""증거 수집 에이전트 — 오케스트레이션 + 규칙 + 안전 등급 통합 테스트.

목적(가상환경 #1): AWS 없이, 두 '지능' 경계(classify, OCR)만 제어해서
그 위의 흐름(assess_scan/deep/batch)과 규칙 교차검증(_decide)이
모든 시나리오에서 '안전하게' 동작하는지 결정적으로 검증한다.

여기서 검증하는 불변식(architecture.md / product.md):
  - 자동 확정 금지: 스캔(내용 미확인)은 절대 auto_accept 안 함 → 항상 needs_review.
  - 보수적 등급: 충돌/다중문서/저품질/근거없음이면 사람 확인(review)으로 강등.
  - 무관 이미지는 후보에서 제외(rejected), 그 외는 버리지 않는다(HITL 안전망).
"""
import config
import services.evidence_intake as ei
from services.evidence_intake import (
    DECISION_AUTO,
    DECISION_REJECT,
    DECISION_REVIEW,
    _decide,
    assess_batch,
    assess_deep,
    assess_scan,
)

# 내용 키워드가 'statement'(급여명세서)와 일치하는 텍스트
STATEMENT_TEXT = "급여명세서 기본급 수당 공제 실수령 지급총액"
# 내용이 'statement' 강한 신호인데 형태를 contract라고 했을 때 → 충돌
STATEMENT_STRONG = "급여명세서 지급총액 공제총액 실수령 기본급 수당"


def setup_function(_):
    config.PROVIDER_MODE = "local"


def _patch_classify(monkeypatch, **over):
    """classify가 내놓을 결과를 고정(실제 LLM 호출 없이 시나리오 주입)."""
    base = {
        "category": "statement", "relevant": True, "confidence": "high",
        "reason": "지급/공제 표가 보임", "evidence": ["지급총액", "공제"],
        "alternative": None, "multiple_docs": False, "readable": True,
    }
    base.update(over)
    monkeypatch.setattr(ei.classify_mod, "classify", lambda _img: base)
    return base


def _patch_ocr(monkeypatch, text: str):
    """OCR이 읽어올 텍스트를 고정(MockOcr 대신 제어된 텍스트 주입)."""
    class _FakeOcr:
        def extract(self, image_bytes, category):
            return {"raw_text": text, "entities": {}}

    monkeypatch.setattr(ei, "get_ocr", lambda _cat: _FakeOcr())


# ── 스캔 단계: 내용 미확인 → 절대 auto 금지 ──────────────────────

def test_scan_high_confidence_is_still_review_not_auto(monkeypatch):
    # 형태 분류가 high여도, OCR 전이므로 자동확정 금지
    _patch_classify(monkeypatch, confidence="high")
    res = assess_scan(b"img")
    assert res["decision"] == DECISION_REVIEW
    assert res["category"] == "statement"
    assert res["confidence"] == "high"  # 우선순위 정보는 보존


def test_scan_irrelevant_is_rejected(monkeypatch):
    _patch_classify(monkeypatch, category="irrelevant", relevant=False, confidence="high")
    res = assess_scan(b"img")
    assert res["decision"] == DECISION_REJECT
    assert res["category"] == "irrelevant"


def test_scan_not_relevant_flag_rejects_even_if_category_set(monkeypatch):
    # category는 그럴듯해도 relevant=False면 제외
    _patch_classify(monkeypatch, category="statement", relevant=False)
    res = assess_scan(b"img")
    assert res["decision"] == DECISION_REJECT


# ── 배치 스캔: 등급 집계 + recommended(=rejected 제외) ───────────

def test_batch_summary_and_recommended_exclude_rejected(monkeypatch):
    # 첫 두 장은 관련(review), 세 번째는 무관(reject)으로 번갈아 분류
    seq = iter([
        {"category": "statement", "relevant": True, "confidence": "high",
         "reason": "", "evidence": ["x"], "alternative": None,
         "multiple_docs": False, "readable": True},
        {"category": "payment", "relevant": True, "confidence": "medium",
         "reason": "", "evidence": ["y"], "alternative": None,
         "multiple_docs": False, "readable": True},
        {"category": "irrelevant", "relevant": False, "confidence": "high",
         "reason": "", "evidence": [], "alternative": None,
         "multiple_docs": False, "readable": True},
    ])
    monkeypatch.setattr(ei.classify_mod, "classify", lambda _img: next(seq))

    out = assess_batch([("a.jpg", b"1"), ("b.jpg", b"2"), ("selfie.jpg", b"3")])

    assert sum(out["summary"].values()) == 3
    assert out["summary"][DECISION_REVIEW] == 2
    assert out["summary"][DECISION_REJECT] == 1
    assert out["summary"][DECISION_AUTO] == 0  # 스캔은 auto 없음
    assert set(out["recommended"]) == {"a.jpg", "b.jpg"}  # selfie 제외


# ── 정밀 단계: 형태 + 내용 교차검증으로 최종 등급 ─────────────────

def test_deep_high_and_content_agree_is_auto_high(monkeypatch):
    _patch_classify(monkeypatch, category="statement", confidence="high")
    _patch_ocr(monkeypatch, STATEMENT_TEXT)
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_AUTO
    assert res["confidence"] == "high"
    assert res["keyword_check"]["agree"] is True


def test_deep_high_but_no_matching_text_downgrades_to_review(monkeypatch):
    # 형태 high지만 내용 키워드가 안 보임 → 한 단계 강등(review/medium)
    _patch_classify(monkeypatch, category="statement", confidence="high")
    _patch_ocr(monkeypatch, "")  # OCR 비어있음(읽기 실패 등)
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_REVIEW
    assert res["confidence"] == "medium"


def test_deep_content_conflict_forces_review_low(monkeypatch):
    # 형태=contract라는데 내용은 명세서 강한 신호 → 충돌 → review/low
    _patch_classify(monkeypatch, category="contract", confidence="high")
    _patch_ocr(monkeypatch, STATEMENT_STRONG)
    res = assess_deep(b"img")
    assert res["keyword_check"]["conflict"] is True
    assert res["decision"] == DECISION_REVIEW
    assert res["confidence"] == "low"


def test_deep_multiple_docs_forces_review(monkeypatch):
    # 내용이 일치해도 한 장에 여러 서류면 보수적으로 review
    _patch_classify(monkeypatch, category="statement", confidence="high",
                    multiple_docs=True)
    _patch_ocr(monkeypatch, STATEMENT_TEXT)
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_REVIEW
    assert res["confidence"] == "low"


def test_deep_unreadable_forces_review(monkeypatch):
    _patch_classify(monkeypatch, category="statement", confidence="high",
                    readable=False)
    _patch_ocr(monkeypatch, STATEMENT_TEXT)
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_REVIEW
    assert res["confidence"] == "low"


def test_deep_medium_and_agree_is_auto_medium(monkeypatch):
    _patch_classify(monkeypatch, category="statement", confidence="medium")
    _patch_ocr(monkeypatch, STATEMENT_TEXT)
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_AUTO
    assert res["confidence"] == "medium"


def test_deep_irrelevant_short_circuits_without_ocr(monkeypatch):
    _patch_classify(monkeypatch, category="irrelevant", relevant=False, confidence="high")
    # OCR이 호출되면 실패하도록 심어, 무관 이미지에 비싼 OCR 안 도는지 확인
    def _boom(_cat):
        raise AssertionError("무관 이미지에 OCR을 호출하면 안 됨")
    monkeypatch.setattr(ei, "get_ocr", _boom)
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_REJECT
    assert res["raw_text"] == ""


# ── 순수 local mock(패치 없음): 정직하게 review/빈텍스트 ───────────

def test_deep_pure_local_mock_is_review_and_empty(monkeypatch):
    # classify=local 보류(other/low), OCR=MockOcr(빈 텍스트) → review/low, raw_text 비어있음
    res = assess_deep(b"img")
    assert res["decision"] == DECISION_REVIEW
    assert res["confidence"] == "low"
    assert res["raw_text"] == ""


# ── _decide 규칙 매트릭스 직접 검증 ──────────────────────────────

def test_decide_matrix():
    agree = {"agree": True, "category_score": 3, "best_category": "statement", "conflict": False}
    disagree = {"agree": False, "category_score": 0, "best_category": None, "conflict": False}
    conflict = {"conflict": True}
    clean = {"multiple_docs": False, "readable": True}

    assert _decide("high", agree, clean) == (DECISION_AUTO, "high")
    assert _decide("high", disagree, clean) == (DECISION_REVIEW, "medium")
    assert _decide("medium", agree, clean) == (DECISION_AUTO, "medium")
    assert _decide("medium", disagree, clean) == (DECISION_REVIEW, "low")
    assert _decide("low", agree, clean) == (DECISION_REVIEW, "low")
    # 충돌/품질은 신뢰도 무관하게 review/low
    assert _decide("high", conflict, clean) == (DECISION_REVIEW, "low")
    assert _decide("high", agree, {"multiple_docs": True, "readable": True}) == (DECISION_REVIEW, "low")
    assert _decide("high", agree, {"multiple_docs": False, "readable": False}) == (DECISION_REVIEW, "low")
