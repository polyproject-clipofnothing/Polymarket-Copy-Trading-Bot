"""
Simulation Service (Phase 1a)

Purpose:
- Backtesting / historical simulations only
- Offline analysis, no live execution
- No private keys required

This service:
- replays canonical raw-events recorded by Phase 1b
- produces metrics and summary outputs (no trading)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict

from src.cloud.factory import get_cloud
from src.config.validate import ConfigError, validate_runtime_config
from src.metrics import metric
from src.metrics.writer import MetricsWriter
from src.observability.events import run_end, run_error, run_start
from src.services.common.manifest import RunManifest, get_git_sha
from src.services.simulation.pipeline.reader import read_events
from src.services.simulation.pipeline.reporter import print_summary, write_summary
from src.services.simulation.pipeline.simulator import ReplayStats, replay_event_stream
from src.utils.logger import log_event


def _norm_prefix(prefix: str | None) -> str:
    p = (prefix or "").strip().strip("/")
    return p if p else "polymarket-copy-bot"


def _join(prefix: str, rel_key: str) -> str:
    return f"{prefix}/{rel_key.strip().lstrip('/')}"


def main() -> int:
    # -------------------------
    # Fail-fast runtime config
    # -------------------------
    try:
        validate_runtime_config()
    except ConfigError as e:
        log_event({"level": "error", "message": f"[Config] {e}", "context": {"type": "config_error"}})
        return 2

    # Banner as structured logs if LOG_FORMAT=json
    log_event({"level": "info", "message": "[Phase 1a] Simulation service starting (replay mode).", "context": {"type": "banner"}})
    log_event({"level": "info", "message": " - Reads recorder_data/events.jsonl", "context": {"type": "banner"}})
    log_event({"level": "info", "message": " - Writes simulation_results/replay_summary.json", "context": {"type": "banner"}})
    log_event({"level": "info", "message": " - No execution allowed. No private keys required.", "context": {"type": "banner"}})

    cloud = get_cloud()

    env = os.getenv("BOT_ENV", "dev")
    run_id = f"replay-{int(time.time())}"
    started_at = time.time()

    # Metrics writer (local always; S3 best-effort if configured)
    mw = MetricsWriter(service="simulation", run_id=run_id, env=env)

    events_path = Path("recorder_data") / "events.jsonl"
    local_summary_path = Path("simulation_results") / "replay_summary.json"
    local_manifest_path = Path("simulation_results") / "manifest.json"

    prefix = _norm_prefix(os.getenv("S3_OBJECT_PREFIX", "polymarket-copy-bot"))

    rel_replay_key = f"simulation/{run_id}/replay_summary.json"
    rel_manifest_key = f"simulation/{run_id}/manifest.json"

    full_replay_key = _join(prefix, rel_replay_key)
    full_manifest_key = _join(prefix, rel_manifest_key)

    log_event(
        run_start(
            service="simulation",
            run_id=run_id,
            ts=started_at,
            context={
                "mode": "replay",
                "inputs": {"events_path": str(events_path)},
                "cloud_backend": os.getenv("CLOUD_BACKEND", "local"),
                "object_store_backend": os.getenv("OBJECT_STORE_BACKEND", "local"),
                "env": env,
            },
        )
    )

    try:
        # -------------------------
        # Replay
        # -------------------------
        replay_start = time.time()

        stats = ReplayStats()
        for event in read_events(events_path):
            replay_event_stream(stats, event)

        replay_end = time.time()
        replay_ms = (replay_end - replay_start) * 1000.0

        # core metrics (simulation)
        mw.write(
            metric(
                metric_name="events_replayed_total",
                metric_type="counter",
                value=float(stats.events_total),
                dimensions={"service": "simulation", "run_id": run_id, "env": env, "mode": "replay"},
            )
        )
        mw.write(
            metric(
                metric_name="replay_duration_ms",
                metric_type="gauge",
                value=replay_ms,
                dimensions={"service": "simulation", "run_id": run_id, "env": env, "mode": "replay"},
            )
        )

        payload: Dict = {
            "version": 1,
            "run_id": run_id,
            "events_total": stats.events_total,
            "events_by_type": stats.events_by_type,
        }

        # -------------------------
        # Artifact writes (local always; S3 best-effort)
        # -------------------------
        write_start = time.time()

        # Local summary (always)
        write_summary(local_summary_path, stats)

        # Best-effort object store replay summary
        s3_ok_summary = True
        try:
            cloud.objects.put_bytes(
                key=rel_replay_key,
                data=json.dumps(payload, indent=2).encode("utf-8"),
                content_type="application/json",
            )
        except Exception as e:
            s3_ok_summary = False
            log_event(
                {
                    "level": "warning",
                    "message": "Simulation S3 write failed for replay_summary (continuing local-only)",
                    "context": {"error": str(e), "service": "simulation", "run_id": run_id},
                }
            )

        finished_at = time.time()

        # Manifest
        manifest = RunManifest(
            schema_version=1,
            service="simulation",
            run_id=run_id,
            started_at=started_at,
            ended_at=finished_at,
            duration_s=finished_at - started_at,
            git_sha=get_git_sha(),
            config={
                "cloud_backend": os.getenv("CLOUD_BACKEND", "local"),
                "object_store_backend": os.getenv("OBJECT_STORE_BACKEND", "local"),
                "aws_region": os.getenv("AWS_REGION"),
                "s3_bucket": os.getenv("S3_OBJECT_BUCKET"),
                "s3_prefix": prefix,
                "inputs": {"events_path": str(events_path)},
            },
            artifacts={
                # Keep intended keys for determinism, plus local paths and S3 success flag
                "replay_summary": full_replay_key,
                "manifest": full_manifest_key,
                "local_summary_path": str(local_summary_path),
                "local_manifest_path": str(local_manifest_path),
                "s3_ok_replay_summary": s3_ok_summary,
            },
        )

        local_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        local_manifest_path.write_text(manifest.to_json() + "\n", encoding="utf-8")

        # Best-effort object store manifest
        s3_ok_manifest = True
        try:
            cloud.objects.put_bytes(
                key=rel_manifest_key,
                data=(manifest.to_json() + "\n").encode("utf-8"),
                content_type="application/json",
            )
        except Exception as e:
            s3_ok_manifest = False
            log_event(
                {
                    "level": "warning",
                    "message": "Simulation S3 write failed for manifest (continuing local-only)",
                    "context": {"error": str(e), "service": "simulation", "run_id": run_id},
                }
            )

        write_end = time.time()
        artifact_write_ms = (write_end - write_start) * 1000.0

        mw.write(
            metric(
                metric_name="artifact_write_latency_ms",
                metric_type="gauge",
                value=artifact_write_ms,
                dimensions={"service": "simulation", "run_id": run_id, "env": env, "mode": "replay"},
            )
        )

        # End event
        duration_s = finished_at - started_at
        log_event(
            run_end(
                service="simulation",
                run_id=run_id,
                duration_s=duration_s,
                ts=finished_at,
                context={
                    "mode": "replay",
                    "artifacts": {
                        "replay_summary": full_replay_key,
                        "manifest": full_manifest_key,
                    },
                    "s3_ok_replay_summary": s3_ok_summary,
                    "s3_ok_manifest": s3_ok_manifest,
                },
            )
        )

        print_summary(stats)
        return 0

    except Exception as e:
        finished_at = time.time()
        duration_s = finished_at - started_at

        mw.write(
            metric(
                metric_name="error_total",
                metric_type="counter",
                value=1,
                dimensions={"service": "simulation", "run_id": run_id, "env": env, "mode": "replay"},
            )
        )

        log_event(
            run_error(
                service="simulation",
                run_id=run_id,
                error=e,
                duration_s=duration_s,
                ts=finished_at,
                context={"mode": "replay"},
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())