from __future__ import annotations

import os

# Backends: "local" now; "aws" later
CLOUD_BACKEND = os.getenv("CLOUD_BACKEND", "local").strip().lower()

# Where local events get written (jsonl)
LOCAL_EVENT_DIR = os.getenv("LOCAL_EVENT_DIR", "logs/cloud_events").strip()

# Where local objects are stored
LOCAL_OBJECT_DIR = os.getenv("LOCAL_OBJECT_DIR", "simulation_results/objects").strip()
