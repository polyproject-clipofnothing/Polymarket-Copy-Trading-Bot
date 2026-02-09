from __future__ import annotations

from typing import Protocol, Optional, Mapping, Any
from .types import CloudWriteResult, JsonDict


class EventPublisher(Protocol):
    """
    Publishes events to some backend (local log, SQS, Kinesis, etc.)
    """
    def publish(self, topic: str, event: JsonDict) -> None: ...
    def flush(self) -> None: ...


class ObjectStore(Protocol):
    """
    Stores and retrieves blobs (local filesystem, S3, etc.)
    """
    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> CloudWriteResult: ...
    def get_bytes(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...


class SecretProvider(Protocol):
    """
    Fetches secrets/config (env vars now; Secrets Manager later).
    """
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]: ...
    def require(self, key: str) -> str: ...


class CloudServices(Protocol):
    """
    Container for all cloud boundary services.
    """
    @property
    def events(self) -> EventPublisher: ...

    @property
    def objects(self) -> ObjectStore: ...

    @property
    def secrets(self) -> SecretProvider: ...
