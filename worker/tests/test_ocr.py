"""OCR 하이브리드 라우팅 + 집계 로직 테스트 (실제 API 호출 없이)."""
import providers.ocr as o
from providers.ocr import ClaudeVisionOcr, MockOcr, UpstageOcr, get_ocr
from services.extract import aggregate


def test_routing_local_is_mock():
    o.PROVIDER_MODE = "local"
    assert isinstance(get_ocr("statement"), MockOcr)
    assert isinstance(get_ocr("chat"), MockOcr)


def test_routing_aws_hybrid():
    o.PROVIDER_MODE = "aws"
    try:
        assert isinstance(get_ocr("statement"), UpstageOcr)   # 정형
        assert isinstance(get_ocr("contract"), UpstageOcr)
        assert isinstance(get_ocr("schedule"), UpstageOcr)
        assert isinstance(get_ocr("chat"), ClaudeVisionOcr)   # 비정형
        assert isinstance(get_ocr("other"), ClaudeVisionOcr)  # 애매 → 안전 기본값
    finally:
        o.PROVIDER_MODE = "local"


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
