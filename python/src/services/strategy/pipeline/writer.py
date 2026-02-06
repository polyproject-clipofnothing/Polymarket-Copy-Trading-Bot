from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.contracts.order_intent import OrderIntent


def write_order_intents(path: Path, intents: Iterable[OrderIntent]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with path.open("a") as f:
        for intent in intents:
            f.write(json.dumps(intent.to_dict()) + "\n")
            count += 1
    return count
