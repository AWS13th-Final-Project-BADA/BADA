"""분석 handler — analyze_case 메시지 처리 (2단계: DB 직접 접근).

메시지 형식:
    {"type": "analyze_case", "case_id": "..."}

DB에서 Case + Evidence를 조회하고, pipeline.process_case()로 분석한 뒤 결과를 직접 저장한다.
멱등성: 기존 AnalysisResult를 삭제 후 재생성하므로 중복 수신에 안전하다.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

# Backend models 접근을 위해 path 추가
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from db import get_session  # noqa: E402
from pipeline import process_case  # noqa: E402
from services.extract import aggregate  # noqa: E402

logger = logging.getLogger(__name__)


def _dt(s):
    """ISO 문자열 → datetime 변환. 실패 시 None."""
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def _run_ocr_parallel(session, evidences) -> None:
    """OCR 미완료 증거를 병렬로 처리 (분석 전 단계)."""
    import os
    import boto3
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from providers.ocr import get_ocr

    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    bucket = os.environ.get("S3_BUCKET", "")

    # 전부 processing 표시
    for ev in evidences:
        ev.ocr_status = "processing"
    session.commit()

    def _ocr_one(ev_id, file_key, category):
        try:
            if not bucket or not file_key:
                return ev_id, None, None, "S3 bucket 또는 file_key 없음"
            obj = s3.get_object(Bucket=bucket, Key=file_key)
            image_bytes = obj["Body"].read()
            ocr = get_ocr(category or "other")
            result = ocr.extract(image_bytes, category or "other")
            return ev_id, result.get("raw_text", ""), result.get("entities", result), None
        except Exception as e:
            return ev_id, None, None, str(e)

    max_workers = min(len(evidences), 50)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ocr-analysis") as executor:
        futures = {
            executor.submit(_ocr_one, ev.id, ev.file_key, ev.category): ev.id
            for ev in evidences
        }
        for future in as_completed(futures):
            ev_id, raw_text, entities, error = future.result()
            results[ev_id] = (raw_text, entities, error)

    # DB 반영
    for ev in evidences:
        res = results.get(ev.id)
        if not res:
            continue
        raw_text, entities, error = res
        if error:
            ev.ocr_status = "failed"
            logger.warning("OCR 실패 (분석 전): evidence_id=%s, error=%s", ev.id, error)
        else:
            ev.extracted_entities = entities
            ev.ocr_text = raw_text
            ev.ocr_status = "done"
    session.commit()
    logger.info("OCR 병렬 처리 완료: %d건 중 %d건 성공",
                len(evidences), sum(1 for r in results.values() if r[2] is None))


def _extract_audio_entities(session, evidences) -> None:
    """전사 완료된 음성 증거에서 entities를 구조화 (텍스트 → Claude Text)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from providers.ocr import _structure_text

    def _structure_one(ev_id, ocr_text, category):
        try:
            result = _structure_text(ocr_text, category or "audio")
            return ev_id, result.get("entities", {}), None
        except Exception as e:
            return ev_id, None, str(e)

    max_workers = min(len(evidences), 50)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="audio-ent") as executor:
        futures = {
            executor.submit(_structure_one, ev.id, ev.ocr_text, ev.category): ev.id
            for ev in evidences
        }
        for future in as_completed(futures):
            ev_id, entities, error = future.result()
            results[ev_id] = (entities, error)

    for ev in evidences:
        res = results.get(ev.id)
        if not res:
            continue
        entities, error = res
        if error:
            logger.warning("음성 entities 구조화 실패: evidence_id=%s, error=%s", ev.id, error)
            ev.extracted_entities = {}
        else:
            ev.extracted_entities = entities
    session.commit()
    logger.info("음성 entities 구조화 완료: %d건 중 %d건 성공",
                len(evidences), sum(1 for r in results.values() if r[1] is None))


def handle(message: dict) -> None:
    """analyze_case 메시지 처리. 실패 시 예외 → consumer가 재시도/DLQ."""
    case_id = message.get("case_id")
    if not case_id:
        raise ValueError("analyze_case: 'case_id' is required")

    lang = message.get("lang", "ko")
    logger.info("analyze_case 시작 (2단계 DB 직접): case_id=%s, lang=%s", case_id, lang)

    session = get_session()
    try:
        _run(session, case_id, lang=lang)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    logger.info("analyze_case 완료: case_id=%s", case_id)


def _run(session, case_id: str, lang: str = "ko") -> None:
    from app.models import AnalysisResult, Case, Evidence, TimelineEvent, TranslationPair

    case = session.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case not found: {case_id}")

    evs = session.query(Evidence).filter(Evidence.case_id == case_id).all()

    # --- OCR 미완료 증거가 있으면 먼저 병렬 처리 ---
    pending_ocr = [e for e in evs
                   if e.file_type in ("image", "pdf")
                   and e.ocr_status in ("pending", "processing")]
    if pending_ocr:
        logger.info("OCR 미완료 %d건 병렬 처리 시작: case_id=%s", len(pending_ocr), case_id)
        _run_ocr_parallel(session, pending_ocr)
        # DB 갱신 후 다시 조회
        session.expire_all()
        evs = session.query(Evidence).filter(Evidence.case_id == case_id).all()

    # --- 음성 전사 완료 + entities 미추출 → 텍스트 기반 구조화 ---
    audio_need_entities = [e for e in evs
                           if e.file_type == "audio"
                           and e.ocr_status == "done"
                           and e.ocr_text
                           and not e.extracted_entities]
    if audio_need_entities:
        logger.info("음성 entities 구조화 %d건 시작: case_id=%s", len(audio_need_entities), case_id)
        _extract_audio_entities(session, audio_need_entities)
        session.expire_all()
        evs = session.query(Evidence).filter(Evidence.case_id == case_id).all()

    present = {e.category for e in evs}

    # OCR 추출값 집계
    collected = [{"category": e.category, "entities": e.extracted_entities or {}}
                 for e in evs if e.extracted_entities]
    ocr = aggregate(collected)

    # 카톡 발화
    chat_utts = []
    for e in evs:
        if e.category in ("chat", "other") and e.extracted_entities:
            ents = e.extracted_entities
            date = (ents.get("dates") or [None])[0]
            for u in ents.get("utterances", []) or []:
                chat_utts.append({
                    "date": date, "speaker": u.get("speaker"), "text": u.get("text"),
                    "kind": u.get("kind"), "confidence": u.get("confidence", "low"),
                    "source_evidence_id": e.id,
                })

    # GPS 로그 조회
    from app.models import GpsLog, Workplace
    gps_logs_db = session.query(GpsLog).filter(GpsLog.case_id == case_id).all()
    workplace = session.query(Workplace).filter(Workplace.case_id == case_id).first()

    gps_logs = [
        {"ts": g.ts, "lat": float(g.lat), "lng": float(g.lng),
         "is_mocked": g.is_mocked, "is_delayed_upload": g.is_delayed_upload}
        for g in gps_logs_db
    ]
    wp = {"lat": float(workplace.center_lat), "lng": float(workplace.center_lng),
          "radius_m": workplace.radius_m} if workplace else None

    # 카톡 도착성 발화에서 chat_arrivals 추출 (GPS 교차검증용)
    chat_arrivals = []
    for u in chat_utts:
        if u.get("kind") in ("arrival", "지급약속", "근무지시") and u.get("date"):
            dt = _dt(u["date"]) if isinstance(u["date"], str) else u["date"]
            if dt:
                chat_arrivals.append(dt)

    ctx = {
        "agreed_hourly_wage": case.agreed_hourly_wage or ocr.get("agreed_hourly_wage"),
        "worked_hours": ocr.get("worked_hours") or [],
        "deposits": ocr.get("deposit_amounts") or [],
        "deposit_events": ocr.get("deposits") or [],
        "raw_deductions": ocr.get("deductions") or [],
        "present_categories": present,
        "evidence_entities": collected,
        "chat_utterances": chat_utts,
        "gps_logs": gps_logs,
        "workplace": wp,
        "chat_arrivals": chat_arrivals,
        "work_start_date": str(case.work_start_date) if case.work_start_date else None,
        "workplace_name": case.workplace_name or ocr.get("workplace_name"),
        "target_lang": lang,
    }

    result = process_case(case_id, ctx)

    # 기존 결과 삭제 (멱등성)
    session.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).delete()
    session.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete()
    session.query(TranslationPair).filter(TranslationPair.case_id == case_id).delete()

    # 결과 저장
    ar = AnalysisResult(
        case_id=case_id,
        total_expected_wage=result.get("total_expected_wage"),
        total_received_wage=result.get("total_received_wage"),
        suspected_unpaid=result.get("suspected_unpaid"),
        deduction_items=result.get("deduction_items"),
        calculation_detail=result.get("calculation_detail"),
        timeline_summary=result.get("timeline_summary"),
        missing_evidences=result.get("missing_evidences"),
    )
    session.add(ar)

    # 타임라인 이벤트 저장
    for ev in result.get("timeline", []):
        te = TimelineEvent(
            case_id=case_id,
            event_type=ev.get("type", "unknown"),
            title=ev.get("title", ""),
            description=ev.get("description", ""),
            description_translated=ev.get("description_translated"),
            event_date=_dt(ev.get("date")),
            confidence=ev.get("confidence", "medium"),
            source="ai",
            source_evidence_id=ev.get("source_evidence_id"),
        )
        session.add(te)

    # 번역 대조표 저장
    for tp in result.get("translation_pairs", []):
        session.add(TranslationPair(
            case_id=case_id,
            source_text=tp.get("source", ""),
            translated_text=tp.get("translated", ""),
            evidence_type=tp.get("evidence_type"),
            related_issue=tp.get("related_issue"),
            source_evidence_id=tp.get("source_evidence_id"),
        ))

    # 사건 상태 업데이트
    case.status = "completed"
    session.commit()

    # PDF Evidence Pack 생성 (실패해도 분석 자체는 성공 처리)
    try:
        from services.pdf_generator import generate_evidence_pack
        case_info = {
            "workplace_name": case.workplace_name,
            "employer_name": case.employer_name,
            "work_start_date": str(case.work_start_date) if case.work_start_date else None,
            "work_end_date": str(case.work_end_date) if case.work_end_date else None,
        }
        s3_key = generate_evidence_pack(case_id, result, case_info, lang=lang)
        ar.pdf_ko_s3_key = s3_key
        session.commit()
        logger.info("PDF 생성 완료: case_id=%s, key=%s", case_id, s3_key)
    except Exception:
        logger.exception("PDF 생성 실패 (분석 결과는 저장됨): case_id=%s", case_id)
