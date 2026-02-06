from __future__ import annotations

from typing import Dict, Optional

from src.contracts.order_intent import OrderIntent


def generate_order_intent(event: Dict) -> Optional[OrderIntent]:
    """
    Phase 2: convert a canonical raw-event into an order_intent.
    Signal-only, no execution.

    Current logic (simple placeholder):
    - If event type is trade_detected, emit a low-confidence intent.
    """
    if event.get("type") != "trade_detected":
        return None

    market_id = event.get("market_id", "unknown_market")
    payload = event.get("payload", {}) or {}

    # Placeholder heuristics
    side = str(payload.get("side", "YES")).upper()
    price = float(payload.get("price", 0.5))

    return OrderIntent(
        version=1,
        source_event_type=event.get("type", "unknown"),
        market_id=market_id,
        side=side,
        confidence=0.10,           # intentionally low until real strategy added
        max_price=min(price + 0.02, 0.99),  # placeholder
        metadata={"raw_event": event},
    )
