# Runtime Config Validation (PR18)

## Goal

Fail fast with **clear, actionable errors** when runtime configuration is missing
or invalid — especially when using S3 as the ObjectStore backend.

This prevents confusing runtime failures such as:

- `NoSuchBucket`
- `AccessDenied`
- `NoneType` attribute errors
- Silent misconfiguration (writing to the wrong backend)

All services validate configuration **before doing any work** and exit with a
**non-zero status code** on failure.

---

## Phase 1 supported values

### CLOUD_BACKEND

Phase 1 **allowed value**:

- `CLOUD_BACKEND=local` (default)

Behavior:
- If unset → defaults to `local`
- If set to anything else → service exits immediately with a clear error

Example failure:
```bash
export CLOUD_BACKEND=aws
python3 -m scripts.run_simulation


[Config] CLOUD_BACKEND='aws' is not supported yet. Use CLOUD_BACKEND=local.