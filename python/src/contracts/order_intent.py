from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class OrderIntent:
    """
    Phase 2 signal-only message.

    NOTE: This is NOT an executable order.
    """
    version: int
    source_event_type: str
    market_id: str
    side: str
    confidence: float
    max_price: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "source_event_type": self.source_event_type,
            "market_id": self.market_id,
            "side": self.side,
            "confidence": self.confidence,
            "max_price": self.max_price,
            "metadata": self.metadata,
        }
