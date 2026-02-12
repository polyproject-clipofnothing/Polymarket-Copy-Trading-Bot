"""
PR21: Interactive Dashboard (Streamlit)

Read-only dashboard for Phase 1/2 artifacts:
- Local files (Phase 1 dev)
- S3 artifacts later (Phase 2+)

Includes:
- Artifact previews (simulation manifest + replay summary)
- Recorder event table (JSONL)
- Candlestick-style chart from trade_detected payload.price (best-effort)
- Phase-1 safe metrics: events by type, throughput, throughput over time
- Trade metrics: trade frequency, market distribution, price distribution

Global sidebar filters:
- Market (market_id)
- Time range (timestamp window)
Applied across ALL tabs & metrics.
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


# -------------------------
# Time / field helpers
# -------------------------
def _to_dt_utc(ts: float) -> datetime:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


def _ts_to_iso(ts: Optional[float]) -> str:
    if ts is None:
        return "n/a"
    try:
        return datetime.fromtimestamp(float(ts)).isoformat()
    except Exception:
        return "unknown"


def _get_event_ts(ev: Dict[str, Any]) -> Optional[float]:
    """
    Recorder event timestamp lives at top-level "timestamp" in your schema.
    """
    ts = ev.get("timestamp")
    try:
        return float(ts) if ts is not None else None
    except Exception:
        return None


def _get_market_id(ev: Dict[str, Any]) -> str:
    v = ev.get("market_id")
    return str(v) if v is not None else "unknown"


def _get_event_type(ev: Dict[str, Any]) -> str:
    t = ev.get("type")
    return str(t) if t is not None else "unknown"


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


# -------------------------
# IO helpers
# -------------------------
def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path, max_events: Optional[int] = None) -> List[dict]:
    """
    Read JSONL into a list[dict]. Best-effort: skips bad lines.
    If max_events is set, loads up to that many lines (from the start).
    """
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
            if max_events is not None and len(out) >= max_events:
                break
    return out


# -------------------------
# Filtering
# -------------------------
@dataclass(frozen=True)
class GlobalFilters:
    market_id: str  # "(all)" or a specific market_id
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

        if gf.market_id != "(all)":
            if _get_market_id(ev) != gf.market_id:
                continue

        out.append(ev)
    return out


# -------------------------
# Candles
# -------------------------
def _trade_points(events: List[dict]) -> pd.DataFrame:
    """
    Build a DataFrame of trade points from recorder trade_detected events:
    - dt (datetime)
    - ts (float)
    - price (float) from payload.price
    - market_id
    """
    rows: List[Dict[str, Any]] = []
    for ev in events:
        if _get_event_type(ev) != "trade_detected":
            continue
        ts = _get_event_ts(ev)
        if ts is None:
            continue
        price = _get_trade_price(ev)
        if price is None:
            continue
        rows.append(
            {
                "ts": float(ts),
                "dt": datetime.fromtimestamp(float(ts)),
                "price": float(price),
                "market_id": _get_market_id(ev),
            }
        )

    if not rows:
        return pd.DataFrame(columns=["ts", "dt", "price", "market_id"])
    return pd.DataFrame(rows).sort_values("dt")


def _make_candles(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    interval: "1min" | "5min" | "15min" | "1h" | "4h" | "1D"
    Returns OHLC DataFrame indexed by dt bucket.
    """
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close"])

    tmp = df.set_index("dt")[["price"]].sort_index()
    ohlc = tmp["price"].resample(interval).ohlc().dropna()
    return ohlc


def _plot_candles(ohlc: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=ohlc.index,
                open=ohlc["open"],
                high=ohlc["high"],
                low=ohlc["low"],
                close=ohlc["close"],
            )
        ]
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def _plot_scatter(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(data=[go.Scatter(x=df["dt"], y=df["price"], mode="markers")])
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    return fig


# -------------------------
# Metrics (Phase 1 safe)
# -------------------------
def _events_by_type(events: List[dict]) -> pd.DataFrame:
    counts: Dict[str, int] = {}
    for ev in events:
        t = _get_event_type(ev)
        counts[t] = counts.get(t, 0) + 1
    df = pd.DataFrame([{"type": k, "count": v} for k, v in counts.items()])
    if df.empty:
        return pd.DataFrame(columns=["type", "count"])
    return df.sort_values("count", ascending=False)


def _throughput(events: List[dict]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Returns: (ts_min, ts_max, events_per_sec) using the filtered window.
    """
    if not events:
        return None, None, None

    tss = [t for t in (_get_event_ts(e) for e in events) if t is not None]
    if not tss:
        return None, None, None

    ts_min = float(min(tss))
    ts_max = float(max(tss))
    span = max(0.000001, ts_max - ts_min)
    eps = len(tss) / span
    return ts_min, ts_max, eps


def _throughput_over_time(events: List[dict], bucket_s: int) -> pd.DataFrame:
    if not events:
        return pd.DataFrame(columns=["dt", "count"])

    rows = []
    for ev in events:
        ts = _get_event_ts(ev)
        if ts is None:
            continue
        rows.append({"dt": datetime.fromtimestamp(float(ts))})

    if not rows:
        return pd.DataFrame(columns=["dt", "count"])

    df = pd.DataFrame(rows).set_index("dt")
    series = df.resample(f"{bucket_s}S").size()
    out = series.reset_index().rename(columns={0: "count"})
    return out


# -------------------------
# Trade metrics (Phase 1 safe)
# -------------------------
def _bucket_seconds(bucket_label: str) -> int:
    m = {
        "1min": 60,
        "5min": 300,
        "15min": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    return m.get(bucket_label, 300)


def _bucket_start(ts: float, bucket_s: int) -> float:
    ts = float(ts)
    return ts - (ts % bucket_s)


def _render_trade_frequency(events: List[dict], bucket_label: str) -> None:
    trades = [e for e in events if _get_event_type(e) == "trade_detected"]
    if not trades:
        st.info("No trade_detected events in the current filter range.")
        return

    bucket_s = _bucket_seconds(bucket_label)
    buckets: Dict[float, int] = {}

    for e in trades:
        ts = _get_event_ts(e)
        if ts is None:
            continue
        b = _bucket_start(ts, bucket_s)
        buckets[b] = buckets.get(b, 0) + 1

    if not buckets:
        st.info("No usable timestamps for trade_detected events.")
        return

    xs = sorted(buckets.keys())
    ys = [buckets[x] for x in xs]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[_to_dt_utc(x) for x in xs], y=ys, mode="lines+markers"))
    fig.update_layout(
        title="Trade frequency over time (trade_detected)",
        xaxis_title="Time (UTC)",
        yaxis_title=f"Trades per {bucket_label}",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_market_distribution(events: List[dict], top_n: int = 15) -> None:
    trades = [e for e in events if _get_event_type(e) == "trade_detected"]
    if not trades:
        st.info("No trade_detected events available for market distribution.")
        return

    counts = Counter(_get_market_id(e) for e in trades)
    if not counts:
        st.info("No usable market_id values found.")
        return

    items = counts.most_common(top_n)
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    total = sum(counts.values())
    pct = [round((v / total) * 100, 2) if total else 0 for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=values, text=[f"{p}%" for p in pct], textposition="auto"))
    fig.update_layout(
        title=f"Market distribution (top {top_n}) — trade_detected",
        xaxis_title="market_id",
        yaxis_title="trade_detected count",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_price_distribution(events: List[dict], bins: int = 30) -> None:
    trades = [e for e in events if _get_event_type(e) == "trade_detected"]
    prices = [p for p in (_get_trade_price(e) for e in trades) if p is not None]

    if not prices:
        st.info("No usable payload.price values found for trade_detected events.")
        return

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=prices, nbinsx=int(bins)))
    fig.update_layout(
        title="Price distribution — trade_detected payload.price",
        xaxis_title="price",
        yaxis_title="count",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# -------------------------
# App
# -------------------------
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Read-only dashboard. Loads artifacts from local files now, and will support S3 artifacts later.")

    # ---------------- Sidebar: source & paths ----------------
    st.sidebar.header("Data Source")
    source = st.sidebar.selectbox("Source", ["Local"], index=0)

    st.sidebar.header("Paths")
    default_manifest = "python/simulation_results/manifest.json"
    default_summary = "python/simulation_results/replay_summary.json"
    default_events = "python/recorder_data/events.jsonl"

    manifest_path_str = st.sidebar.text_input("Simulation manifest path", default_manifest)
    summary_path_str = st.sidebar.text_input("Simulation summary path", default_summary)

    st.sidebar.header("Recorder")
    events_path_str = st.sidebar.text_input("Recorder events path (.jsonl)", default_events)
    max_events = int(st.sidebar.slider("Max recorder events to load", 50, 5000, 500, step=50))

    manifest_path = Path(manifest_path_str)
    summary_path = Path(summary_path_str)
    events_path = Path(events_path_str)

    manifest_ok = manifest_path.exists()
    summary_ok = summary_path.exists()
    events_ok = events_path.exists()

    # Load events once
    recorder_events: List[dict] = _read_jsonl(events_path, max_events=max_events) if events_ok else []

    # ---------------- Sidebar: GLOBAL filters ----------------
    st.sidebar.header("Global Filters")

    markets = sorted({_get_market_id(e) for e in recorder_events} or {"unknown"})
    market_choice = st.sidebar.selectbox("Market (market_id)", ["(all)"] + markets, index=0)

    ts_list = [t for t in (_get_event_ts(e) for e in recorder_events) if t is not None]
    if ts_list:
        ts_min = float(min(ts_list))
        ts_max = float(max(ts_list))
        ts_start_i, ts_end_i = st.sidebar.slider(
            "Time range (unix seconds)",
            min_value=int(ts_min),
            max_value=int(ts_max),
            value=(int(ts_min), int(ts_max)),
        )
        gf = GlobalFilters(market_id=market_choice, ts_start=float(ts_start_i), ts_end=float(ts_end_i))
        st.sidebar.caption(f"Start: `{_ts_to_iso(gf.ts_start)}`")
        st.sidebar.caption(f"End:   `{_ts_to_iso(gf.ts_end)}`")
    else:
        now = datetime.now().timestamp()
        gf = GlobalFilters(market_id=market_choice, ts_start=now - 3600, ts_end=now)

    filtered_events = _apply_global_filters(recorder_events, gf)

    # ---------------- Layout ----------------
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("Status")
        st.write(f"Source: **{source}**")
        st.write(f"Manifest: `{manifest_path}` → {'✅ found' if manifest_ok else '❌ missing'}")
        st.write(f"Summary: `{summary_path}` → {'✅ found' if summary_ok else '❌ missing'}")
        st.write(f"Recorder events: `{events_path}` → {'✅ found' if events_ok else '❌ missing'}")

        st.divider()
        st.subheader("Quick Tips")
        st.code("cd python\npython3 -m scripts.run_simulation\npython3 -m scripts.run_recorder", language="bash")
        st.code("streamlit run dashboard/app.py", language="bash")

    with col_right:
        st.subheader("Artifacts Preview")
        tabs = st.tabs(["Replay Summary", "Recorder Events", "Candlestick Chart", "Metrics"])

        # --- Replay Summary ---
        with tabs[0]:
            if summary_ok:
                st.json(_read_json(summary_path))
            else:
                st.info("Replay summary not found yet. Run simulation first.")

        # --- Recorder Events (filtered) ---
        with tabs[1]:
            st.caption("Loads JSONL records from recorder output. Global filters apply (market + time range).")

            if not events_ok:
                st.info("Recorder events not found yet. Run recorder first.")
            else:
                st.success(f"Loaded {len(recorder_events)} event(s); showing {len(filtered_events)} after filters.")

                types = sorted({_get_event_type(e) for e in filtered_events} or {"unknown"})
                type_choice = st.selectbox("Filter by event type", ["(all)"] + types, index=0)

                view = filtered_events
                if type_choice != "(all)":
                    view = [e for e in filtered_events if _get_event_type(e) == type_choice]

                if view:
                    rows = []
                    for e in view[:200]:
                        rows.append(
                            {
                                "version": e.get("version"),
                                "source": e.get("source"),
                                "type": _get_event_type(e),
                                "market_id": _get_market_id(e),
                                "timestamp": _get_event_ts(e),
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=320)

                    with st.expander("Raw JSON preview (first 3)"):
                        for e in view[:3]:
                            st.json(e)
                else:
                    st.warning("No events match the current filters.")

        # --- Candlestick (filtered) ---
        with tabs[2]:
            st.caption("Candlestick-style view built from recorder trade_detected events (payload.price).")

            if not filtered_events:
                st.info("No events after filters. Adjust market/time range.")
            else:
                if gf.market_id == "(all)":
                    market_for_candles = st.selectbox("Market for candles", markets, index=0 if markets else 0)
                    candle_events = [e for e in filtered_events if _get_market_id(e) == market_for_candles]
                else:
                    market_for_candles = gf.market_id
                    candle_events = filtered_events

                df_trades = _trade_points(candle_events)

                st.write(f"Market: `{market_for_candles}`")
                st.write(f"Trades in window: **{len(df_trades)}**")

                interval_map = {
                    "1min": "1min",
                    "5min": "5min",
                    "15min": "15min",
                    "1h": "1h",
                    "4h": "4h",
                    "1d": "1D",
                }
                interval_choice = st.selectbox("Candle interval", list(interval_map.keys()), index=3)

                if df_trades.empty:
                    st.warning("No usable price points (trade_detected payload.price) for the selected range.")
                else:
                    ohlc = _make_candles(df_trades, interval_map[interval_choice])

                    if len(ohlc) >= 2:
                        st.plotly_chart(_plot_candles(ohlc), use_container_width=True)
                        st.caption(f"Built {len(ohlc)} candle(s) from {len(df_trades)} trade(s).")
                    else:
                        st.warning("Not enough buckets to build candles yet — showing scatter fallback.")
                        st.plotly_chart(_plot_scatter(df_trades), use_container_width=True)

        # --- Metrics (filtered) ---
        with tabs[3]:
            st.caption("Phase-1 safe metrics from recorder events. Global filters apply.")

            if not filtered_events:
                st.info("No events after filters. Adjust market/time range.")
            else:
                ts_min, ts_max, eps = _throughput(filtered_events)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Events loaded", f"{len(filtered_events)}")
                m2.metric("Range start", _ts_to_iso(ts_min))
                m3.metric("Range end", _ts_to_iso(ts_max))
                m4.metric("Throughput (events/sec)", f"{(eps or 0):.4f}")

                st.subheader("Events by type")
                df_types = _events_by_type(filtered_events)
                if df_types.empty:
                    st.info("No events to summarize.")
                else:
                    st.bar_chart(df_types.set_index("type")["count"])

                st.subheader("Throughput over time")
                bucket_choice = st.selectbox("Bucket", ["5min", "15min", "1h"], index=0)
                bucket_s = {"5min": 300, "15min": 900, "1h": 3600}[bucket_choice]
                df_tp = _throughput_over_time(filtered_events, bucket_s=bucket_s)
                if df_tp.empty:
                    st.info("No events to chart.")
                else:
                    st.line_chart(df_tp.set_index("dt")["count"])

                # --------------------------
                # Step 3: Trade Metrics panel
                # --------------------------
                st.divider()
                st.subheader("Trade metrics (Phase 1 safe)")

                freq_bucket = st.selectbox(
                    "Trade frequency bucket",
                    ["1min", "5min", "15min", "1h", "4h", "1d"],
                    index=1,
                )
                _render_trade_frequency(filtered_events, bucket_label=freq_bucket)

                st.divider()
                st.subheader("Market distribution (trade_detected)")
                _render_market_distribution(filtered_events, top_n=15)

                st.divider()
                st.subheader("Price distribution (trade_detected payload.price)")
                bins = st.slider("Histogram bins", min_value=10, max_value=80, value=30, step=5)
                _render_price_distribution(filtered_events, bins=bins)

    st.divider()
    st.subheader("Coming Next")
    st.write(
        "- Trader activity timelines\n"
        "- More filters (event type, side, price ranges)\n"
        "- S3 artifact loading (Phase 2+)\n"
        "- Upgrade path: Athena/Timestream/Postgres + Grafana/Superset"
    )


if __name__ == "__main__":
    main()