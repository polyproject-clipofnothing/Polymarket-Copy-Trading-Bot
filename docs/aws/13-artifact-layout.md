# Artifact Layout + Per-Run Manifest (PR19)

## Goal
Standardize ObjectStore/S3 artifact keys so downstream tooling (dashboards, analytics, automation) can discover artifacts reliably.

This PR introduces:
- Canonical artifact key layout
- `manifest.json` written per run

---

## Canonical layout (under prefix)

Prefix (configured / agreed): `polymarket-copy-bot/`

### Simulation (Phase 1a)
- `polymarket-copy-bot/simulation/<run_id>/replay_summary.json`
- `polymarket-copy-bot/simulation/<run_id>/manifest.json`

### Recorder (Phase 1b) *(future / optional)*
- `polymarket-copy-bot/recorder/<run_id>/events.jsonl`
- `polymarket-copy-bot/recorder/<run_id>/manifest.json`

### Optional future
- `polymarket-copy-bot/logs/<run_id>/...`

---

## run_id standard
For Phase 1, we use:
- `replay-<unix_ts>`

In later phases we can extend this to:
- include ISO8601 timestamps
- include a short git SHA suffix
- include a strategy name or market scope

---

## manifest.json schema (v1)

A `manifest.json` is written per run to enable:
- traceability (what ran, when)
- reproducibility (which git SHA)
- automation (where artifacts are stored)

### Fields
- `schema_version` (int): currently `1`
- `service` (string): e.g. `simulation`
- `run_id` (string)
- `started_at` (float epoch seconds)
- `ended_at` (float epoch seconds)
- `duration_s` (float)
- `git_sha` (string): best-effort (env or `git rev-parse`)
- `config` (object): **non-sensitive** snapshot of runtime config
- `artifacts` (object map): logical name → object key/path

### Example
```json
{
  "schema_version": 1,
  "service": "simulation",
  "run_id": "replay-1700000000",
  "started_at": 1700000000.1,
  "ended_at": 1700000002.3,
  "duration_s": 2.2,
  "git_sha": "abc123...",
  "config": {
    "CLOUD_BACKEND": "local",
    "OBJECT_STORE_BACKEND": "s3",
    "AWS_REGION": "us-east-1",
    "S3_OBJECT_BUCKET": "polymarket-copy-bot-objects-dev-137097287791",
    "S3_OBJECT_PREFIX": "polymarket-copy-bot"
  },
  "artifacts": {
    "replay_summary": "polymarket-copy-bot/simulation/replay-1700000000/replay_summary.json",
    "manifest": "polymarket-copy-bot/simulation/replay-1700000000/manifest.json",
    "local_summary_path": "simulation_results/replay_summary.json"
  }
}