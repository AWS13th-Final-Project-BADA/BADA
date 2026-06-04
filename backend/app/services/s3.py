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


def presign_put(file_key: str, file_type: str, expires: int = 300) -> str:
    content_type = {"image": "image/*", "pdf": "application/pdf", "text": "text/plain"}.get(
        file_type, "application/octet-stream"
    )
    return _s3().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": file_key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def presign_get(file_key: str, expires: int = 300) -> str:
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": file_key},
        ExpiresIn=expires,
    )
