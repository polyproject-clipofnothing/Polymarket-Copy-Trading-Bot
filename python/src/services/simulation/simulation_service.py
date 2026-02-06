"""
Simulation Service (Phase 1a)

Purpose:
- Backtesting / historical simulations only
- Offline analysis, no live execution
- No private keys required

This is a scaffold entrypoint that will be wired to:
- existing src/scripts/simulation modules
- result outputs to simulation_results/ (and later S3)
"""


from __future__ import annotations


def main() -> int:
    """
    Phase 1a entrypoint.

    Returns:
        int: process exit code (0 = success)
    """
    print("[Phase 1a] Simulation service starting (scaffold).")
    print(" - Offline only.")
    print(" - No execution allowed.")
    print(" - No private keys required.")
    print("TODO: Wire to existing simulation runners and persist results.")
    return 0
