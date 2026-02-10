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

import signal
import time
from typing import Any

from src.cloud.factory import get_cloud
from src.config.validate import ConfigError, validate_runtime_config
from src.observability.events import run_end, run_error, run_start
from src.services.recorder.ingestion.poller_polymarket_gamma import poll_events
from src.services.recorder.ingestion.normalizer import normalize_event
from src.services.recorder.ingestion.writer import write_event
from src.utils.logger import error as log_error
from src.utils.logger import info as log_info
from src.utils.logger import log_event


class _ShutdownFlag:
    def __init__(self) -> None:
        self.requested = False
        self.reason = "unknown"


def main() -> int:
    # Banner (go through logger so JSON mode stays valid JSONL)
    log_info("[Phase 1b] Recorder service starting.", context={"type": "banner"})
    log_info(" - Ingestion enabled.", context={"type": "banner"})
    log_info(" - No execution allowed.", context={"type": "banner"})
    log_info(" - No private keys required.", context={"type": "banner"})

    # -------------------------
    # Fail-fast runtime config
    # -------------------------
    try:
        validate_runtime_config()
    except ConfigError as e:
        log_error(f"[Config] {e}", context={"type": "config_error"})
        return 2

    # Fail fast if env/config is invalid (especially S3 ObjectStore config)
    try:
        validate_runtime_config()
    except ConfigError as e:
        print(f"[Config] {e}")
        return 2

    cloud = get_cloud()

    run_id = f"recorder-{int(time.time())}"
    started_at = time.time()

    shutdown = _ShutdownFlag()

    def _handle_signal(signum: int, frame: Any) -> None:  # noqa: ARG001
        shutdown.requested = True
        shutdown.reason = "SIGINT" if signum == signal.SIGINT else "SIGTERM"

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    processed = 0

    # Emit run_start
    log_event(
        run_start(
            service="recorder",
            run_id=run_id,
            ts=started_at,
            context={
                "cloud_backend": "local",
                "object_store_backend": "local",  # recorder writes local jsonl today
            },
        )
    )

    try:
        for raw_event in poll_events():
            if shutdown.requested:
                break

            event = normalize_event(raw_event)

            # Publish canonical event for downstream consumers (Phase 1 local backend)
            cloud.events.publish("recorder", event)

            # Local write (Phase 1)
            write_event(event)
            processed += 1

            # Per-event log (logger, not print)
            log_info(
                "Recorder event written",
                context={
                    "type": "recorder_event",
                    "event_type": event.get("type"),
                    "processed_events": processed,
                },
            )

        finished_at = time.time()
        duration_s = finished_at - started_at

        # Emit run_end
        log_event(
            run_end(
                service="recorder",
                run_id=run_id,
                ts=finished_at,
                duration_s=duration_s,
                context={
                    "processed_events": processed,
                    "shutdown_requested": shutdown.requested,
                    "shutdown_reason": shutdown.reason if shutdown.requested else None,
                },
            )
        )

        return 0

    except Exception as e:
        finished_at = time.time()
        duration_s = finished_at - started_at

        # Emit run_error
        log_event(
            run_error(
                service="recorder",
                run_id=run_id,
                ts=finished_at,
                duration_s=duration_s,
                error=e,
                context={
                    "processed_events": processed,
                },
            )
        )

        log_error("Recorder failed", context={"error": str(e), "processed_events": processed})
        return 1
