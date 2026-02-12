from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.cloud.factory import get_cloud
from src.metrics.schema import MetricRecord
from src.utils.logger import warning


def _norm_prefix(prefix: str | None) -> str:
    p = (prefix or "").strip().strip("/")
    return p if p else "polymarket-copy-bot"


def _join(prefix: str, rel_key: str) -> str:
    return f"{prefix}/{rel_key.strip().lstrip('/')}"


class MetricsWriter:
    """
    Phase-safe metrics writer.

    Always writes locally to a JSONL file.
    If OBJECT_STORE_BACKEND=s3, also attempts to write a JSON object per line to S3 (best-effort).
    """

    def __init__(
        self,
        *,
        service: str,
        run_id: str,
        env: str,
        local_path: Path | str = "metrics_results/metrics.jsonl",
        prefix: Optional[str] = None,
    ) -> None:
        self.service = service
        self.run_id = run_id
        self.env = env

        self.local_path = Path(local_path)
        self.local_path.parent.mkdir(parents=True, exist_ok=True)

        self.prefix = _norm_prefix(prefix or os.getenv("S3_OBJECT_PREFIX", "polymarket-copy-bot"))

        # Relative object-store key (relative to prefix)
        self.rel_key = f"metrics/{self.service}/{self.run_id}/metrics.jsonl"
        self.full_key = _join(self.prefix, self.rel_key)

        self.cloud = get_cloud()

    def write(self, rec: MetricRecord) -> None:
        """
        Append one metric record as a JSONL line locally.
        Optionally emit to object store (best-effort) as one JSON object per line.
        """
        line_obj = rec.to_dict()
        line = json.dumps(line_obj, separators=(",", ":")) + "\n"

        # Local append (always)
        with self.local_path.open("a", encoding="utf-8") as f:
            f.write(line)

        backend = os.getenv("OBJECT_STORE_BACKEND", "local").lower().strip()
        if backend != "s3":
            return

        # Best-effort object store write
        try:
            ts_ms = int(time.time() * 1000)
            line_rel_key = f"metrics/{self.service}/{self.run_id}/lines/{ts_ms}.json"
            self.cloud.objects.put_bytes(
                key=line_rel_key,
                data=line.encode("utf-8"),
                content_type="application/json",
            )
        except Exception as e:
            # Don't crash the service if SSO expired / offline / perms, etc.
            warning(
                "Metrics S3 write failed (continuing with local-only metrics)",
                context={"error": str(e), "service": self.service, "run_id": self.run_id},
            )

    def info(self) -> Dict[str, Any]:
        return {
            "local_path": str(self.local_path),
            "rel_key": self.rel_key,
            "full_key": self.full_key,
            "object_store_backend": os.getenv("OBJECT_STORE_BACKEND", "local"),
        }