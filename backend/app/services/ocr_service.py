"""OCR 실행 서비스 — 업로드된 증거에 OCR → 엔티티 추출·저장·집계.

로컬: Mock(빈 결과). AWS: Claude Vision / Upstage 하이브리드.
성능: 'done'은 재OCR 안 함(캐싱). 보안: 카톡(chat/other)은 PII 마스킹(계좌·주민번호·전화).
자동 분류: category='auto'로 올라온 증거는 추출 전에 종류를 판단(분류)하고,
          무관하면 'excluded'(추출 skip), 관련이면 분류된 카테고리로 추출한다.
"""
from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Evidence
from .storage import get_storage

_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))

log = logging.getLogger("bada")


def _mask_chat(category: str, ocr_text: str, entities: dict):
    """카톡 등 비정형: 제3자 PII(계좌·주민번호·전화) 자동 마스킹(security.md)."""
    if category not in ("chat", "other"):
        return ocr_text, entities
    try:
        from security.pii import mask_pii  # worker
    except Exception:
        return ocr_text, entities
    ocr_text = mask_pii(ocr_text or "")
    for u in (entities.get("utterances") or []):
        if u.get("text"):
            u["text"] = mask_pii(u["text"])
    return ocr_text, entities


def _quality(category: str, ocr_status: str, entities: dict):
    if category in ("chat", "other") and ocr_status == "done":
        try:
            from rules.chat_evidence import assess_chat  # worker
            return assess_chat(entities or {})
        except Exception:
            return None
    return None


def _sanity(ocr_status: str, entities: dict):
    """타당성(모순) 경고 — 통상임금<기본급, 산식 불일치 등."""
    if ocr_status != "done":
        return []
    try:
        from rules.sanity import check_entities  # worker
        return check_entities(entities or {})
    except Exception:
        return []


def _confidence(ocr_status: str, entities: dict, cross: dict | None):
    """근거 기반 필드별 신뢰도(LLM 자기보고 X). cross=증거 간 일치 신호."""
    if ocr_status != "done":
        return None
    try:
        from rules.confidence import assess  # worker
        return assess(entities or {}, cross or {})
    except Exception:
        return None


def _cross_for_case(evs: list[Evidence]) -> dict:
    """증거 간 교차 일치 신호 — 같은 값이 2건 이상에서 일치/불일치하는지(근거 confidence용)."""
    hw = [(e.extracted_entities or {}).get("hourly_wage") for e in evs]
    hw = [x for x in hw if x]
    cross: dict = {}
    if len(hw) >= 2:
        cross["hourly_wage"] = "agree" if len(set(hw)) == 1 else "disagree"
    return cross


def _row(ev: Evidence, cross: dict | None = None):
    ents = ev.extracted_entities or {}
    return {
        "evidence_id": ev.id, "file_name": ev.file_name, "category": ev.category,
        "ocr_status": ev.ocr_status, "ocr_text": (ev.ocr_text or "")[:600],
        "entities": ents, "evidence_quality": _quality(ev.category, ev.ocr_status, ents),
        "sanity": _sanity(ev.ocr_status, ents),
        "confidence": _confidence(ev.ocr_status, ents, cross),
        "classify": ents.get("_classify"),   # 자동 분류 결과(있으면) — UI 표시용
        "error": None,
    }


def _eligible(ev: Evidence) -> bool:
    return ev.file_type in ("image", "pdf", "audio") and bool(ev.file_key)


def collect(db: Session, case_id: str) -> dict:
    """OCR을 돌리지 않고 현재 DB 상태로 rows+aggregate를 만든다(폴링용 스냅샷).

    status: 처리 대상 중 하나라도 pending/processing이면 'processing', 아니면 'done'.
    """
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    cross = _cross_for_case(evs)
    targets = [e for e in evs if _eligible(e)]
    rows = [_row(e, cross) for e in targets]
    from services.extract import aggregate  # worker
    agg = aggregate(rows)
    agg["evidences"] = rows
    pending = any(e.ocr_status in ("pending", "processing") for e in targets)
    agg["status"] = "processing" if pending else "done"
    return agg


def mark_processing(db: Session, case_id: str) -> None:
    """비동기 OCR 시작 전, 대상 중 아직 안 끝난(done/excluded 아님) 증거를 processing으로 표시."""
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    changed = False
    for ev in evs:
        if _eligible(ev) and ev.ocr_status not in ("done", "excluded"):
            ev.ocr_status = "processing"
            changed = True
    if changed:
        db.commit()


def update_entities(db: Session, case_id: str, eid: str, entities: dict) -> dict | None:
    """사용자가 OCR 값을 수정(HITL) → 저장. 수정본은 done으로 간주하고 행을 다시 계산."""
    ev = db.get(Evidence, eid)
    if not ev or ev.case_id != case_id:
        return None
    ev.extracted_entities = entities or {}
    ev.ocr_status = "done"
    db.commit()
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return _row(ev, _cross_for_case(evs))


def restore_excluded(db: Session, case_id: str, eid: str, category: str = "other") -> dict | None:
    """사용자가 '제외'된 자료를 되살림(HITL 안전망) → 지정 카테고리로 재추출 대기(pending)."""
    ev = db.get(Evidence, eid)
    if not ev or ev.case_id != case_id:
        return None
    ev.category = category
    ev.ocr_status = "pending"
    ev.ocr_text = None
    db.commit()
    return _row(ev, _cross_for_case(db.query(Evidence).filter(Evidence.case_id == case_id).all()))


def run_ocr_on_case(db: Session, case_id: str, force: bool = False) -> dict:
    from providers.ocr import get_ocr        # worker
    from providers.classify import classify  # worker (자동 분류)
    from services.extract import aggregate   # worker

    storage = get_storage()
    evs = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    collected: list = []

    # OCR 대상만 선별(이미지/PDF · 캐시된 done/excluded 제외) → 즉시 processing 표시
    targets = [ev for ev in evs
               if ev.file_type in ("image", "pdf") and ev.file_key
               and (force or ev.ocr_status not in ("done", "excluded"))]
    for ev in targets:
        ev.ocr_status = "processing"

    # 느린 부분(파일읽기 + 분류 + Bedrock OCR)만 스레드로 동시 실행 — ORM/DB는 손대지 않는다.
    def _extract_one(args):
        eid, category, file_key = args
        try:
            data = storage.read(file_key)
            cls = None
            # category='auto' → 먼저 분류. 무관하면 추출 안 함(제외).
            if category == "auto":
                cls = classify(data)
                if not cls.get("relevant", True):
                    return eid, {"excluded": True, "cls": cls,
                                 "category": cls.get("category", "irrelevant"),
                                 "text": None, "ents": None, "err": None}
                category = cls.get("category") or "other"
            out = get_ocr(category).extract(data, category)
            text, ents = _mask_chat(category, out.get("raw_text", ""), out.get("entities", {}))
            if cls:
                ents = dict(ents or {})
                ents["_classify"] = cls   # 분류 근거·신뢰도 보존(UI 표시·HITL용)
            return eid, {"excluded": False, "cls": cls, "category": category,
                         "text": text, "ents": ents, "err": None}
        except Exception as e:  # noqa: BLE001 (사유는 메인스레드에서 기록)
            return eid, {"excluded": False, "cls": None, "category": category,
                         "text": None, "ents": None, "err": str(e)[:300]}

    results: dict = {}
    job_args = [(ev.id, ev.category, ev.file_key) for ev in targets]
    if job_args:
        with ThreadPoolExecutor(max_workers=min(len(job_args), 4), thread_name_prefix="ocr-ex") as ex:
            for eid, res in ex.map(_extract_one, job_args):
                results[eid] = res

    # DB 반영은 메인 스레드에서만 (SQLAlchemy 세션 thread-safe 보장)
    for ev in evs:
        if ev.file_type not in ("image", "pdf") or not ev.file_key:
            continue
        if ev.id not in results:   # 캐시된 done/excluded
            collected.append(ev)
            continue
        res = results[ev.id]
        if res.get("excluded"):
            # 무관 자료 → 제외(추출 안 함). 사용자가 '되살리기' 가능(restore_excluded).
            ev.category = res["category"]
            ev.ocr_status = "excluded"
            ev.extracted_entities = {"_classify": res["cls"]}
            reason = (res["cls"] or {}).get("reason", "임금체불과 무관한 자료로 보임")
            ev.ocr_text = f"[제외] {reason}"
            collected.append((ev, None))
        elif res["err"] is None:
            if res.get("category"):
                ev.category = res["category"]   # 분류 결과로 카테고리 확정
            ev.ocr_text = res["text"]
            ev.extracted_entities = res["ents"]
            ev.ocr_status = "done"
            collected.append((ev, None))
        else:
            log.warning("OCR failed for evidence %s: %s", ev.id, res["err"])
            ev.ocr_status = "failed"
            ev.extracted_entities = {}
            ev.ocr_text = f"[OCR 실패] {res['err']}"   # 폴링(GET) 때도 사유 노출
            collected.append((ev, res["err"]))

    db.commit()
    # 모든 추출이 끝난 뒤 교차 신호 계산 → 행 생성(근거 confidence 반영)
    cross = _cross_for_case(evs)
    rows = []
    for item in collected:
        if isinstance(item, tuple):
            ev, err = item
            r = _row(ev, cross)
            if err:
                r["error"] = err
            rows.append(r)
        else:
            rows.append(_row(item, cross))

    agg = aggregate(rows)
    agg["evidences"] = rows
    return agg
