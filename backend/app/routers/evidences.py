"""증거 — 메타데이터 등록(manual), 로컬 파일 업로드(storage), AWS presign."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Evidence
from ..schemas import PresignedUploadRequest
from ..services import s3
from ..services.storage import get_storage

router = APIRouter(prefix="/cases/{case_id}/evidences", tags=["evidences"])


class ManualEvidence(BaseModel):
    file_name: str
    category: str


def _guess_type(name: str) -> str:
    n = (name or "").lower()
    if n.endswith(".pdf"):
        return "pdf"
    if n.endswith((".png", ".jpg", ".jpeg", ".webp", ".heic")):
        return "image"
    return "text"


@router.post("/manual")
def add_manual(case_id: str, payload: ManualEvidence, db: Session = Depends(get_db)):
    """파일 없이 분류만 등록(누락 체크용)."""
    ev = Evidence(case_id=case_id, file_key="", file_name=payload.file_name,
                  file_type="text", category=payload.category, ocr_status="pending")
    db.add(ev); db.commit(); db.refresh(ev)
    return {"id": ev.id, "file_name": ev.file_name, "category": ev.category}


@router.post("/upload")
async def upload_file(case_id: str, category: str = Form(...), file: UploadFile = File(...),
                      db: Session = Depends(get_db)):
    """실제 파일 업로드 → storage 저장(로컬 FS 또는 S3). OCR 담당이 이 파일을 읽는다."""
    data = await file.read()
    key = f"cases/{case_id}/{file.filename}"
    get_storage().save(key, data)
    ev = Evidence(case_id=case_id, file_key=key, file_name=file.filename,
                  file_type=_guess_type(file.filename), category=category, ocr_status="pending")
    db.add(ev); db.commit(); db.refresh(ev)
    return {"id": ev.id, "file_name": ev.file_name, "category": ev.category, "file_key": key}


@router.post("")
def request_upload(case_id: str, payload: PresignedUploadRequest, db: Session = Depends(get_db)):
    """AWS presign(버킷 설정 시)."""
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
