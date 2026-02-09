from __future__ import annotations

from src.config.cloud import CLOUD_BACKEND, LOCAL_EVENT_DIR, LOCAL_OBJECT_DIR
from .interfaces import CloudServices
from .local import LocalCloudServices, LocalEventPublisher, LocalObjectStore, EnvSecretProvider


_cloud_singleton: CloudServices | None = None


def get_cloud() -> CloudServices:
    """
    Returns the cloud service container. Phase 1 returns local implementations.
    Phase 2 will add AWS implementations without changing callers.
    """
    global _cloud_singleton
    if _cloud_singleton is not None:
        return _cloud_singleton

    backend = CLOUD_BACKEND
    if backend == "local":
        _cloud_singleton = LocalCloudServices(
            events=LocalEventPublisher(LOCAL_EVENT_DIR),
            objects=LocalObjectStore(LOCAL_OBJECT_DIR),
            secrets=EnvSecretProvider(),
        )
        return _cloud_singleton

    # Placeholder for Phase 2
    raise RuntimeError(
        f"CLOUD_BACKEND={backend!r} not supported in Phase 1. Use CLOUD_BACKEND=local."
    )
