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
import traceback
from pathlib import Path
from typing import Dict

from src.cloud.factory import get_cloud
from src.config.validate import ConfigError, validate_runtime_config
from src.observability.events import run_end, run_error, run_start
from src.services.common.manifest import RunManifest, get_git_sha
from src.services.simulation.pipeline.reader import read_events
from src.services.simulation.pipeline.reporter import print_summary, write_summary
from src.services.simulation.pipeline.simulator import ReplayStats, replay_event_stream
from src.utils.logger import log_event


def _is_json_logs() -> bool:
    return os.getenv("LOG_FORMAT", "text").lower().strip() == "json"


def _banner(lines: list[str]) -> None:
    """
    In JSON mode: emit banner lines as JSON logs so stdout stays valid NDJSON.
    In text mode: preserve the existing print() UX.
    """
    if _is_json_logs():
        for line in lines:
            log_event({"level": "info", "message": line, "context": {"type": "banner"}})
    else:
        for line in lines:
            print(line)


def _norm_prefix(prefix: str | None) -> str:
    p = (prefix or "").strip().strip("/")
    return p if p else "polymarket-copy-bot"


def _join(prefix: str, rel_key: str) -> str:
    # Canonical key used in manifests/docs
    return f"{prefix}/{rel_key.strip().lstrip('/')}"


def main() -> int:
    """
    Phase 1a entrypoint.

    Returns:
        int: process exit code (0 = success)
    """
    # -------------------------
    # Fail-fast runtime config
    # -------------------------
    try:
        validate_runtime_config()
    except ConfigError as e:
        # Keep config errors human-readable even in JSON mode
        # (they're one-liners and super actionable)
        if _is_json_logs():
            log_event({"level": "error", "message": f"[Config] {e}", "context": {"type": "config_error"}})
        else:
            print(f"[Config] {e}")
        return 2

    _banner(
        [
            "[Phase 1a] Simulation service starting (replay mode).",
            " - Reads recorder_data/events.jsonl",
            " - Writes simulation_results/replay_summary.json",
            " - No execution allowed. No private keys required.",
        ]
    )

    cloud = get_cloud()

    run_id = f"replay-{int(time.time())}"
    started_at = time.time()

    events_path = Path("recorder_data") / "events.jsonl"
    local_summary_path = Path("simulation_results") / "replay_summary.json"
    local_manifest_path = Path("simulation_results") / "manifest.json"

    # Canonical prefix (PR19) for manifests/docs only
    prefix = _norm_prefix(os.getenv("S3_OBJECT_PREFIX", "polymarket-copy-bot"))

    # IMPORTANT:
    # - rel_* keys are relative-to-prefix (safe for object store implementations that prepend prefix)
    # - full_* keys are canonical keys recorded in manifests/docs
    rel_replay_key = f"simulation/{run_id}/replay_summary.json"
    rel_manifest_key = f"simulation/{run_id}/manifest.json"

    full_replay_key = _join(prefix, rel_replay_key)
    full_manifest_key = _join(prefix, rel_manifest_key)

    # Emit standardized run_start
    log_event(
        run_start(
            service="simulation",
            run_id=run_id,
            ts=started_at,
            context={
                "inputs": {"events_path": str(events_path)},
                "object_store_backend": os.getenv("OBJECT_STORE_BACKEND", "local"),
                "cloud_backend": os.getenv("CLOUD_BACKEND", "local"),
            },
        )
    )

    try:
        # Replay
        stats = ReplayStats()
        for event in read_events(events_path):
            replay_event_stream(stats, event)

        # Canonical summary payload
        payload: Dict = {
            "version": 1,
            "run_id": run_id,
            "events_total": stats.events_total,
            "events_by_type": stats.events_by_type,
        }

        # Local write (always)
        write_summary(local_summary_path, stats)

        # Object store write (local or S3 backend)
        # PASS RELATIVE KEY ONLY
        cloud.objects.put_bytes(
            key=rel_replay_key,
            data=(json.dumps(payload, indent=2) + "\n").encode("utf-8"),
            content_type="application/json",
        )

        finished_at = time.time()
        duration_s = finished_at - started_at

        # Manifest
        manifest = RunManifest(
            schema_version=1,
            service="simulation",
            run_id=run_id,
            started_at=started_at,
            ended_at=finished_at,
            duration_s=duration_s,
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
                # Canonical keys (what downstream tools should use)
                "replay_summary": full_replay_key,
                "manifest": full_manifest_key,
                # Local convenience
                "local_summary_path": str(local_summary_path),
                "local_manifest_path": str(local_manifest_path),
            },
        )

        # Local manifest write
        local_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        local_manifest_path.write_text(manifest.to_json() + "\n", encoding="utf-8")

        # Object store manifest write (relative key)
        cloud.objects.put_bytes(
            key=rel_manifest_key,
            data=(manifest.to_json() + "\n").encode("utf-8"),
            content_type="application/json",
        )

        # Emit standardized run_end
        log_event(
            run_end(
                service="simulation",
                run_id=run_id,
                ts=finished_at,
                duration_s=duration_s,
                context={
                    "artifacts": {
                        "replay_summary": full_replay_key,
                        "manifest": full_manifest_key,
                    }
                },
            )
        )

        # Keep existing human replay summary output ONLY in text mode
        if not _is_json_logs():
            print_summary(stats)

        return 0

    except Exception as e:
        finished_at = time.time()
        duration_s = finished_at - started_at

        log_event(
            run_error(
                service="simulation",
                run_id=run_id,
                ts=finished_at,
                duration_s=duration_s,
                error=e,
                context={
                    "artifacts": {
                        "replay_summary": full_replay_key,
                        "manifest": full_manifest_key,
                    }
                },
                stack=traceback.format_exc(),
            )
        )

        if not _is_json_logs():
            print(f"[ERROR] Simulation failed: {e}")

        return 1