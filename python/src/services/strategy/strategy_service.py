"""
Strategy Service (Phase 2)

Purpose:
- Generate signals / order_intent messages only
- No execution
- No private keys required

This is a scaffold entrypoint that will be wired to:
- consume raw-events (from storage/queue)
- emit order_intents (to local files/S3/SQS) in later PRs
"""


from __future__ import annotations


def main() -> int:
    """
    Phase 2 entrypoint (signal-only).

    Returns:
        int: process exit code (0 = success)
    """
    print("[Phase 2] Strategy service starting (scaffold).")
    print(" - Signal-only (order_intent generation).")
    print(" - No execution allowed.")
    print(" - No private keys required.")
    print("TODO: Consume raw-events and emit order_intents (no trading).")
    return 0
