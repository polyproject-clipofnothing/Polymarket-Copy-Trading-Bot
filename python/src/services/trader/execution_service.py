"""
Execution Service (Phase 4+)

Purpose:
- The ONLY component allowed to place trades
- Must be gated behind explicit ENABLE_TRADING=true

Safety guarantees:
- Must never run in Phase 1, Phase 2, or Phase 3
- Requires explicit opt-in + validated secrets
"""

from __future__ import annotations

from src.config.validate import (
    ConfigError,
    validate_runtime_config,
    validate_trading_config,
)


def main() -> int:
    """
    Entry point for live execution (Phase 4+ ONLY).

    Returns:
        int: process exit code
             0 = success
             2 = configuration error (fail fast)
    """
    try:
        # Baseline checks (safe for all phases)
        validate_runtime_config()

        # HARD GATE: trading must be explicitly enabled
        validate_trading_config()

    except ConfigError as e:
        print(f"[Config] {e}")
        return 2

    # ===============================
    # Phase 4+ execution wiring ONLY
    # ===============================
    print("[Phase 4+] Live execution ENABLED.")
    print(" - Trading secrets validated")
    print(" - Execution logic not yet implemented")

    # TODO (Phase 4+):
    # - create exchange client
    # - apply risk checks
    # - place orders
    # - record execution events
    # - support kill switch / circuit breaker

    return 0