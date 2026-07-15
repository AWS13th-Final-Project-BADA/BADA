"""Worker Prometheus 메트릭 — 비즈니스 로직 계측 + HTTP 서버.

consumer.py 시작 시 `start_metrics_server()`를 호출하면
별도 스레드에서 :9090/metrics 를 서빙한다.
Prometheus가 Worker task의 9090 포트를 스크레이핑.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from threading import Thread

from prometheus_client import (
    Counter, Histogram, Gauge, start_http_server,
)

# ── SQS 처리 ──
SQS_MESSAGES = Counter(
    "worker_sqs_messages_total",
    "SQS 메시지 처리 횟수",
    ["task_type", "status"],  # status: success / failed
)
SQS_PROCESSING_TIME = Histogram(
    "worker_sqs_processing_seconds",
    "SQS 메시지 1건 처리 소요시간",
    ["task_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

# ── Bedrock (OCR + 분석 LLM) ──
BEDROCK_CALLS = Counter(
    "worker_bedrock_calls_total",
    "Bedrock API 호출 횟수",
    ["purpose", "status"],  # purpose: ocr / analysis / audio_entities, status: success / failed
)
BEDROCK_LATENCY = Histogram(
    "worker_bedrock_latency_seconds",
    "Bedrock API 호출 소요시간",
    ["purpose"],
    buckets=[1, 2, 5, 10, 20, 30, 60],
)

# ── OCR ──
OCR_PROCESSED = Counter(
    "worker_ocr_processed_total",
    "OCR 처리 건수",
    ["category", "status"],  # status: success / failed
)
OCR_BATCH_SIZE = Histogram(
    "worker_ocr_batch_size",
    "1회 OCR 병렬 배치 건수",
    buckets=[1, 2, 5, 10, 20, 50],
)

# ── STT (Transcribe) ──
STT_PROCESSED = Counter(
    "worker_stt_processed_total",
    "음성 전사(STT) 처리 건수",
    ["status"],
)
STT_LATENCY = Histogram(
    "worker_stt_latency_seconds",
    "음성 전사 소요시간",
    buckets=[5, 10, 15, 20, 30, 60],
)

# ── PDF 생성 ──
PDF_GENERATED = Counter(
    "worker_pdf_generated_total",
    "PDF Evidence Pack 생성 건수",
    ["status"],
)
PDF_LATENCY = Histogram(
    "worker_pdf_latency_seconds",
    "PDF 생성 소요시간",
    buckets=[5, 10, 15, 20, 30, 60, 120],
)

# ── 분석 파이프라인 전체 ──
ANALYSIS_TOTAL = Counter(
    "worker_analysis_total",
    "분석 파이프라인 실행 건수",
    ["status"],
)
ANALYSIS_DURATION = Histogram(
    "worker_analysis_duration_seconds",
    "분석 파이프라인 전체 소요시간 (OCR+LLM+PDF)",
    buckets=[10, 30, 60, 90, 120, 180, 300],
)

# ── Worker 상태 ──
WORKER_IDLE = Gauge(
    "worker_idle",
    "Worker가 메시지 대기 중이면 1, 처리 중이면 0",
)
WORKER_IDLE.set(1)


@contextmanager
def track_bedrock(purpose: str):
    """Bedrock 호출 계측용 context manager."""
    start = time.perf_counter()
    try:
        yield
        BEDROCK_CALLS.labels(purpose=purpose, status="success").inc()
    except Exception:
        BEDROCK_CALLS.labels(purpose=purpose, status="failed").inc()
        raise
    finally:
        BEDROCK_LATENCY.labels(purpose=purpose).observe(time.perf_counter() - start)


@contextmanager
def track_stt():
    """STT 호출 계측용 context manager."""
    start = time.perf_counter()
    try:
        yield
        STT_PROCESSED.labels(status="success").inc()
    except Exception:
        STT_PROCESSED.labels(status="failed").inc()
        raise
    finally:
        STT_LATENCY.observe(time.perf_counter() - start)


@contextmanager
def track_pdf():
    """PDF 생성 계측용 context manager."""
    start = time.perf_counter()
    try:
        yield
        PDF_GENERATED.labels(status="success").inc()
    except Exception:
        PDF_GENERATED.labels(status="failed").inc()
        raise
    finally:
        PDF_LATENCY.observe(time.perf_counter() - start)


def start_metrics_server(port: int = 9090) -> None:
    """별도 스레드에서 Prometheus metrics HTTP 서버 시작."""
    start_http_server(port)
