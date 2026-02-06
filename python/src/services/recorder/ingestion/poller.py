from __future__ import annotations
import time
from typing import Iterator, Dict


def poll_events() -> Iterator[Dict]:
    """
    Phase-1 stub poller.
    Later: WebSocket / API polling.
    """
    while True:
        yield {
            "source": "polymarket",
            "event_type": "trade_detected",
            "market_id": "example_market",
            "timestamp": time.time(),
            "raw": {"price": 0.62, "side": "YES"},
        }
        time.sleep(2)
