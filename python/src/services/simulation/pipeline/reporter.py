from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.services.simulation.pipeline.simulator import ReplayStats


def write_summary(path: Path, stats: ReplayStats) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict = {
        "version": 1,
        "events_total": stats.events_total,
        "events_by_type": stats.events_by_type,
    }

    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def print_summary(stats: ReplayStats) -> None:
    print("[Simulation] Replay summary")
    print(f" - Total events: {stats.events_total}")

    for k in sorted(stats.events_by_type.keys()):
        print(f" - {k}: {stats.events_by_type[k]}")
