"""
PR21/PR22: Interactive Dashboard (Streamlit)

Read-only dashboard for Phase 1/2 artifacts:
- Local files (Phase 1 dev)
- S3 artifacts later (Phase 2+)

Includes:
- Artifact previews (simulation manifest + replay summary)
- Recorder event table (JSONL)
- Candlestick-style chart from trade_detected payload.price (best-effort)
- Phase-1 safe metrics (event-derived)
- Trade metrics
- PR22 Metrics Store tab (canonical metrics.jsonl)
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


APP_TITLE = "Polymarket Copy Bot Dashboard (Phase 1/2)"


# ============================================================
# -------------------- TIME HELPERS ---------------------------
# ============================================================

def _to_dt_utc(ts: float) -> datetime:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


def _ts_to_iso(ts: Optional[float]) -> str:
    if ts is None:
        return "n/a"
    try:
        return datetime.fromtimestamp(float(ts)).isoformat()
    except Exception:
        return "unknown"


# ============================================================
# -------------------- EVENT HELPERS --------------------------
# ============================================================

def _get_event_ts(ev: Dict[str, Any]) -> Optional[float]:
    ts = ev.get("timestamp")
    try:
        return float(ts) if ts is not None else None
    except Exception:
        return None


def _get_market_id(ev: Dict[str, Any]) -> str:
    return str(ev.get("market_id") or "unknown")


def _get_event_type(ev: Dict[str, Any]) -> str:
    return str(ev.get("type") or "unknown")


def _safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _get_trade_price(ev: Dict[str, Any]) -> Optional[float]:
    payload = ev.get("payload") or {}
    if not isinstance(payload, dict):
        return None
    return _safe_float(payload.get("price"))


# ============================================================
# -------------------- IO HELPERS -----------------------------
# ============================================================

def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path, max_lines: Optional[int] = None) -> List[dict]:
    out: List[dict] = []
    if not path.exists():
        return out

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
            if max_lines is not None and len(out) >= max_lines:
                break
    return out


# -------------------- PR22 Metrics Store --------------------

def _metrics_df(metrics: List[dict]) -> pd.DataFrame:
    if not metrics:
        return pd.DataFrame()

    rows: List[Dict[str, Any]] = []

    for m in metrics:
        dims = m.get("dimensions") or {}
        if not isinstance(dims, dict):
            dims = {}

        ts = m.get("ts")
        try:
            ts_f = float(ts) if ts is not None else None
        except Exception:
            ts_f = None

        row: Dict[str, Any] = {
            "schema_version": m.get("schema_version"),
            "metric_name": m.get("metric_name"),
            "metric_type": m.get("metric_type"),
            "value": m.get("value"),
            "ts": ts_f,
            "dt": datetime.fromtimestamp(ts_f) if ts_f is not None else None,
        }

        for k, v in dims.items():
            row[f"dim_{k}"] = v

        rows.append(row)

    df = pd.DataFrame(rows)
    if "dt" in df.columns:
        df = df.sort_values("dt")
    return df


# ============================================================
# -------------------- FILTERING ------------------------------
# ============================================================

@dataclass(frozen=True)
class GlobalFilters:
    market_id: str
    ts_start: float
    ts_end: float


def _apply_global_filters(events: List[dict], gf: GlobalFilters) -> List[dict]:
    out: List[dict] = []
    for ev in events:
        ts = _get_event_ts(ev)
        if ts is None:
            continue
        if ts < gf.ts_start or ts > gf.ts_end:
            continue
        if gf.market_id != "(all)" and _get_market_id(ev) != gf.market_id:
            continue
        out.append(ev)
    return out


# ============================================================
# -------------------- CANDLESTICKS ---------------------------
# ============================================================

def _trade_points(events: List[dict]) -> pd.DataFrame:
    rows = []
    for ev in events:
        if _get_event_type(ev) != "trade_detected":
            continue
        ts = _get_event_ts(ev)
        price = _get_trade_price(ev)
        if ts is None or price is None:
            continue
        rows.append({
            "dt": datetime.fromtimestamp(ts),
            "price": price,
            "market_id": _get_market_id(ev),
        })

    if not rows:
        return pd.DataFrame(columns=["dt", "price", "market_id"])

    return pd.DataFrame(rows).sort_values("dt")


def _make_candles(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    tmp = df.set_index("dt")[["price"]]
    return tmp["price"].resample(interval).ohlc().dropna()


def _plot_candles(ohlc: pd.DataFrame) -> go.Figure:
    fig = go.Figure(data=[
        go.Candlestick(
            x=ohlc.index,
            open=ohlc["open"],
            high=ohlc["high"],
            low=ohlc["low"],
            close=ohlc["close"],
        )
    ])
    fig.update_layout(height=420)
    return fig


# ============================================================
# -------------------- MAIN APP -------------------------------
# ============================================================

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    # ---------------- Sidebar ----------------
    st.sidebar.header("Paths")

    manifest_path = Path(st.sidebar.text_input(
        "Simulation manifest path",
        "python/simulation_results/manifest.json",
    ))

    summary_path = Path(st.sidebar.text_input(
        "Simulation summary path",
        "python/simulation_results/replay_summary.json",
    ))

    events_path = Path(st.sidebar.text_input(
        "Recorder events path",
        "python/recorder_data/events.jsonl",
    ))

    metrics_path = Path(st.sidebar.text_input(
        "Metrics store path",
        "python/metrics_results/metrics.jsonl",
    ))

    max_events = st.sidebar.slider("Max recorder events", 50, 5000, 500)
    max_metrics = st.sidebar.slider("Max metrics rows", 100, 20000, 2000)

    recorder_events = _read_jsonl(events_path, max_events)
    metrics_rows = _read_jsonl(metrics_path, max_metrics)
    df_metrics = _metrics_df(metrics_rows)

    # ---------------- Tabs ----------------
    tabs = st.tabs([
        "Replay Summary",
        "Recorder Events",
        "Candlestick",
        "Metrics (Events)",
        "Metrics Store (PR22)",
    ])

    # =========================================================
    # Replay Summary
    # =========================================================
    with tabs[0]:
        if summary_path.exists():
            st.json(_read_json(summary_path))
        else:
            st.info("Replay summary not found.")

    # =========================================================
    # Recorder Events
    # =========================================================
    with tabs[1]:
        st.write(f"Loaded {len(recorder_events)} event(s)")
        st.dataframe(pd.DataFrame(recorder_events).head(200))

    # =========================================================
    # Candlestick
    # =========================================================
    with tabs[2]:
        df_trades = _trade_points(recorder_events)
        if df_trades.empty:
            st.info("No trade_detected events.")
        else:
            interval = st.selectbox("Interval", ["1min", "5min", "15min", "1h"], index=1)
            interval_map = {
                "1min": "1min",
                "5min": "5min",
                "15min": "15min",
                "1h": "1h",
            }
            ohlc = _make_candles(df_trades, interval_map[interval])
            if not ohlc.empty:
                st.plotly_chart(_plot_candles(ohlc), use_container_width=True)
            else:
                st.warning("Not enough data for candles.")

    # =========================================================
    # Event-Derived Metrics
    # =========================================================
    with tabs[3]:
        st.write("Event-derived metrics")
        st.write(f"Total events: {len(recorder_events)}")

    # =========================================================
    # PR22 Metrics Store
    # =========================================================
    with tabs[4]:
        st.caption("Canonical metric artifacts (metrics_results/metrics.jsonl)")

        if df_metrics.empty:
            st.info("No metrics loaded.")
        else:
            st.success(f"Loaded {len(df_metrics)} metric rows")

            services = sorted(df_metrics["dim_service"].dropna().unique())
            runs = sorted(df_metrics["dim_run_id"].dropna().unique())
            names = sorted(df_metrics["metric_name"].dropna().unique())

            c1, c2, c3 = st.columns(3)
            svc = c1.selectbox("Service", ["(all)"] + services)
            run = c2.selectbox("Run ID", ["(all)"] + runs)
            name = c3.selectbox("Metric", ["(all)"] + names)

            view = df_metrics.copy()
            if svc != "(all)":
                view = view[view["dim_service"] == svc]
            if run != "(all)":
                view = view[view["dim_run_id"] == run]
            if name != "(all)":
                view = view[view["metric_name"] == name]

            st.dataframe(view.tail(500), use_container_width=True)

            if not view.empty:
                st.subheader("Timeseries")
                metric_pick = st.selectbox(
                    "Metric timeseries",
                    sorted(view["metric_name"].unique()),
                )
                ts_df = view[view["metric_name"] == metric_pick].dropna(subset=["dt"])
                if not ts_df.empty:
                    st.line_chart(ts_df.set_index("dt")["value"])


if __name__ == "__main__":
    main()