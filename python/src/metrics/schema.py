from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


# -------------------------
# Canonical Metric Record (PR22)
# -------------------------
# Example:
# {
#   "schema_version": 1,
#   "metric_name": "events_ingested_total",
#   "metric_type": "counter",
#   "value": 1,
#   "ts": 1770511200,
#   "dimensions": {
#     "service": "recorder",
#     "run_id": "recorder-1770511163",
#     "env": "dev",
#     "market_id": "example_market",
#     "stage": "ingest"
#   }
# }


MetricType = str  # "counter" | "gauge" | "histogram"


REQUIRED_DIMENSIONS = ("service", "run_id", "env")


def now_ts() -> float:
    return time.time()


def validate_dimensions(dimensions: Dict[str, Any]) -> None:
    if not isinstance(dimensions, dict):
        raise ValueError("dimensions must be a dict")

    missing = [k for k in REQUIRED_DIMENSIONS if k not in dimensions or dimensions.get(k) in (None, "")]
    if missing:
        raise ValueError(f"missing required dimensions: {missing}")

    # Ensure JSON-safe keys
    for k in list(dimensions.keys()):
        if not isinstance(k, str):
            raise ValueError("dimension keys must be strings")


def validate_metric_type(metric_type: str) -> None:
    allowed = {"counter", "gauge", "histogram"}
    if metric_type not in allowed:
        raise ValueError(f"metric_type must be one of {sorted(allowed)}; got '{metric_type}'")


@dataclass(frozen=True)
class MetricRecord:
    schema_version: int
    metric_name: str
    metric_type: MetricType
    value: float
    ts: float
    dimensions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "metric_name": str(self.metric_name),
            "metric_type": str(self.metric_type),
            "value": float(self.value),
            "ts": float(self.ts),
            "dimensions": dict(self.dimensions),
        }


def metric(
    *,
    metric_name: str,
    metric_type: MetricType,
    value: float,
    dimensions: Dict[str, Any],
    ts: Optional[float] = None,
    schema_version: int = 1,
) -> MetricRecord:
    if not metric_name or not isinstance(metric_name, str):
        raise ValueError("metric_name must be a non-empty string")

    validate_metric_type(metric_type)
    validate_dimensions(dimensions)

    # Value must be numeric
    try:
        v = float(value)
    except Exception as e:
        raise ValueError(f"value must be numeric: {e}") from e

    t = now_ts() if ts is None else float(ts)

    return MetricRecord(
        schema_version=int(schema_version),
        metric_name=metric_name,
        metric_type=metric_type,
        value=v,
        ts=t,
        dimensions=dimensions,
    )