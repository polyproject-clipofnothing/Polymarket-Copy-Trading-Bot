"""
Trade executor service - executes trades based on monitored activity

PHASE SAFETY:
- This module is NOT allowed to run in Phase 1 (Recorder/Simulation) or Phase 2 (Strategy).
- Importing it should also fail fast unless explicitly enabled.

To enable (Phase 4+ only):
  export ENABLE_TRADING=true
  export APP_PHASE=4   # optional but recommended
"""

from __future__ import annotations

import os

# -----------------------------
# Phase / Trading safety gate
# -----------------------------
def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


ENABLE_TRADING = _env_bool("ENABLE_TRADING", "false")

# Optional: enforce an explicit phase number (recommended)
# Phase definitions (your project convention):
#   1 = recorder/simulation
#   2 = strategy
#   3 = dry-run execution
#   4 = live execution (ONLY here)
APP_PHASE = _env_str("APP_PHASE", "")

if not ENABLE_TRADING:
    raise RuntimeError(
        "trade_executor is DISABLED for Phase 1/2/3 safety.\n"
        "This module must not be imported or executed until Phase 4+.\n"
        "To enable (Phase 4+ only):\n"
        "  export ENABLE_TRADING=true\n"
        "  export APP_PHASE=4   # recommended\n"
    )

if APP_PHASE and APP_PHASE != "4":
    raise RuntimeError(
        f"trade_executor blocked: APP_PHASE={APP_PHASE!r}.\n"
        "This module is only allowed when APP_PHASE=4.\n"
        "Set:\n"
        "  export APP_PHASE=4\n"
    )

# -----------------------------
# Real implementation below
# (unchanged from your original)
# -----------------------------

import asyncio
import time
from typing import List, Dict, Any

from ...config.env import ENV
from ...models.user_history import get_user_activity_collection
from ...interfaces.user import UserActivityInterface, UserPositionInterface
from ...utils.fetch_data import fetch_data_async
from ...utils.get_my_balance import get_my_balance_async
from ...utils.post_order import post_order
from ...utils.logger import (
    success,
    info,
    warning,
    header,
    waiting,
    clear_line,
    separator,
    trade as log_trade,
    balance as log_balance,
)

USER_ADDRESSES = ENV.USER_ADDRESSES
RETRY_LIMIT = ENV.RETRY_LIMIT
PROXY_WALLET = ENV.PROXY_WALLET
TRADE_AGGREGATION_ENABLED = ENV.TRADE_AGGREGATION_ENABLED
TRADE_AGGREGATION_WINDOW_SECONDS = ENV.TRADE_AGGREGATION_WINDOW_SECONDS
TRADE_AGGREGATION_MIN_TOTAL_USD = 1.0  # Polymarket minimum

is_running = True

TradeWithUser = Dict[str, Any]
AggregatedTrade = Dict[str, Any]

trade_aggregation_buffer: Dict[str, AggregatedTrade] = {}


async def read_temp_trades() -> List[TradeWithUser]:
    """Read unprocessed trades from database"""
    all_trades: List[TradeWithUser] = []

    for address in USER_ADDRESSES:
        collection = get_user_activity_collection(address)
        trades = list(
            collection.find(
                {
                    "type": "TRADE",
                    "bot": False,
                    "botExcutedTime": 0,
                }
            )
        )

        for trade in trades:
            trade["userAddress"] = address
            all_trades.append(trade)

    return all_trades


def get_aggregation_key(trade: TradeWithUser) -> str:
    """Generate a unique key for trade aggregation based on user, market, side"""
    return (
        f"{trade['userAddress']}:{trade.get('conditionId', '')}:"
        f"{trade.get('asset', '')}:{trade.get('side', 'BUY')}"
    )


def add_to_aggregation_buffer(trade: TradeWithUser) -> None:
    """Add trade to aggregation buffer or update existing aggregation"""
    key = get_aggregation_key(trade)
    existing = trade_aggregation_buffer.get(key)
    now = int(time.time() * 1000)  # milliseconds

    if existing:
        existing["trades"].append(trade)
        existing["totalUsdcSize"] += trade.get("usdcSize", 0)

        total_value = sum(
            t.get("usdcSize", 0) * t.get("price", 0) for t in existing["trades"]
        )
        existing["averagePrice"] = (
            total_value / existing["totalUsdcSize"]
            if existing["totalUsdcSize"] > 0
            else 0
        )
        existing["lastTradeTime"] = now
    else:
        trade_aggregation_buffer[key] = {
            "userAddress": trade["userAddress"],
            "conditionId": trade.get("conditionId", ""),
            "asset": trade.get("asset", ""),
            "side": trade.get("side", "BUY"),
            "slug": trade.get("slug"),
            "eventSlug": trade.get("eventSlug"),
            "trades": [trade],
            "totalUsdcSize": trade.get("usdcSize", 0),
            "averagePrice": trade.get("price", 0),
            "firstTradeTime": now,
            "lastTradeTime": now,
        }


def get_ready_aggregated_trades() -> List[AggregatedTrade]:
    """Check buffer and return ready aggregated trades"""
    ready: List[AggregatedTrade] = []
    now = int(time.time() * 1000)
    window_ms = TRADE_AGGREGATION_WINDOW_SECONDS * 1000

    keys_to_remove = []

    for key, agg in trade_aggregation_buffer.items():
        time_elapsed = now - agg["firstTradeTime"]

        if time_elapsed >= window_ms:
            if agg["totalUsdcSize"] >= TRADE_AGGREGATION_MIN_TOTAL_USD:
                ready.append(agg)
            else:
                info(
                    f"Trade aggregation for {agg['userAddress']} on "
                    f"{agg.get('slug') or agg.get('asset', 'unknown')}: "
                    f"${agg['totalUsdcSize']:.2f} total from {len(agg['trades'])} "
                    f"trades below minimum (${TRADE_AGGREGATION_MIN_TOTAL_USD}) - skipping"
                )

                for trade in agg["trades"]:
                    collection = get_user_activity_collection(trade["userAddress"])
                    collection.update_one({"_id": trade["_id"]}, {"$set": {"bot": True}})

            keys_to_remove.append(key)

    for key in keys_to_remove:
        del trade_aggregation_buffer[key]

    return ready


async def do_trading(clob_client: Any, trades: List[TradeWithUser]) -> None:
    """Execute trades"""
    for trade in trades:
        collection = get_user_activity_collection(trade["userAddress"])
        collection.update_one({"_id": trade["_id"]}, {"$set": {"botExcutedTime": 1}})

        log_trade(
            trade["userAddress"],
            trade.get("side", "UNKNOWN"),
            {
                "asset": trade.get("asset"),
                "side": trade.get("side"),
                "amount": trade.get("usdcSize"),
                "price": trade.get("price"),
                "slug": trade.get("slug"),
                "eventSlug": trade.get("eventSlug"),
                "transactionHash": trade.get("transactionHash"),
            },
        )

        my_positions_data = await fetch_data_async(
            f"https://data-api.polymarket.com/positions?user={PROXY_WALLET}"
        )
        user_positions_data = await fetch_data_async(
            f"https://data-api.polymarket.com/positions?user={trade['userAddress']}"
        )

        my_positions_list = my_positions_data if isinstance(my_positions_data, list) else []
        user_positions_list = (
            user_positions_data if isinstance(user_positions_data, list) else []
        )

        my_position = next(
            (p for p in my_positions_list if p.get("conditionId") == trade.get("conditionId")),
            None,
        )
        user_position = next(
            (p for p in user_positions_list if p.get("conditionId") == trade.get("conditionId")),
            None,
        )

        my_balance = await get_my_balance_async(PROXY_WALLET)
        user_balance = sum(pos.get("currentValue", 0) or 0 for pos in user_positions_list)

        log_balance(my_balance, user_balance, trade["userAddress"])

        await post_order(
            clob_client,
            "buy" if trade.get("side") == "BUY" else "sell",
            my_position,
            user_position,
            trade,
            my_balance,
            user_balance,
            trade["userAddress"],
        )

        separator()


async def do_aggregated_trading(clob_client: Any, aggregated_trades: List[AggregatedTrade]) -> None:
    """Execute aggregated trades"""
    for agg in aggregated_trades:
        header(f"AGGREGATED TRADE ({len(agg['trades'])} trades combined)")
        info(f"Market: {agg.get('slug') or agg.get('asset', 'unknown')}")
        info(f"Side: {agg.get('side', 'BUY')}")
        info(f"Total volume: ${agg['totalUsdcSize']:.2f}")
        info(f"Average price: ${agg['averagePrice']:.4f}")

        for trade in agg["trades"]:
            collection = get_user_activity_collection(trade["userAddress"])
            collection.update_one({"_id": trade["_id"]}, {"$set": {"botExcutedTime": 1}})

        my_positions_data = await fetch_data_async(
            f"https://data-api.polymarket.com/positions?user={PROXY_WALLET}"
        )
        user_positions_data = await fetch_data_async(
            f"https://data-api.polymarket.com/positions?user={agg['userAddress']}"
        )

        my_positions_list = my_positions_data if isinstance(my_positions_data, list) else []
        user_positions_list = (
            user_positions_data if isinstance(user_positions_data, list) else []
        )

        my_position = next(
            (p for p in my_positions_list if p.get("conditionId") == agg.get("conditionId")),
            None,
        )
        user_position = next(
            (p for p in user_positions_list if p.get("conditionId") == agg.get("conditionId")),
            None,
        )

        my_balance = await get_my_balance_async(PROXY_WALLET)
        user_balance = sum(pos.get("currentValue", 0) or 0 for pos in user_positions_list)

        log_balance(my_balance, user_balance, agg["userAddress"])

        synthetic_trade: TradeWithUser = {
            **agg["trades"][0],
            "usdcSize": agg["totalUsdcSize"],
            "price": agg["averagePrice"],
            "side": agg.get("side", "BUY"),
        }

        await post_order(
            clob_client,
            "buy" if agg.get("side", "BUY") == "BUY" else "sell",
            my_position,
            user_position,
            synthetic_trade,
            my_balance,
            user_balance,
            agg["userAddress"],
        )

        separator()


def stop_trade_executor() -> None:
    """Stop the trade executor gracefully"""
    global is_running
    is_running = False
    info("Trade executor shutdown requested...")


async def trade_executor(clob_client: Any) -> None:
    """Main trade executor function"""
    success(f"Trade executor ready for {len(USER_ADDRESSES)} trader(s)")
    if TRADE_AGGREGATION_ENABLED:
        info(
            f"Trade aggregation enabled: {TRADE_AGGREGATION_WINDOW_SECONDS}s window, "
            f"${TRADE_AGGREGATION_MIN_TOTAL_USD} minimum"
        )

    last_check = time.time()

    while is_running:
        trades = await read_temp_trades()

        if TRADE_AGGREGATION_ENABLED:
            if trades:
                clear_line()
                info(f"{len(trades)} new trade{'s' if len(trades) > 1 else ''} detected")

                for trade in trades:
                    if trade.get("side") == "BUY" and trade.get("usdcSize", 0) < TRADE_AGGREGATION_MIN_TOTAL_USD:
                        info(
                            f"Adding ${trade.get('usdcSize', 0):.2f} {trade.get('side', 'BUY')} trade "
                            f"to aggregation buffer for {trade.get('slug') or trade.get('asset', 'unknown')}"
                        )
                        add_to_aggregation_buffer(trade)
                    else:
                        clear_line()
                        header("IMMEDIATE TRADE (above threshold)")
                        await do_trading(clob_client, [trade])

                last_check = time.time()

            ready_aggregations = get_ready_aggregated_trades()
            if ready_aggregations:
                clear_line()
                header(
                    f"{len(ready_aggregations)} AGGREGATED TRADE"
                    f"{'S' if len(ready_aggregations) > 1 else ''} READY"
                )
                await do_aggregated_trading(clob_client, ready_aggregations)
                last_check = time.time()

            if not trades and not ready_aggregations:
                if time.time() - last_check > 0.3:
                    buffered_count = len(trade_aggregation_buffer)
                    if buffered_count > 0:
                        waiting(len(USER_ADDRESSES), f"{buffered_count} trade group(s) pending")
                    else:
                        waiting(len(USER_ADDRESSES))
                    last_check = time.time()
        else:
            if trades:
                clear_line()
                header(f"{len(trades)} NEW TRADE{'S' if len(trades) > 1 else ''} TO COPY")
                await do_trading(clob_client, trades)
                last_check = time.time()
            else:
                if time.time() - last_check > 0.3:
                    waiting(len(USER_ADDRESSES))
                    last_check = time.time()

        if not is_running:
            break

        await asyncio.sleep(0.3)

    info("Trade executor stopped")