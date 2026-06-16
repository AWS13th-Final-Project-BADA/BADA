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


@router.post("/scan")
async def scan_evidences(case_id: str, files: list[UploadFile] = File(...)):
    """증거 수집 에이전트 [스캔] — 여러 이미지를 분류만으로 빠르게 훑어 후보를 추린다.

    단계적 비용 절감: 여기선 OCR을 돌리지 않는다(형태 분류만, 싸다).
    무관 이미지(셀카 등)는 rejected로 걸러지고, 관련 후보만 사용자에게 추천한다.

    반환:
      candidates: [{file_name, category, decision, confidence, alternative, reasons}]
      summary:    {auto_accept, needs_review, rejected}
      recommended:[관련 후보 file_name]   ← 사용자가 승인하면 /upload 로 등록(OCR은 그때 1회)

    ⚠️ 자동 등록하지 않는다(HITL). 비싼 OCR은 승인 후 /extract 단계에서만.
    """
    from ..services.intake_service import scan_images

    images: list[tuple[str, bytes]] = []
    for f in files:
        images.append((f.filename, await f.read()))
    return scan_images(images)


@router.post("/agent-upload")
async def agent_batch_upload(
    case_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """증거 수집 에이전트 [4단계] — 승인된 파일들을 일괄 업로드 + category=auto 로 등록.

    디바이스에서 1~3단계 필터를 거치고 사용자가 승인한 파일만 여기로 온다.
    category="auto"로 등록하면 기존 ocr_service가 자동분류+OCR+저장을 한 번에 처리한다.

    흐름: agent-upload → (DB 등록) → /extract 호출 → classify+OCR 1회 → 분석 준비 완료
    """
    results = []
    storage = get_storage()
    for f in files:
        data = await f.read()
        key = f"cases/{case_id}/{f.filename}"
        storage.save(key, data)
        ev = Evidence(
            case_id=case_id, file_key=key, file_name=f.filename,
            file_type=_guess_type(f.filename), category="auto", ocr_status="pending",
        )
        db.add(ev)
        results.append({"file_name": f.filename, "category": "auto", "file_key": key})
    db.commit()
    return {
        "uploaded": len(results),
        "files": results,
        "next_step": f"POST /cases/{case_id}/evidences/extract 를 호출하면 자동분류+OCR이 실행됩니다.",
    }


@router.post("/assess")
async def assess_evidence(case_id: str, file: UploadFile = File(...)):
    """증거 수집 에이전트 [정밀] — 1장을 분류+OCR+키워드 교차검증으로 확인(정확성 3종).

    스캔에서 추려진 파일을 정밀 확인하거나, 사용자가 애매한 1장을 확인할 때 사용.

    decision:
      - auto_accept   : 형태+내용 모두 강함
      - needs_review  : 애매/불일치 → 사용자 확인 필요
      - rejected      : 무관 이미지 → 제외

    ⚠️ 자동 등록하지 않는다. 승인 시 /upload 로 등록(HITL).
    """
    from ..services.intake_service import assess_one_deep

    data = await file.read()
    result = assess_one_deep(data)
    return {
        "file_name": file.filename,
        "suggested_category": result["category"],
        "decision": result["decision"],
        "confidence": result["confidence"],
        "reasons": result["reasons"],
        "alternative": (result.get("classify") or {}).get("alternative"),
    }


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


class RestoreRequest(BaseModel):
    category: str = "other"


@router.post("/{eid}/restore")
def restore_excluded(case_id: str, eid: str, payload: RestoreRequest = RestoreRequest(),
                     db: Session = Depends(get_db)):
    """자동분류로 '제외'된 자료를 사용자가 되살림(HITL 안전망). 재추출 대기로 전환."""
    row = ocr_service.restore_excluded(db, case_id, eid, payload.category)
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
