"""
Execution Service (Phase 4+)

Purpose:
- The ONLY component allowed to place trades
- Must be gated behind explicit ENABLE_TRADING=true (future)

Phase 1/2/3 safety:
- This must never be called during Phase 1, Phase 2, or Phase 3
"""


from __future__ import annotations

import os


def main() -> int:
    """
    Entry point for live execution (Phase 4+ only).

    This is intentionally disabled by default. In later phases, we will:
    - require ENABLE_TRADING=true
    - require explicit environment + account protections
    - enforce circuit breakers / kill switch
    """
    enabled = os.getenv("ENABLE_TRADING", "").lower() == "true"
    if not enabled:
        raise RuntimeError(
            "Execution is disabled in Phase 1/2/3.\n"
            "To enable (Phase 4+ only), run with: ENABLE_TRADING=true\n"
            "Do not run trader execution services until Phase 4+."
        )

    # Phase 4+ wiring will go here
    print("[Phase 4+] Live execution enabled (placeholder).")
    return 0
