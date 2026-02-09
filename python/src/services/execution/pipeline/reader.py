from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator


def read_intents(path: Path) -> Iterator[Dict]:
    if not path.exists():
        return
        yield  # pragma: no cover

    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
