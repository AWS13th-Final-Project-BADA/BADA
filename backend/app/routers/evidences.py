"""증거 — 메타데이터 등록(manual), 로컬 파일 업로드, AWS presign, OCR 추출."""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Evidence
from ..schemas import PresignedUploadRequest
from ..services import jobs, ocr_service, s3
from ..services.storage import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases/{case_id}/evidences", tags=["evidences"])

# ---------------------------------------------------------------------------
# Audio upload constants
# ---------------------------------------------------------------------------

AUDIO_EXTENSIONS = {"mp3", "mp4", "wav", "flac", "ogg", "amr", "webm"}
SUPPORTED_LANGUAGE_CODES = {"ko-KR", "vi-VN", "en-US", "th-TH", "ja-JP", "id-ID", "km-KH", "ne-NP"}
MAX_AUDIO_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


class ManualEvidence(BaseModel):
    file_name: str
    category: str


class EntitiesUpdate(BaseModel):
    entities: dict


def _guess_type(name: str) -> str:
    n = (name or "").lower()
    if n.endswith(".pdf"):
        return "pdf"
    if n.endswith((".png", ".jpg", ".jpeg", ".webp", ".heic")):
        return "image"
    # Audio extensions
    ext = n.rsplit(".", 1)[-1] if "." in n else ""
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "text"


@router.post("/manual")
def add_manual(case_id: str, payload: ManualEvidence, db: Session = Depends(get_db)):
    ev = Evidence(case_id=case_id, file_key="", file_name=payload.file_name,
                  file_type="text", category=payload.category, ocr_status="pending")
    db.add(ev); db.commit(); db.refresh(ev)
    return {"id": ev.id, "file_name": ev.file_name, "category": ev.category}


@router.post("/upload")
async def upload_file(case_id: str, category: str = Form(...), file: UploadFile = File(...),
                      language_code: Optional[str] = Form(None),
                      db: Session = Depends(get_db)):
    """실제 파일 업로드 → storage 저장. 오디오 파일은 전사 처리도 수행."""
    from fastapi import BackgroundTasks
    from fastapi.responses import JSONResponse
    import threading

    # Determine file type from extension
    file_type = _guess_type(file.filename)

    # --- Audio-specific validations ---
    if file_type == "audio":
        # Validate language_code if provided
        if language_code is not None and language_code not in SUPPORTED_LANGUAGE_CODES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported language_code '{language_code}'. "
                       f"Supported: {sorted(SUPPORTED_LANGUAGE_CODES)}",
            )
    else:
        # For non-audio files: validate extension is one we support (image/pdf/text)
        ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
        supported_non_audio = {"pdf", "png", "jpg", "jpeg", "webp", "heic"}
        # We allow any non-audio file through as "text" — existing behavior preserved.

    # Read file data
    data = await file.read()

    # --- File size validation for audio ---
    if file_type == "audio" and len(data) > MAX_AUDIO_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file exceeds maximum size of 200MB. "
                   f"Received: {len(data) / (1024 * 1024):.1f}MB",
        )

    # Store file
    key = f"cases/{case_id}/{file.filename}"
    get_storage().save(key, data)

    # Create Evidence record
    ev = Evidence(
        case_id=case_id,
        file_key=key,
        file_name=file.filename,
        file_type=file_type,
        category=category,
        ocr_status="pending",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # --- Audio: trigger transcription (non-blocking) ---
    if file_type == "audio":
        ev.ocr_status = "processing"
        db.commit()
        if settings.sqs_queue_url:
            _publish_transcription_message(ev, case_id, key, language_code)
        else:
            # Background thread for local transcription (non-blocking)
            _ev_id = ev.id
            _case_id = case_id
            _key = key
            _lang = language_code
            def _bg_transcribe():
                from ..db import SessionLocal
                _db = SessionLocal()
                try:
                    _ev = _db.get(Evidence, _ev_id)
                    if _ev:
                        _run_local_transcription(_db, _ev, _key, _lang)
                finally:
                    _db.close()
            threading.Thread(target=_bg_transcribe, daemon=True).start()

    return {"id": ev.id, "file_name": ev.file_name, "category": ev.category, "file_key": key}


def _publish_transcription_message(ev: Evidence, case_id: str, s3_key: str, language_code: str | None) -> None:
    """Publish a transcription task message to SQS (AWS mode)."""
    import json
    import boto3

    message = {
        "task": "transcribe",
        "evidence_id": ev.id,
        "case_id": case_id,
        "s3_key": s3_key,
        "language_code": language_code or "ko-KR",
    }
    client = boto3.client("sqs", region_name=settings.aws_region)
    client.send_message(QueueUrl=settings.sqs_queue_url, MessageBody=json.dumps(message))
    logger.info("Published transcription message for evidence %s", ev.id)


def _run_local_transcription(db: Session, ev: Evidence, s3_key: str, language_code: str | None) -> None:
    """Run transcription in background (separate DB session)."""
    import sys
    import json
    import urllib.request
    from pathlib import Path

    worker_dir = Path(__file__).resolve().parents[3] / "worker"
    if str(worker_dir) not in sys.path:
        sys.path.insert(0, str(worker_dir))

    import boto3

    # Build S3 URI
    s3_uri = f"s3://{settings.s3_bucket}/{s3_key}"
    job_name = f"bada-{ev.case_id[:8]}-{ev.id[:8]}-{int(time.time())}"
    lang = language_code or "ko-KR"

    try:
        client = boto3.client("transcribe", region_name=settings.aws_region)

        # Start job
        client.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode=lang,
            Media={"MediaFileUri": s3_uri},
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 5},
        )
        logger.info("Transcription job started: %s (lang=%s)", job_name, lang)

        # Poll (5s interval, 10min timeout)
        elapsed = 0
        while elapsed < 600:
            time.sleep(5)
            elapsed += 5
            resp = client.get_transcription_job(TranscriptionJobName=job_name)
            status = resp["TranscriptionJob"]["TranscriptionJobStatus"]

            if status == "COMPLETED":
                uri = resp["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                with urllib.request.urlopen(uri) as r:
                    result_json = json.loads(r.read().decode("utf-8"))

                # Parse transcript
                transcripts = result_json.get("results", {}).get("transcripts", [])
                text = transcripts[0]["transcript"] if transcripts else ""

                ev.ocr_text = text
                ev.ocr_status = "done"
                logger.info("Transcription done: %s (%d chars)", job_name, len(text))
                db.commit()
                return

            if status == "FAILED":
                reason = resp["TranscriptionJob"].get("FailureReason", "unknown")
                ev.ocr_status = "failed"
                logger.error("Transcription failed: %s reason=%s", job_name, reason)
                db.commit()
                return

        # Timeout
        ev.ocr_status = "failed"
        logger.error("Transcription timeout: %s", job_name)
        db.commit()

    except Exception as e:
        ev.ocr_status = "failed"
        logger.error("Transcription error for %s: %s", ev.id, e)
        db.commit()


@router.post("/extract")
def extract(case_id: str, wait: bool = False, db: Session = Depends(get_db)):
    """업로드된 증거 파일에 OCR 실행 → 엔티티 추출·저장.

    기본(비동기): 대상 증거를 'processing'으로 표시하고 백그라운드로 OCR을 돌린 뒤
                 즉시 현재 상태 스냅샷을 반환한다(논블로킹). 프론트는 GET으로 폴링.
    wait=true(동기): OCR을 끝까지 돌리고 결과를 반환(테스트·간단 케이스용).

    로컬(목)에서는 빈 결과(키 필요). AWS 모드에서 실제 추출. 결과는 HITL 검토 후 분석에 사용.
    """
    if wait:
        return ocr_service.run_ocr_on_case(db, case_id)
    ocr_service.mark_processing(db, case_id)
    jobs.submit_ocr(case_id)
    return ocr_service.collect(db, case_id)


@router.get("/extract")
def extract_status(case_id: str, db: Session = Depends(get_db)):
    """현재 OCR 진행 상태 스냅샷(폴링용). status: processing | done."""
    return ocr_service.collect(db, case_id)


@router.patch("/{eid}/entities")
def update_entities(case_id: str, eid: str, payload: EntitiesUpdate, db: Session = Depends(get_db)):
    """사용자가 수정한 OCR 엔티티 저장(HITL). 수정본은 done으로 간주, 갱신된 행 반환."""
    row = ocr_service.update_entities(db, case_id, eid, payload.entities)
    if row is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return row


@router.post("")
def request_upload(case_id: str, payload: PresignedUploadRequest, db: Session = Depends(get_db)):
    file_key = f"cases/{case_id}/{payload.file_name}"
    url = s3.presign_put(file_key, payload.file_type) if settings.s3_bucket else None
    ev = Evidence(case_id=case_id, file_key=file_key, file_name=payload.file_name,
                  file_type=payload.file_type, category=payload.category)
    db.add(ev); db.commit(); db.refresh(ev)
    return {"evidence_id": ev.id, "upload_url": url, "file_key": file_key}


@router.get("")
def list_evidences(case_id: str, db: Session = Depends(get_db)):
    rows = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return [{"id": e.id, "file_name": e.file_name, "category": e.category, "ocr_status": e.ocr_status} for e in rows]


@router.delete("/{eid}")
def delete_evidence(case_id: str, eid: str, db: Session = Depends(get_db)):
    ev = db.get(Evidence, eid)
    if ev:
        db.delete(ev); db.commit()
    return {"deleted": True}
