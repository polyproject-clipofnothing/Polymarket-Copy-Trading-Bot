"""
Execution Service (Phase 4+)

Purpose:
- The ONLY component allowed to place trades
- Must be gated behind explicit ENABLE_TRADING=true (future)

Phase 1/2 safety:
- This must never be called during Phase 1 or Phase 2
"""


from __future__ import annotations


def main() -> int:
    raise RuntimeError(
        "Execution is disabled in Phase 1 and Phase 2.\n"
        "Do not run trader execution services until Phase 4+."
    )
