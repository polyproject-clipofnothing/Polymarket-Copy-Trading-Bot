from __future__ import annotations

from src.config.cloud import (
    CLOUD_BACKEND,
    OBJECT_STORE_BACKEND,
    LOCAL_EVENT_DIR,
    LOCAL_OBJECT_DIR,
)
from .interfaces import CloudServices
from .local import LocalCloudServices, LocalEventPublisher, LocalObjectStore, EnvSecretProvider


_cloud_singleton: CloudServices | None = None


def get_cloud() -> CloudServices:
    """
    Returns the cloud service container.

    Phase 1 safety:
    - CLOUD_BACKEND must remain 'local'
    - events remain local JSONL
    - secrets remain env-based
    - objects can be local (default) or S3 (opt-in via OBJECT_STORE_BACKEND=s3)
    """
    global _cloud_singleton
    if _cloud_singleton is not None:
        return _cloud_singleton

    backend = CLOUD_BACKEND
    if backend != "local":
        raise RuntimeError(
            f"CLOUD_BACKEND={backend!r} not supported in Phase 1. Use CLOUD_BACKEND=local."
        )

    events = LocalEventPublisher(LOCAL_EVENT_DIR)
    secrets = EnvSecretProvider()

    if OBJECT_STORE_BACKEND == "s3":
        from .aws_s3 import S3ObjectStore
        objects = S3ObjectStore()
    else:
        objects = LocalObjectStore(LOCAL_OBJECT_DIR)

    _cloud_singleton = LocalCloudServices(events=events, objects=objects, secrets=secrets)
    return _cloud_singleton
