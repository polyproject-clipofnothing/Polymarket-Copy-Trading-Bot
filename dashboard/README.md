# PR21 --- Streamlit Dashboard (Phase 1/2)

Read-only dashboard for exploring Phase 1/2 artifacts.

------------------------------------------------------------------------

## Overview

This dashboard provides a real-time and historical visualization layer
for Phase 1 & Phase 2 data.

It enables:

-   Visualization of recorder, simulation, and strategy outputs
-   Exploratory analysis for strategy development
-   Early observability without requiring production-grade
    infrastructure
-   A clean upgrade path to Athena/Timestream/Postgres +
    Grafana/Superset later

------------------------------------------------------------------------

## Current Features (Phase 1 Safe)

### Artifact Previews

-   `python/simulation_results/manifest.json`
-   `python/simulation_results/replay_summary.json`

### Recorder Data

-   `python/recorder_data/events.jsonl`
-   Filterable by:
    -   `market_id`
    -   time range (UNIX timestamp)
    -   event type

### Candlestick Chart

-   Built from `trade_detected` events
-   Uses `payload.price`
-   Supports configurable intervals:
    -   1min
    -   5min
    -   15min
    -   1h
    -   4h
    -   1d

### Phase-1 Metrics

-   Total events loaded
-   Range start / end
-   Throughput (events/sec)
-   Events by type
-   Throughput over time
-   Market distribution (trade_detected)
-   Price distribution (trade_detected.payload.price)

------------------------------------------------------------------------

## How to Run

From the repository root:

``` bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

------------------------------------------------------------------------

## Generate Phase 1 Data

From the repository root:

``` bash
cd python
python3 -m scripts.run_recorder
python3 -m scripts.run_simulation
```

Then return to root and launch dashboard:

``` bash
cd ..
streamlit run dashboard/app.py
```

------------------------------------------------------------------------

## Architecture Notes

-   Read-only dashboard (no execution, no writes)
-   Local-first artifact loading
-   Designed to support S3 artifact loading in Phase 2+
-   Metrics layer designed to map cleanly to:
    -   Athena
    -   Timestream
    -   Postgres
    -   Grafana / Superset

------------------------------------------------------------------------

## Upgrade Path (Planned)

-   S3 artifact loading via manifest keys
-   Strategy artifact visualizations
-   Latency breakdown metrics (p50 / p95 / p99)
-   Slippage + fill-rate metrics
-   Live execution monitoring
-   Cost per trade
-   Strategy performance overlays

------------------------------------------------------------------------

## Status

Phase: PR21\
Scope: Interactive Dashboard (Streamlit)\
Data Safety: Phase 1 / Phase 2 read-only\
Production Impact: None
Im