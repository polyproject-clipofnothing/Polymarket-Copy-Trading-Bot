from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import boto3

from src.config.cloud import AWS_REGION, S3_OBJECT_BUCKET, S3_OBJECT_PREFIX
from src.cloud.exceptions import CloudError, ObjectNotFound
from src.cloud.types import CloudWriteResult


def _s3_key(key: str) -> str:
    clean = key.lstrip("/")
    if S3_OBJECT_PREFIX:
        return f"{S3_OBJECT_PREFIX}/{clean}"
    return clean


@dataclass
class S3ObjectStore:
    """
    S3-backed implementation of ObjectStore.
    Uses credentials from the standard AWS chain (AWS SSO session works via AWS_PROFILE).
    """
    bucket: str = S3_OBJECT_BUCKET

    def __post_init__(self) -> None:
        if not self.bucket:
            raise CloudError("S3_OBJECT_BUCKET is required when OBJECT_STORE_BACKEND=s3")
        self._client = boto3.client("s3", region_name=AWS_REGION)

    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> CloudWriteResult:
        s3_key = _s3_key(key)

        extra = {}
        if content_type:
            extra["ContentType"] = content_type

        self._client.put_object(Bucket=self.bucket, Key=s3_key, Body=data, **extra)

        uri = f"s3://{self.bucket}/{s3_key}"
        meta = {"content_type": content_type} if content_type else None
        return CloudWriteResult(uri=uri, bytes_written=len(data), metadata=meta)

    def get_bytes(self, key: str) -> bytes:
        s3_key = _s3_key(key)
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=s3_key)
            return resp["Body"].read()
        except self._client.exceptions.NoSuchKey as e:
            raise ObjectNotFound(f"S3 object not found: s3://{self.bucket}/{s3_key}") from e

    def exists(self, key: str) -> bool:
        s3_key = _s3_key(key)
        try:
            self._client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception:
            return False
