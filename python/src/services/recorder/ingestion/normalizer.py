from __future__ import annotations
from typing import Dict


def normalize_event(raw_event: Dict) -> Dict:
    """
    Convert raw events into canonical format.
    """
    return {
        "version": 1,
        "source": raw_event["source"],
        "type": raw_event["event_type"],
        "market_id": raw_event["market_id"],
        "timestamp": raw_event["timestamp"],
        "payload": raw_event["raw"],
    }
