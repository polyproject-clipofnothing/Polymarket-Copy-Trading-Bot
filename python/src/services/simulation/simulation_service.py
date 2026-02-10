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
import time
from pathlib import Path
from typing import Dict

from src.config.validate import ConfigError, validate_runtime_config
from src.cloud.factory import get_cloud
from src.services.simulation.pipeline.reader import read_events
from src.services.simulation.pipeline.simulator import ReplayStats, replay_event_stream
from src.services.simulation.pipeline.reporter import print_summary, write_summary


def main() -> int:
    """
    Phase 1a entrypoint.

    Returns:
        int: process exit code (0 = success)
    """
    # Fail fast if runtime config is invalid (S3, env vars, etc.)
    try:
        validate_runtime_config()
    except ConfigError as e:
        print(f"[Config] {e}")
        return 2

    print("[Phase 1a] Simulation service starting (replay mode).")
    print(" - Reads recorder_data/events.jsonl")
    print(" - Writes simulation_results/replay_summary.json")
    print(" - No execution allowed. No private keys required.")

    cloud = get_cloud()
    run_id = f"replay-{int(time.time())}"
    started_at = time.time()

    events_path = Path("recorder_data") / "events.jsonl"
    out_path = Path("simulation_results") / "replay_summary.json"

    # Publish start event
    cloud.events.publish(
        "simulation",
        {
            "type": "simulation_start",
            "mode": "replay",
            "run_id": run_id,
            "ts": started_at,
            "inputs": {
                "events_path": str(events_path),
            },
        },
    )

    stats = ReplayStats()

    for event in read_events(events_path):
        replay_event_stream(stats, event)

    # Canonical summary payload (single source of truth)
    payload: Dict = {
        "version": 1,
        "events_total": stats.events_total,
        "events_by_type": stats.events_by_type,
    }

    # Local write (Phase 1 convenience)
    write_summary(out_path, stats)

    # Cloud-compatible artifact write (local backend now, S3 later)
    artifact_key = f"simulation/{run_id}/replay_summary.json"
    cloud.objects.put_bytes(
        key=artifact_key,
        data=json.dumps(payload, indent=2).encode("utf-8"),
        content_type="application/json",
    )

    finished_at = time.time()
    cloud.events.publish(
        "simulation",
        {
            "type": "simulation_end",
            "mode": "replay",
            "run_id": run_id,
            "ts": finished_at,
            "duration_s": finished_at - started_at,
            "artifacts": {
                "replay_summary": artifact_key,
                "local_summary_path": str(out_path),
            },
        },
    )

    print_summary(stats)
    return 0