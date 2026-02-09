from __future__ import annotations
import json
from pathlib import Path
from typing import Dict


DATA_DIR = Path("recorder_data")
DATA_DIR.mkdir(exist_ok=True)


def write_event(event: Dict) -> None:
    """
    Append-only JSONL writer.
    """
    file_path = DATA_DIR / "events.jsonl"
    with file_path.open("a") as f:
        f.write(json.dumps(event) + "\n")
