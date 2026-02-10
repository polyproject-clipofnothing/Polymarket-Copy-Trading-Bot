"""
Strategy Service (Phase 2)

Purpose:
- Generate signals / order_intent messages only
- No execution
- No private keys required

This service:
- consumes canonical raw-events (Phase 1b output)
- emits order_intents (signal-only) for downstream execution (Phase 4+)
"""

from __future__ import annotations

from pathlib import Path

from src.config.validate import ConfigError, validate_runtime_config
from src.services.strategy.pipeline.reader import read_events
from src.services.strategy.pipeline.generator import generate_order_intent
from src.services.strategy.pipeline.writer import write_order_intents


def main() -> int:
    """
    Phase 2 entrypoint (signal-only).

    Returns:
        int: process exit code (0 = success)
    """
    # Fail fast if runtime config is invalid.
    # Strategy is currently local-only, but we still validate in case future
    # changes add cloud dependencies (and to keep entrypoints consistent).
    try:
        validate_runtime_config()
    except ConfigError as e:
        print(f"[Config] {e}")
        return 2

    print("[Phase 2] Strategy service starting (signal-only).")
    print(" - Reads recorder_data/events.jsonl")
    print(" - Emits strategy_data/order_intents.jsonl")
    print(" - No execution allowed. No private keys required.")

    events_path = Path("recorder_data") / "events.jsonl"
    out_path = Path("strategy_data") / "order_intents.jsonl"

    intents = []
    read_count = 0

    for event in read_events(events_path):
        read_count += 1
        intent = generate_order_intent(event)
        if intent is not None:
            intents.append(intent)

    written = write_order_intents(out_path, intents)

    print(f"[Strategy] Read events: {read_count}")
    print(f"[Strategy] Wrote intents: {written}")
    return 0