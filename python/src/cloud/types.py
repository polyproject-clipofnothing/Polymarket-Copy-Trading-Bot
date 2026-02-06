from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


JsonDict = Dict[str, Any]


@dataclass(frozen=True)
class CloudWriteResult:
    uri: str
    bytes_written: int
    metadata: Optional[JsonDict] = None
