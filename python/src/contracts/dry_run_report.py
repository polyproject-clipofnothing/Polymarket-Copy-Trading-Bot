from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class DryRunReport:
    version: int
    market_id: str
    side: str
    confidence: float
    max_price: float

    # simulated fields
    assumed_fill_price: float
    assumed_slippage: float
    assumed_fee: float
    status: str

    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "market_id": self.market_id,
            "side": self.side,
            "confidence": self.confidence,
            "max_price": self.max_price,
            "assumed_fill_price": self.assumed_fill_price,
            "assumed_slippage": self.assumed_slippage,
            "assumed_fee": self.assumed_fee,
            "status": self.status,
            "metadata": self.metadata,
        }
