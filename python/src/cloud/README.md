# Cloud Boundary (Phase-safe)

This folder defines the **cloud boundary** for the Polymarket bot.

## Goal
- Phase 1a/1b must remain **cloud-agnostic**.
- No AWS SDK imports.
- No provisioning.
- Services depend on **interfaces**, not AWS implementations.

## Interfaces
- `EventPublisher` — publish structured events
- `ObjectStore` — store blobs / artifacts
- `SecretProvider` — fetch config/secrets
- `CloudServices` — container for the above

## Phase usage
- Phase 1: only **local** implementations (filesystem, stdout, env)
- Phase 2+: add `aws.py` implementations (SQS/S3/Secrets Manager) without changing service logic
