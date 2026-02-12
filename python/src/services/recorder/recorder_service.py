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

import os
import signal
import time

from src.cloud.factory import get_cloud
from src.config.validate import ConfigError, validate_runtime_config
from src.metrics import metric
from src.metrics.writer import MetricsWriter
from src.observability.events import run_end, run_error, run_start
from src.services.recorder.ingestion.poller_polymarket_gamma import poll_events
from src.services.recorder.ingestion.normalizer import normalize_event
from src.services.recorder.ingestion.writer import write_event
from src.utils.logger import log_event


def main() -> int:
    # Banner as structured logs (via logger’s json mode) if LOG_FORMAT=json
    log_event(
        {"level": "info", "message": "[Phase 1b] Recorder service starting.", "context": {"type": "banner"}}
    )
    log_event({"level": "info", "message": " - Ingestion enabled.", "context": {"type": "banner"}})
    log_event({"level": "info", "message": " - No execution allowed.", "context": {"type": "banner"}})
    log_event({"level": "info", "message": " - No private keys required.", "context": {"type": "banner"}})

    # Fail fast if env/config is invalid (especially S3 ObjectStore config)
    try:
        validate_runtime_config()
    except ConfigError as e:
        log_event({"level": "error", "message": f"[Config] {e}", "context": {"type": "config_error"}})
        return 2

    cloud = get_cloud()

    run_id = f"recorder-{int(time.time())}"
    started_at = time.time()
    env = os.getenv("BOT_ENV", "dev")

    # Metrics writer (local always; S3 best-effort if configured)
    mw = MetricsWriter(service="recorder", run_id=run_id, env=env)

    processed_events = 0
    shutdown_requested = False
    shutdown_reason: str | None = None

    # Graceful shutdown flag (SIGTERM/SIGINT)
    stop = {"requested": False, "reason": None}

    def _request_stop(reason: str) -> None:
        stop["requested"] = True
        stop["reason"] = reason

    def _handle_sigterm(_signum: int, _frame: object) -> None:
        _request_stop("SIGTERM")

    def _handle_sigint(_signum: int, _frame: object) -> None:
        _request_stop("SIGINT")

    # Register signal handlers (best-effort)
    try:
        signal.signal(signal.SIGTERM, _handle_sigterm)
        signal.signal(signal.SIGINT, _handle_sigint)
    except Exception:
        # Some environments may not allow signal registration
        pass

    log_event(
        run_start(
            service="recorder",
            run_id=run_id,
            ts=started_at,
            context={
                "cloud_backend": os.getenv("CLOUD_BACKEND", "local"),
                "object_store_backend": os.getenv("OBJECT_STORE_BACKEND", "local"),
                "env": env,
            },
        )
    )

    try:
        for raw_event in poll_events():
            # Honor shutdown request
            if stop["requested"]:
                shutdown_requested = True
                shutdown_reason = str(stop["reason"] or "shutdown_requested")
                break

            loop_start = time.time()

            # 1) ingested counter
            mw.write(
                metric(
                    metric_name="events_ingested_total",
                    metric_type="counter",
                    value=1,
                    dimensions={"service": "recorder", "run_id": run_id, "env": env},
                )
            )

            # Normalize + publish
            event = normalize_event(raw_event)
            cloud.events.publish("recorder", event)

            ingest_ms = (time.time() - loop_start) * 1000.0
            mw.write(
                metric(
                    metric_name="ingest_latency_ms",
                    metric_type="gauge",
                    value=ingest_ms,
                    dimensions={"service": "recorder", "run_id": run_id, "env": env},
                )
            )

            # Write event
            write_start = time.time()
            write_event(event)
            write_ms = (time.time() - write_start) * 1000.0

            processed_events += 1

            # 2) written counter + write latency
            mw.write(
                metric(
                    metric_name="events_written_total",
                    metric_type="counter",
                    value=1,
                    dimensions={"service": "recorder", "run_id": run_id, "env": env},
                )
            )
            mw.write(
                metric(
                    metric_name="write_latency_ms",
                    metric_type="gauge",
                    value=write_ms,
                    dimensions={"service": "recorder", "run_id": run_id, "env": env},
                )
            )

            # Optional: structured log about a processed event (Phase 1 safe)
            log_event(
                {
                    "level": "info",
                    "message": "Recorder event written",
                    "context": {
                        "type": "recorder_event",
                        "event_type": event.get("type"),
                        "processed_events": processed_events,
                    },
                }
            )

        finished_at = time.time()
        duration_s = finished_at - started_at

        log_event(
            run_end(
                service="recorder",
                run_id=run_id,
                duration_s=duration_s,
                ts=finished_at,
                context={
                    "processed_events": processed_events,
                    "shutdown_requested": shutdown_requested,
                    "shutdown_reason": shutdown_reason,
                },
            )
        )
        return 0

    except Exception as e:
        finished_at = time.time()
        duration_s = finished_at - started_at

        # error counter
        mw.write(
            metric(
                metric_name="error_total",
                metric_type="counter",
                value=1,
                dimensions={"service": "recorder", "run_id": run_id, "env": env},
            )
        )

        log_event(
            run_error(
                service="recorder",
                run_id=run_id,
                error=e,
                duration_s=duration_s,
                ts=finished_at,
                context={
                    "processed_events": processed_events,
                    "shutdown_requested": shutdown_requested,
                    "shutdown_reason": shutdown_reason,
                },
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())