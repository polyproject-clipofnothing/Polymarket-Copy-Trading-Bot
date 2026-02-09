from __future__ import annotations

from typing import Dict


def normalize_event(raw_event: Dict) -> Dict:
    """
    Convert raw events into canonical format.
    """
    return {
        "version": 1,
        "source": raw_event.get("source", "unknown"),
        "type": raw_event.get("event_type", "unknown"),
        "timestamp": raw_event.get("timestamp"),
        "market_id": raw_event.get("market_id", "n/a"),
        "payload": raw_event.get("raw", {}),
    }
