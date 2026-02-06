from __future__ import annotations

import time
from typing import Dict, Iterator, Optional

import httpx

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"


def _fetch_markets(
    client: httpx.Client,
    limit: int,
    offset: int,
) -> list[Dict]:
    # Gamma markets endpoint is public/read-only
    # https://gamma-api.polymarket.com/markets
    resp = client.get(
        f"{GAMMA_BASE_URL}/markets",
        params={"limit": limit, "offset": offset},
        timeout=20.0,
    )
    resp.raise_for_status()
    data = resp.json()

    # Gamma returns a list of markets; some clients wrap in {"markets": ...}
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "markets" in data and isinstance(data["markets"], list):
        return data["markets"]
    raise ValueError("Unexpected Gamma /markets response shape")


def poll_events(
    *,
    interval_seconds: float = 15.0,
    page_limit: int = 50,
    max_pages: int = 1,
) -> Iterator[Dict]:
    """
    Phase 1b Polymarket public recorder poller.
    Emits market snapshots via Gamma API (no auth).

    Yields raw events (pre-normalization) that will be normalized by normalizer.py
    into your canonical event format.
    """
    headers = {
        "User-Agent": "polymarket-recorder/phase1b",
        "Accept": "application/json",
    }

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        while True:
            ts = time.time()

            # Fetch first N pages of markets (kept intentionally small for Phase 1)
            for page in range(max_pages):
                offset = page * page_limit
                markets = _fetch_markets(client, limit=page_limit, offset=offset)

                yield {
                    "source": "polymarket",
                    "event_type": "market_snapshot",
                    "timestamp": ts,
                    "raw": {
                        "page": page,
                        "limit": page_limit,
                        "offset": offset,
                        "markets": markets,
                    },
                }

            time.sleep(interval_seconds)
