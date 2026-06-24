"""S3 presigned URL. KMS 암호화 버킷 사용(security.md).

로컬(SQLite/AWS 미연결) 모드에서는 boto3가 없어도 앱이 뜨도록 지연 임포트한다.
"""
from ..config import settings

_client = None


def _s3():
    global _client
    if _client is None:
        import boto3  # 지연 임포트 (로컬 모드에서 boto3 미설치 허용)
        _client = boto3.client("s3", region_name=settings.aws_region)
    return _client


# 모바일 직접 PUT 시 클라이언트가 보내는 실제 MIME 화이트리스트.
# S3 presigned PUT은 서명된 ContentType과 PUT 헤더가 정확히 일치해야 통과한다.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "application/pdf",
    "text/plain",
}


def presign_put(
    file_key: str, file_type: str, expires: int = 300, content_type: str | None = None
) -> str:
    if content_type:
        # 앱이 실제 MIME(image/jpeg 등)을 주면 그대로 서명 → PUT 헤더와 100% 일치
        ct = content_type
    else:
        # (기존 동작 그대로 — content_type 미전달 클라이언트/웹 무영향)
        ct = {"image": "image/*", "pdf": "application/pdf", "text": "text/plain"}.get(
            file_type, "application/octet-stream"
        )
    return _s3().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": file_key, "ContentType": ct},
        ExpiresIn=expires,
    )


def presign_get(file_key: str, expires: int = 300) -> str:
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": file_key},
        ExpiresIn=expires,
    )
