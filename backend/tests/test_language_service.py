from app.services.guardrail_service import build_disclaimer
from app.services.language_service import resolve_chat_language


def test_vietnamese_message_overrides_korean_ui_language():
    message = "Đơn khiếu nại thường cần viết những nội dung gì?"

    assert resolve_chat_language("ko", message) == "vi"
    assert resolve_chat_language("auto", message) == "vi"


def test_vietnamese_disclaimer_is_localized():
    disclaimer = build_disclaimer("vi")

    assert "đánh giá pháp lý" in disclaimer
