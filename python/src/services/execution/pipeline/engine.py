from __future__ import annotations

from typing import Dict, Any

from src.contracts.dry_run_report import DryRunReport


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def simulate_execution(intent: Dict[str, Any]) -> DryRunReport:
    """
    Phase 3: simulate execution outcome.
    No RPC, no execution, no keys.
    """
    market_id = str(intent.get("market_id", "unknown_market"))
    side = str(intent.get("side", "YES")).upper()
    confidence = float(intent.get("confidence", 0.0))
    max_price = float(intent.get("max_price", 0.5))

    # simple deterministic assumptions (placeholder)
    assumed_slippage = _clamp(0.01 + (1.0 - confidence) * 0.02, 0.0, 0.05)
    assumed_fill_price = _clamp(max_price - assumed_slippage, 0.01, 0.99)

    # flat fee placeholder
    assumed_fee = 0.001

    status = "simulated"

    return DryRunReport(
        version=1,
        market_id=market_id,
        side=side,
        confidence=confidence,
        max_price=max_price,
        assumed_fill_price=assumed_fill_price,
        assumed_slippage=assumed_slippage,
        assumed_fee=assumed_fee,
        status=status,
        metadata={"intent": intent},
    )
