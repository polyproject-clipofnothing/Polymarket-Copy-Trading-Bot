from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .exceptions import SecretNotFound, ObjectNotFound
from .interfaces import EventPublisher, ObjectStore, SecretProvider, CloudServices
from .types import CloudWriteResult, JsonDict


class LocalEventPublisher:
    """
    Writes events as JSONL files under LOCAL_EVENT_DIR, partitioned by topic/day.
    """
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, topic: str, event: JsonDict) -> None:
        # Partition by date (UTC) to keep files manageable
        day = time.strftime("%Y-%m-%d", time.gmtime())
        out_dir = self.base_dir / topic
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{day}.jsonl"

        record = {
            "topic": topic,
            "ts": time.time(),
            "event": event,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def flush(self) -> None:
        # no-op for local file append
        return


class LocalObjectStore:
    """
    Stores raw bytes on disk.
    Keys are treated as relative paths.
    """
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        safe_key = key.lstrip("/").replace("..", "__")
        return self.base_dir / safe_key

    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> CloudWriteResult:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

        meta = {"content_type": content_type} if content_type else None
        return CloudWriteResult(uri=str(path), bytes_written=len(data), metadata=meta)

    def get_bytes(self, key: str) -> bytes:
        path = self._path_for(key)
        if not path.exists():
            raise ObjectNotFound(f"Object not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path_for(key).exists()


class EnvSecretProvider:
    """
    Reads secrets from environment variables (Phase 1).
    Later swapped with AWS Secrets Manager.
    """
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key, default)

    def require(self, key: str) -> str:
        value = os.getenv(key)
        if value is None or value == "":
            raise SecretNotFound(f"Missing required secret: {key}")
        return value


@dataclass(frozen=True)
class LocalCloudServices:
    events: EventPublisher
    objects: ObjectStore
    secrets: SecretProvider
