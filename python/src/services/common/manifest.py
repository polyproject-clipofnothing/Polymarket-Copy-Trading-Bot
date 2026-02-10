from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional


def canonical_artifact_key(prefix: str, service: str, run_id: str, filename: str) -> str:
    """
    Produces: <prefix>/<service>/<run_id>/<filename>

    Example:
      polymarket-copy-bot/simulation/replay-123/manifest.json
    """
    p = prefix.strip().strip("/")
    if not p:
        p = "polymarket-copy-bot"
    return f"{p}/{service}/{run_id}/{filename}"


def get_git_sha() -> str:
    """
    Best-effort git SHA. Returns 'unknown' if git isn't available.
    """
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


@dataclass(frozen=True)
class RunManifest:
    schema_version: int
    service: str
    run_id: str

    started_at: float
    ended_at: float
    duration_s: float

    git_sha: str

    # only non-sensitive config snapshot
    config: Dict[str, Any]

    # logical name -> key/path
    artifacts: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "service": self.service,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_s": self.duration_s,
            "git_sha": self.git_sha,
            "config": self.config,
            "artifacts": self.artifacts,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)