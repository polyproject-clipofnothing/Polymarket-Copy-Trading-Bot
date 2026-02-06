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

from pathlib import Path

from src.services.simulation.pipeline.reader import read_events
from src.services.simulation.pipeline.simulator import ReplayStats, replay_event_stream
from src.services.simulation.pipeline.reporter import print_summary, write_summary


def main() -> int:
    """
    Phase 1a entrypoint.

    Returns:
        int: process exit code (0 = success)
    """
    print("[Phase 1a] Simulation service starting (replay mode).")
    print(" - Reads recorder_data/events.jsonl")
    print(" - Writes simulation_results/replay_summary.json")
    print(" - No execution allowed. No private keys required.")

    events_path = Path("recorder_data") / "events.jsonl"
    out_path = Path("simulation_results") / "replay_summary.json"

    stats = ReplayStats()

    for event in read_events(events_path):
        replay_event_stream(stats, event)

    write_summary(out_path, stats)
    print_summary(stats)

    return 0
