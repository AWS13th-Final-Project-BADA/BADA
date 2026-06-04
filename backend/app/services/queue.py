"""SQS 전송 — 분석 작업을 워커로 비동기 전달.

로컬 모드에서는 SQS 미설정 → no-op. 분석은 동기 엔드포인트가 직접 실행한다.
"""
import json

from ..config import settings

_client = None


def _sqs():
    global _client
    if _client is None:
        import boto3  # 지연 임포트
        _client = boto3.client("sqs", region_name=settings.aws_region)
    return _client


def send_analysis_job(case_id: str) -> None:
    if not settings.sqs_queue_url:
        return  # 로컬: 큐 미설정이면 no-op
    _sqs().send_message(
        QueueUrl=settings.sqs_queue_url,
        MessageBody=json.dumps({"type": "analyze_case", "case_id": case_id}),
    )
