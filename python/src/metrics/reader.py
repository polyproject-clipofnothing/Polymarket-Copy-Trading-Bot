from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from src.metrics.schema import MetricRecord


def read_metrics_jsonl(path: Path | str) -> Iterator[MetricRecord]:
    p = Path(path)
    if not p.exists():
        return iter(())

    def _iter() -> Iterator[MetricRecord]:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    yield MetricRecord.from_dict(obj)
                except Exception:
                    # best-effort: skip bad lines
                    continue

    return _iter()