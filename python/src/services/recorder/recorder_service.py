"""
Recorder Service (Phase 1b)

Purpose:
- Live monitoring / ingestion only
- No trading execution
- No private keys required

This service produces raw canonical events for downstream consumers
(strategy, simulation, analytics).
"""

from __future__ import annotations

from src.cloud.factory import get_cloud

from __future__ import annotations

from src.services.recorder.ingestion.poller_polymarket_gamma import poll_events
from src.services.recorder.ingestion.normalizer import normalize_event
from src.services.recorder.ingestion.writer import write_event


def main() -> int:
    """
    Phase 1b entrypoint.

    Returns:
        int: process exit code (0 = success)
    """
    print("[Phase 1b] Recorder service starting.")
    print(" - Ingestion enabled.")
    print(" - No execution allowed.")
    print(" - No private keys required.")

    cloud = get_cloud()

    for raw_event in poll_events():
        event = normalize_event(raw_event)

        # Publish canonical event for downstream consumers (Phase 1 local backend)
        cloud.events.publish("recorder", event)

        write_event(event)
        print(f"[Recorder] Event written: {event['type']}")

    return 0
