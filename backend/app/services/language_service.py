from __future__ import annotations

import re


SUPPORTED_RESPONSE_LANGUAGES = {"ko", "en", "vi", "zh", "ja", "th", "id", "ne", "uz", "km", "mn", "my"}


def resolve_chat_language(requested_language: str | None, message: str) -> str:
    """Choose the answer language for chat.

    The frontend may send the UI language, but the chatbot should usually reply
    in the language the user actually typed.
    """
    detected = detect_message_language(message)
    requested = normalize_language_code(requested_language)

    if requested in ("", "auto"):
        return detected

    if requested == "ko" and detected != "ko":
        return detected

    if requested in SUPPORTED_RESPONSE_LANGUAGES:
        return requested

    return detected


def normalize_language_code(language: str | None) -> str:
    value = (language or "").strip().lower().replace("_", "-")
    if not value:
        return "auto"
    return value.split("-", 1)[0]


def detect_message_language(message: str) -> str:
    text = message.strip()
    if not text:
        return "ko"

    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[ぁ-ゟ゠-ヿ]", text):
        return "ja"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u0e00-\u0e7f]", text):
        return "th"
    if re.search(r"[\u1780-\u17ff]", text):
        return "km"
    if re.search(r"[\u0400-\u04ff]", text):
        return "mn"
    if re.search(r"[\u1000-\u109f]", text):
        return "my"

    lowered = text.lower()
    if re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", lowered):
        return "vi"

    vietnamese_markers = {
        "xin",
        "chào",
        "tôi",
        "cần",
        "nên",
        "ghi",
        "viết",
        "đơn",
        "khiếu",
        "nại",
        "lương",
        "công",
        "ty",
        "hợp",
        "đồng",
        "lao",
        "động",
    }
    tokens = set(re.findall(r"[a-zA-ZÀ-ỹ]+", lowered))
    if len(tokens & vietnamese_markers) >= 2:
        return "vi"

    return "en"


def language_name(language: str) -> str:
    names = {
        "ko": "Korean",
        "en": "English",
        "vi": "Vietnamese",
        "zh": "Chinese",
        "ja": "Japanese",
        "th": "Thai",
        "id": "Indonesian",
        "ne": "Nepali",
        "uz": "Uzbek",
        "km": "Khmer",
        "mn": "Mongolian",
        "my": "Burmese",
    }
    return names.get(normalize_language_code(language), "the user's language")
