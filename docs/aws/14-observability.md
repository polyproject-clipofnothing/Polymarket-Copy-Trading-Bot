# Observability Baseline (PR20)

This document describes the baseline observability features introduced in **PR20**.  
These changes establish a consistent foundation for debugging, auditing, and future
metrics/alerting pipelines.

---

## Goals

PR20 focuses on:

- Consistent **run lifecycle visibility**
- Clear **failure diagnostics**
- Minimal but extensible **event schema**
- Optional **structured (JSON) logging** for future ingestion (CloudWatch, Loki, etc.)

This is intentionally lightweight and Phase-1 safe.

---

## Run Lifecycle Events

All long-running services emit standardized run lifecycle events:

- `run_start`
- `run_end`
- `run_error`

These events are emitted **exactly once per run**, regardless of backend
(local or cloud).

They form the canonical timeline for:

- Debugging failures
- Measuring durations
- Correlating artifacts
- Future metrics extraction

---

## Event Schema

All run events share the same minimal schema:

| Field | Description |
|-----|-------------|
| `type` | `run_start`, `run_end`, or `run_error` |
| `service` | Service name (`simulation`, `recorder`, etc.) |
| `run_id` | Unique identifier for the run |
| `ts` | Unix timestamp (seconds) |
| `level` | `info` or `error` |
| `message` | Short human-readable message |
| `context` | JSON-safe dictionary with service-specific metadata |

---

## Event Examples

### run_start

```json
{
  "type": "run_start",
  "service": "simulation",
  "run_id": "replay-1770758790",
  "level": "info",
  "message": "Run started",
  "context": {
    "inputs": {
      "events_path": "recorder_data/events.jsonl"
    },
    "object_store_backend": "s3",
    "cloud_backend": "local"
  }
}