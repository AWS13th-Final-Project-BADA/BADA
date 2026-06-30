"""PDF Evidence Pack 생성 서비스 — WeasyPrint HTML→PDF.

분석 완료 후 호출되어 제출용(ko) PDF를 생성하고 S3에 저장한다.
다국어 폰트(Noto Sans 패밀리)는 Docker 이미지에 임베딩되어야 한다.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import jinja2

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_S3_BUCKET = os.environ.get("S3_REPORT_BUCKET", os.environ.get("S3_BUCKET", ""))
_AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

DISCLAIMER = (
    "본 자료는 법률자문이 아닌 상담 준비용 증거 정리 자료입니다. "
    "위법·체불 여부와 금액을 확정하지 않으며, 최종 판단은 고용노동부 또는 전문기관에서 확인해야 합니다."
)


def generate_evidence_pack(case_id: str, result: dict, case_info: dict, lang: str = "ko") -> str:
    """분석 결과 → PDF 렌더 → S3 업로드. 반환값: s3_key.

    Args:
        case_id: 사건 ID
        result: pipeline.process_case() 결과 dict
        case_info: {"workplace_name", "employer_name", "work_start_date", "work_end_date"}
        lang: PDF 언어 (기본 ko, 제출용)

    Returns:
        S3에 저장된 PDF의 키 문자열
    """
    html = _render_html(case_id, result, case_info, lang)
    pdf_bytes = _html_to_pdf(html)
    s3_key = _upload_to_s3(case_id, pdf_bytes, lang)
    return s3_key


def _render_html(case_id: str, result: dict, case_info: dict, lang: str) -> str:
    """Jinja2 템플릿으로 HTML 생성."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("evidence_pack.html")
    return template.render(
        case_id=case_id,
        case=case_info,
        result=result,
        lang=lang,
        disclaimer=DISCLAIMER,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def _html_to_pdf(html: str) -> bytes:
    """WeasyPrint HTML→PDF 변환. 폰트 서브셋 비활성화로 속도 최적화.

    WeasyPrint 63에서는 Document.write_pdf(uncompressed_pdf=True)로
    폰트 서브셋을 스킵. PDF 크기 커지지만 생성 2~3초에 완료.
    """
    from weasyprint import HTML

    document = HTML(string=html).render()
    pdf_bytes = document.write_pdf(uncompressed_pdf=True)
    return pdf_bytes


def _upload_to_s3(case_id: str, pdf_bytes: bytes, lang: str) -> str:
    """PDF를 S3 Report Bucket에 업로드."""
    if not _S3_BUCKET:
        # 로컬 개발: 파일로 저장
        out = Path(f"./reports/{case_id}_{lang}.pdf")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)
        logger.info("PDF 로컬 저장: %s (%d bytes)", out, len(pdf_bytes))
        return str(out)

    s3 = boto3.client("s3", region_name=_AWS_REGION)
    key = f"packs/{case_id}/{lang}/evidence-pack.pdf"
    s3.put_object(
        Bucket=_S3_BUCKET,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )
    logger.info("PDF S3 업로드: s3://%s/%s (%d bytes)", _S3_BUCKET, key, len(pdf_bytes))
    return key
