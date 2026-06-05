"""증거 — 메타데이터 등록(manual), 로컬 파일 업로드, AWS presign, OCR 추출."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Evidence
from ..schemas import PresignedUploadRequest
from ..services import jobs, ocr_service, s3
from ..services.storage import get_storage

router = APIRouter(prefix="/cases/{case_id}/evidences", tags=["evidences"])


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
    return "text"


@router.post("/manual")
def add_manual(case_id: str, payload: ManualEvidence, db: Session = Depends(get_db)):
    ev = Evidence(case_id=case_id, file_key="", file_name=payload.file_name,
                  file_type="text", category=payload.category, ocr_status="pending")
    db.add(ev); db.commit(); db.refresh(ev)
    return {"id": ev.id, "file_name": ev.file_name, "category": ev.category}


@router.post("/upload")
async def upload_file(case_id: str, category: str = Form(...), file: UploadFile = File(...),
                      db: Session = Depends(get_db)):
    """실제 파일 업로드 → storage 저장. 이후 /extract 로 OCR."""
    data = await file.read()
    key = f"cases/{case_id}/{file.filename}"
    get_storage().save(key, data)
    ev = Evidence(case_id=case_id, file_key=key, file_name=file.filename,
                  file_type=_guess_type(file.filename), category=category, ocr_status="pending")
    db.add(ev); db.commit(); db.refresh(ev)
    return {"id": ev.id, "file_name": ev.file_name, "category": ev.category, "file_key": key}


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
