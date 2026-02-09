from __future__ import annotations

import os


# Backends: "local" now; "aws" later (Phase 2+)
CLOUD_BACKEND = os.getenv("CLOUD_BACKEND", "local").strip().lower()

# Where local events get written (jsonl)
LOCAL_EVENT_DIR = os.getenv("LOCAL_EVENT_DIR", "logs/cloud_events").strip()

# Where local objects are stored
LOCAL_OBJECT_DIR = os.getenv("LOCAL_OBJECT_DIR", "simulation_results/objects").strip()

# Object store backend: local (default) or s3 (opt-in)
OBJECT_STORE_BACKEND = os.getenv("OBJECT_STORE_BACKEND", "local").strip().lower()

# S3 object store config (only used when OBJECT_STORE_BACKEND=s3)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1").strip()
S3_OBJECT_BUCKET = os.getenv("S3_OBJECT_BUCKET", "").strip()
S3_OBJECT_PREFIX = os.getenv("S3_OBJECT_PREFIX", "polymarket-copy-bot").strip().strip("/")
