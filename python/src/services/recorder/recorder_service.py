"""
Recorder Service (Phase 1b)

Purpose:
- Live monitoring / ingestion only
- No trading execution
- No private keys required

This is a scaffold entrypoint that will be wired to:
- websocket/polling ingestion
- persistence (S3/DynamoDB/Mongo) in later PRs
"""


from __future__ import annotations


def main() -> int:
    """
    Phase 1b entrypoint.

    Returns:
        int: process exit code (0 = success)
    """
    print("[Phase 1b] Recorder service starting (scaffold).")
    print(" - No execution allowed.")
    print(" - No private keys required.")
    print("TODO: Implement ingestion -> raw-events storage.")
    return 0
