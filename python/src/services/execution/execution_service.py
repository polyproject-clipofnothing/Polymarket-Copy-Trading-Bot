"""
Dry-Run Execution Service (Phase 3)

Purpose:
- Simulate execution ONLY (no real trades)
- Validate strategy outputs downstream
- Produce execution reports without placing orders

Safety:
- No trading
- No private keys
- ENABLE_TRADING must NOT be required
"""

from __future__ import annotations

from pathlib import Path

from src.config.validate import ConfigError, validate_runtime_config
from src.services.execution.pipeline.reader import read_intents
from src.services.execution.pipeline.engine import simulate_execution
from src.services.execution.pipeline.writer import write_reports


def main() -> int:
    """
    Phase 3 dry-run execution entrypoint.

    Returns:
        int: process exit code
             0 = success
             2 = configuration error
    """
    try:
        # Baseline runtime validation only
        validate_runtime_config()

    except ConfigError as e:
        print(f"[Config] {e}")
        return 2

    print("[Phase 3] Dry-run execution service starting.")
    print(" - Reads strategy_data/order_intents.jsonl")
    print(" - Writes execution_reports/dry_run_report.jsonl")
    print(" - No execution allowed. No private keys required.")

    intents_path = Path("strategy_data") / "order_intents.jsonl"
    out_path = Path("execution_reports") / "dry_run_report.jsonl"

    reports = []
    read_count = 0

    for intent in read_intents(intents_path):
        read_count += 1
        reports.append(simulate_execution(intent))

    written = write_reports(out_path, reports)

    print(f"[DryRun] Read intents: {read_count}")
    print(f"[DryRun] Wrote reports: {written}")
    return 0