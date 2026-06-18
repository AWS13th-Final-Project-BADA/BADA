from __future__ import annotations

import re
from typing import Tuple


BLOCKED_PATTERNS = [
    # Korean: asks for final legal judgment, guaranteed outcome, lawsuit/report command.
    r"불법\s*(이야|인가요|인가|입니까|맞나요|맞아)",
    r"위법\s*(이야|인가요|인가|입니까|맞나요|맞아)",
    r"법\s*(위반|어긴|어겼)",
    r"체불\s*(확정|맞지|맞나요|인가요|이죠)",
    r"미지급\s*(확정|맞지|맞나요|인가요|이죠)",
    r"무조건\s*(받|이기|신고)",
    r"반드시\s*(받|이기)",
    r"받을\s*수\s*있(어|나요|겠)",
    r"얼마(?:를)?\s*(받을|청구할)\s*수",
    r"바로\s*(신고|고소|소송)",
    r"소송\s*(해야|가능|할까|해도)",
    r"고소\s*(해야|가능|할까|해도)",
    r"신고\s*(해야|가능|할까|해도)",
    r"사업주.*(처벌|벌금|감옥|형사)",
    r"(법률|법적)\s*(조언|자문)\s*(해\s*줘|해주세요|부탁|가능)",
    r"(변호사|노무사)처럼\s*(판단|답변|조언)",
    # English.
    r"\bis\s+this\s+illegal\b",
    r"\bis\s+it\s+illegal\b",
    r"\bdoes\s+this\s+violate\s+the\s+law\b",
    r"\bdid\s+the\s+employer\s+break\s+the\s+law\b",
    r"\bis\s+this\s+unpaid\s+wages?\b",
    r"\bam\s+i\s+guaranteed\s+to\s+get\b",
    r"\bwill\s+i\s+definitely\s+receive\b",
    r"\bhow\s+much\s+can\s+i\s+(get|claim|receive)\b",
    r"\bshould\s+i\s+(sue|report|file\s+a\s+complaint)\b",
    r"\bcan\s+i\s+(sue|report|file\s+a\s+complaint)\b",
    r"\bpunish(?:ed|ment)?\b.*\bemployer\b",
    r"\blegal\s+advice\b",
    r"\badvise\s+me\s+legally\b",
    # Vietnamese.
    r"có\s+(bất\s+hợp\s+pháp|trái\s+pháp\s+luật)\s+không",
    r"có\s+vi\s+phạm\s+pháp\s+luật\s+không",
    r"chủ\s+(có\s+)?(vi\s+phạm|phạm\s+luật)\s+không",
    r"công\s+ty\s+(có\s+)?(vi\s+phạm|phạm\s+luật)\s+không",
    r"đây\s+có\s+phải\s+là\s+(tiền\s+lương\s+)?bị\s+nợ\s+không",
    r"tôi\s+có\s+chắc\s+chắn\s+nhận\s+được",
    r"chắc\s+chắn\s+(nhận|lấy)\s+được",
    r"tôi\s+có\s+thể\s+(kiện|tố\s+cáo|báo\s+cáo)",
    r"có\s+nên\s+(kiện|tố\s+cáo|báo\s+cáo)",
    r"phải\s+(kiện|tố\s+cáo|báo\s+cáo)\s+ngay",
    r"chủ.*(bị\s+phạt|bị\s+trừng\s+phạt|đi\s+tù)",
    r"tư\s+vấn\s+pháp\s+lý",
    r"lời\s+khuyên\s+pháp\s+lý",
]


REVIEW_PATTERNS = [
    # Korean: asks for possibility/review without demanding a final conclusion.
    r"상담\s*(가능|받아도|가도)",
    r"검토\s*해\s*줘",
    r"확인\s*해\s*줘",
    r"가능성",
    r"문제\s*될\s*수",
    r"자료가\s*충분",
    r"신고\s*전\s*준비",
    r"진정서.*(작성|준비)",
    # English.
    r"\bcan\s+you\s+review\b",
    r"\bdoes\s+this\s+look\s+like\b",
    r"\bis\s+my\s+evidence\s+enough\b",
    r"\bbefore\s+(consultation|reporting|filing)\b",
    r"\bprepare\s+(for|before)\b",
    r"\bcomplaint\s+form\b",
    # Vietnamese.
    r"chuẩn\s+bị\s+(trước|đi)\s+tư\s+vấn",
    r"tài\s+liệu\s+(có\s+)?đủ\s+không",
    r"kiểm\s+tra\s+giúp",
    r"xem\s+giúp",
    r"trước\s+khi\s+(tư\s+vấn|nộp\s+đơn)",
    r"đơn\s+khiếu\s+nại",
    r"nên\s+viết\s+gì",
]


def classify_legal_risk(message: str) -> Tuple[str, bool]:
    text = _normalize(message)

    if _matches_any(text, BLOCKED_PATTERNS):
        return "blocked", True

    if _matches_any(text, REVIEW_PATTERNS):
        return "review", False

    return "safe", False


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message.lower().strip())


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
