from __future__ import annotations

import time
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RunEvent:
    """
    Minimal, consistent run event schema (PR20).

    type:      run_start | run_end | run_error
    service:   simulation | recorder | strategy | execution | trader | etc
    run_id:    per-run identifier (e.g. replay-<unix_ts>)
    ts:        unix timestamp (float seconds)
    level:     info | warning | error
    message:   short human message
    context:   JSON-safe dict for extra fields
    """
    type: str
    service: str
    run_id: str
    ts: float
    level: str
    message: str
    context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "service": self.service,
            "run_id": self.run_id,
            "ts": self.ts,
            "level": self.level,
            "message": self.message,
            "context": self.context,
        }


def _now() -> float:
    return time.time()


def run_start(
    *,
    service: str,
    run_id: str,
    ts: Optional[float] = None,
    message: str = "Run started",
    context: Optional[Dict[str, Any]] = None,
) -> RunEvent:
    return RunEvent(
        type="run_start",
        service=service,
        run_id=run_id,
        ts=_now() if ts is None else ts,
        level="info",
        message=message,
        context=context or {},
    )


def run_end(
    *,
    service: str,
    run_id: str,
    duration_s: float,
    ts: Optional[float] = None,
    message: str = "Run finished",
    context: Optional[Dict[str, Any]] = None,
) -> RunEvent:
    ctx = dict(context or {})
    ctx["duration_s"] = duration_s
    return RunEvent(
        type="run_end",
        service=service,
        run_id=run_id,
        ts=_now() if ts is None else ts,
        level="info",
        message=message,
        context=ctx,
    )


def run_error(
    *,
    service: str,
    run_id: str,
    error: Exception | str,
    ts: Optional[float] = None,
    duration_s: Optional[float] = None,
    message: str = "Run error",
    context: Optional[Dict[str, Any]] = None,
    stack: Optional[str] = None,
) -> RunEvent:
    ctx = dict(context or {})

    if duration_s is not None:
        ctx["duration_s"] = duration_s

    if isinstance(error, Exception):
        ctx["error_type"] = type(error).__name__
        ctx["error_message"] = str(error)
    else:
        ctx["error_type"] = "Error"
        ctx["error_message"] = str(error)

    # capture stack if not supplied
    ctx["stack"] = stack if stack is not None else traceback.format_exc()

    return RunEvent(
        type="run_error",
        service=service,
        run_id=run_id,
        ts=_now() if ts is None else ts,
        level="error",
        message=message,
        context=ctx,
    )