"""OCR 하이브리드 라우팅 + 엔진 스위치 + 집계 로직 테스트 (실제 API 호출 없이)."""
import providers.ocr as o
from providers.ocr import ClaudeVisionOcr, MockOcr, ParseurOcr, UpstageOcr, get_ocr
from services.extract import aggregate


def test_routing_local_is_mock():
    o.PROVIDER_MODE = "local"
    assert isinstance(get_ocr("statement"), MockOcr)
    assert isinstance(get_ocr("chat"), MockOcr)


def test_routing_aws_hybrid_default_upstage():
    o.PROVIDER_MODE = "aws"
    o.STRUCTURED_ENGINE = "upstage"
    try:
        assert isinstance(get_ocr("statement"), UpstageOcr)   # 정형 → Upstage
        assert isinstance(get_ocr("contract"), UpstageOcr)
        assert isinstance(get_ocr("chat"), ClaudeVisionOcr)   # 비정형 → Vision
        assert isinstance(get_ocr("other"), ClaudeVisionOcr)  # 애매 → Vision
    finally:
        o.PROVIDER_MODE = "local"


def test_routing_structured_engine_parseur():
    o.PROVIDER_MODE = "aws"
    o.STRUCTURED_ENGINE = "parseur"
    try:
        assert isinstance(get_ocr("statement"), ParseurOcr)   # 정형 → Parseur
        assert isinstance(get_ocr("chat"), ClaudeVisionOcr)   # 비정형은 그대로 Vision
    finally:
        o.PROVIDER_MODE = "local"
        o.STRUCTURED_ENGINE = "upstage"


def test_mock_returns_empty():
    o.PROVIDER_MODE = "local"
    assert get_ocr("statement").extract(b"x", "statement") == {"raw_text": "", "entities": {}}


def test_aggregate_merges_entities():
    evs = [
        {"category": "statement", "entities": {"hourly_wage": 10320, "hours": [174.0],
            "deductions": [{"name": "기숙사비", "amount": 250000}],
            "amounts": [{"label": "지급액", "value": 2300000}]}},
        {"category": "payment", "entities": {"amounts": [{"label": "입금", "value": 1900000}],
            "pay_date": "2026-05-01"}},
    ]
    agg = aggregate(evs)
    assert agg["agreed_hourly_wage"] == 10320
    assert agg["worked_hours"] == [174.0]
    assert agg["deductions"] == [{"name": "기숙사비", "amount": 250000}]
    assert agg["deposits"] == [{"date": "2026-05-01", "amount": 1900000}]
