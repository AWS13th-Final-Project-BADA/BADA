from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas_ai_chat import ChatMessageRequest, ChatMessageResponse
from ..services.ai_chat_orchestrator import run_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatMessageResponse)
async def chat_messages(request: Request, db: Session = Depends(get_db)):
    payload = await _read_chat_payload(request)
    return run_chat(payload, db)


async def _read_chat_payload(request: Request) -> ChatMessageRequest:
    data: dict[str, Any] = {}

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            raw = await request.json()
        except Exception:
            raw = {}
        if isinstance(raw, dict):
            data = raw
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        data = dict(form)

    if not data:
        data = dict(request.query_params)

    message = data.get("message") or data.get("text") or data.get("question")
    if not message or not str(message).strip():
        raise HTTPException(status_code=400, detail="message is required")

    # 사건 ID는 UUID 문자열. 미지정/빈값이면 None → 일반 상담(스펙).
    # (과거: int() 강제 → UUID가 들어오면 항상 1로 폴백되어 사건 컨텍스트가 무시됐음)
    case_id = data.get("case_id") or data.get("caseId")
    case_id = str(case_id) if case_id not in ("", None) else None

    session_id = data.get("session_id") or data.get("sessionId")
    if session_id in ("", None):
        session_id = None
    else:
        try:
            session_id = int(session_id)
        except (TypeError, ValueError):
            session_id = None

    return ChatMessageRequest(
        session_id=session_id,
        case_id=case_id,
        message=str(message).strip(),
        language=str(data.get("language") or data.get("lang") or "auto"),
    )
