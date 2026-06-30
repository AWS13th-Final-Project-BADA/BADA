"""SQS Consumer — 큐에서 작업을 받아 종류별 handler로 디스패치하는 장기 실행 프로세스.

흐름:
    1. SQS long polling 으로 메시지 수신
    2. 본문(JSON) 파싱
    3. 종류 판별: "task"=="transcribe"  또는  "type"=="analyze_case"
    4. 해당 handler.handle(message) 호출
    5. 성공한 메시지만 SQS 에서 삭제
    6. 실패하면 삭제하지 않음 → 가시성 타임아웃 후 재수신(재시도),
       maxReceiveCount 초과 시 큐의 redrive 정책에 따라 DLQ 로 이동(인프라 설정)
    7. 멱등성: 각 handler 가 idempotent(재실행 안전)하게 구현되어 중복 수신에도 안전

consumer 는 "어떤 handler 로 넘길지"만 담당하고, 실제 처리 로직은 모른다.

실행:
    python consumer.py                 # SQS 폴링 루프 (운영)
    python consumer.py --once '<JSON>' # SQS 없이 메시지 1건 처리 (로컬 테스트/데모)

환경변수:
    SQS_QUEUE_URL     소비할 큐 URL (필수, 운영)
    AWS_REGION        AWS 리전 (기본: ap-northeast-2)
    SQS_WAIT_SECONDS  long polling 대기 초 (기본: 20)
    SQS_MAX_MESSAGES  1회 수신 최대 개수 (기본: 5)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time

# X-Ray는 daemon sidecar 준비 후 활성화. 현재는 비활성.
# from xray_setup import init_xray
# init_xray()

from handlers import analysis, transcription

logger = logging.getLogger("worker.consumer")

QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
WAIT_SECONDS = int(os.environ.get("SQS_WAIT_SECONDS", "20"))
MAX_MESSAGES = int(os.environ.get("SQS_MAX_MESSAGES", "5"))


def dispatch(message: dict) -> None:
    """메시지 종류를 보고 알맞은 handler 를 호출. 알 수 없는 종류면 예외."""
    kind = message.get("task") or message.get("type")
    if kind == "transcribe":
        transcription.handle(message)
    elif kind == "analyze_case":
        analysis.handle(message)
    elif kind == "extract_ocr":
        _handle_ocr(message)
    else:
        raise ValueError(f"unknown message kind: {kind!r}")


def _handle_ocr(message: dict) -> None:
    """OCR 추출 — 증거 파일에서 엔티티 추출 후 DB 저장."""
    from db import get_session
    from providers.ocr import get_ocr
    from app.models import Evidence
    import boto3
    import os

    case_id = message["case_id"]
    logger.info("extract_ocr 시작: case_id=%s", case_id)
    session = get_session()
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    bucket = os.environ.get("S3_BUCKET", "")

    try:
        evidences = session.query(Evidence).filter(
            Evidence.case_id == case_id,
            Evidence.file_type.in_(["image", "pdf"]),
            Evidence.ocr_status.in_(["pending", "processing"])
        ).all()

        for ev in evidences:
            try:
                ev.ocr_status = "processing"
                session.commit()

                # S3에서 파일 읽기
                if bucket and ev.file_key:
                    obj = s3.get_object(Bucket=bucket, Key=ev.file_key)
                    image_bytes = obj["Body"].read()
                else:
                    logger.warning("S3 bucket 또는 file_key 없음: evidence_id=%s", ev.id)
                    ev.ocr_status = "failed"
                    session.commit()
                    continue

                # OCR 실행
                ocr = get_ocr(ev.category or "other")
                result = ocr.extract(image_bytes, ev.category or "other")
                ev.extracted_entities = result.get("entities", result)
                ev.ocr_text = result.get("raw_text", "")
                ev.ocr_status = "done"
                session.commit()
            except Exception as e:
                ev.ocr_status = "failed"
                session.commit()
                logger.warning("OCR 실패: evidence_id=%s, error=%s", ev.id, e)

        logger.info("extract_ocr 완료: case_id=%s, 처리=%d건", case_id, len(evidences))
    finally:
        session.close()


def _sqs_client():
    import boto3  # 지연 임포트 — 로컬 테스트(--once)는 AWS 없이 동작
    return boto3.client("sqs", region_name=AWS_REGION)


def _process_message(sqs, msg: dict) -> None:
    """메시지 1건 처리. 성공 시 삭제, 실패 시 미삭제(재시도/DLQ)."""
    mid = msg.get("MessageId", "?")
    receipt = msg["ReceiptHandle"]

    try:
        body = json.loads(msg.get("Body", ""))
    except (ValueError, TypeError):
        # 파싱 불가능한 메시지는 영원히 실패하므로(poison pill) 삭제하여 무한 재시도 방지
        logger.error("잘못된 JSON 본문, 삭제: id=%s", mid)
        sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)
        return

    try:
        dispatch(body)
    except Exception:
        # 삭제하지 않음 → 가시성 타임아웃 후 재수신, 반복 실패 시 DLQ
        logger.exception("handler 실패(재시도 예정): id=%s body=%s", mid, body)
        return

    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)
    logger.info("처리 완료 및 삭제: id=%s", mid)


def run_forever() -> None:
    """SQS 폴링 루프 (운영 모드)."""
    if not QUEUE_URL:
        raise RuntimeError("SQS_QUEUE_URL 환경변수가 설정되지 않았습니다")
    sqs = _sqs_client()
    logger.info("consumer 시작: queue=%s region=%s", QUEUE_URL, AWS_REGION)
    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=MAX_MESSAGES,
                WaitTimeSeconds=WAIT_SECONDS,
                MessageAttributeNames=["All"],
            )
        except Exception:
            # 일시적 네트워크/SQS 오류 → 루프 죽지 않도록 잠시 쉬고 재시도
            logger.exception("receive_message 실패, 5초 후 재시도")
            time.sleep(5)
            continue

        messages = resp.get("Messages", [])
        if not messages:
            continue  # long polling 타임아웃(메시지 없음) → 다시 수신
        for msg in messages:
            _process_message(sqs, msg)


def run_once(payload: str) -> None:
    """SQS 없이 JSON 메시지 1건을 그대로 dispatch (로컬 테스트/데모)."""
    logger.info("로컬 테스트: 메시지 1건 처리")
    dispatch(json.loads(payload))
    logger.info("로컬 테스트 완료")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="BADA worker SQS consumer")
    parser.add_argument("--once", metavar="JSON", help="SQS 없이 메시지 1건 처리(로컬 테스트)")
    args = parser.parse_args()

    if args.once:
        run_once(args.once)
    else:
        run_forever()


if __name__ == "__main__":
    main()
