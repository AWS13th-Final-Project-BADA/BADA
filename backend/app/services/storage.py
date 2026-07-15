"""Evidence file storage seam.

Local development stores files under ``settings.upload_dir``. Production can
switch to S3 by setting ``STORAGE_MODE=s3`` and ``S3_BUCKET``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..config import settings


class Storage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> str: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def url(self, key: str) -> str: ...


class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def url(self, key: str) -> str:
        return f"/files/{key}"


class S3Storage(Storage):
    def __init__(self, bucket: str, region: str):
        import boto3  # Deferred import so local mode does not require boto3.

        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def save(self, key: str, data: bytes) -> str:  # pragma: no cover
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def read(self, key: str) -> bytes:  # pragma: no cover
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def url(self, key: str) -> str:  # pragma: no cover
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=300,
        )


def get_storage() -> Storage:
    if settings.storage_mode == "s3" and settings.s3_bucket:
        return S3Storage(settings.s3_bucket, settings.aws_region)
    return LocalStorage(settings.upload_dir)
