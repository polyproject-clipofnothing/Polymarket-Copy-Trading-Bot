from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.contracts.dry_run_report import DryRunReport


def write_reports(path: Path, reports: Iterable[DryRunReport]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with path.open("a") as f:
        for report in reports:
            f.write(json.dumps(report.to_dict()) + "\n")
            count += 1
    return count
