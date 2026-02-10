"""
Trade monitor service - monitors trader activity via WebSocket

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

# Optional: enforce explicit phase number (recommended)
#   1 = recorder/simulation
#   2 = strategy
#   3 = dry-run execution
#   4 = live execution (ONLY here)
APP_PHASE = _env_str("APP_PHASE", "")

if not ENABLE_TRADING:
    raise RuntimeError(
        "trade_monitor is DISABLED for Phase 1/2/3 safety.\n"
        "This module must not be imported or executed until Phase 4+.\n"
        "To enable (Phase 4+ only):\n"
        "  export ENABLE_TRADING=true\n"
        "  export APP_PHASE=4   # recommended\n"
    )

if APP_PHASE and APP_PHASE != "4":
    raise RuntimeError(
        f"trade_monitor blocked: APP_PHASE={APP_PHASE!r}.\n"
        "This module is only allowed when APP_PHASE=4.\n"
        "Set:\n"
        "  export APP_PHASE=4\n"
    )

# -----------------------------
# Real implementation below
# (your original imports/logic)
# -----------------------------

import asyncio
import json
import websockets
from typing import List, Dict, Any, Optional

from ...config.env import ENV
from ...models.user_history import get_user_activity_collection, get_user_position_collection
from ...utils.fetch_data import fetch_data_async
from ...utils.logger import (
    info, success, warning, error, db_connection, my_positions,
    traders_positions, clear_line
)
from ...utils.get_my_balance import get_my_balance

USER_ADDRESSES = ENV.USER_ADDRESSES
TOO_OLD_TIMESTAMP = ENV.TOO_OLD_TIMESTAMP
RTDS_URL = "wss://ws-live-data.polymarket.com"

if not USER_ADDRESSES or len(USER_ADDRESSES) == 0:
    raise ValueError("USER_ADDRESSES is not defined or empty")

# WebSocket connection state
ws: Optional[websockets.client.WebSocketClientProtocol] = None
reconnect_attempts = 0
MAX_RECONNECT_ATTEMPTS = 10
RECONNECT_DELAY = 5  # seconds
is_running = True
position_update_task: Optional[asyncio.Task] = None
is_first_run = True


# -----------------------------------
# Your functions (remove stubbed raises)
# Keep these as real implementations.
# -----------------------------------

async def init():
    """Initialize the RTDS websocket connection and any state."""
    # TODO: restore real init logic here (from original bot) when Phase 4+ starts.
    raise NotImplementedError("Phase 4+ trade_monitor init not implemented yet.")


async def process_trade_activity(activity: Dict[str, Any], address: str):
    """Process an activity message and persist relevant updates."""
    # TODO: restore real trade activity processing here.
    raise NotImplementedError("Phase 4+ trade_monitor processing not implemented yet.")


async def update_positions():
    """Periodic position refresh loop."""
    # TODO: restore real position refresh loop here.
    raise NotImplementedError("Phase 4+ trade_monitor update_positions not implemented yet.")


async def connect_rtds():
    """Connect to the RTDS websocket and subscribe to trader feeds."""
    # TODO: restore real websocket connect/subscribe logic here.
    raise NotImplementedError("Phase 4+ trade_monitor connect_rtds not implemented yet.")


async def reconnect_loop():
    """Reconnect logic if websocket drops."""
    # TODO: restore reconnect logic here.
    raise NotImplementedError("Phase 4+ trade_monitor reconnect_loop not implemented yet.")


def stop_trade_monitor():
    """Stop the trade monitor gracefully."""
    global is_running
    is_running = False
    info("Trade monitor shutdown requested...")


async def trade_monitor():
    """
    Main trade monitor coroutine.
    Phase 4+ only.
    """
    success(f"Trade monitor starting for {len(USER_ADDRESSES)} trader(s).")
    # TODO: wire:
    #  - await init()
    #  - await connect_rtds()
    #  - run reconnect_loop/update_positions tasks
    raise NotImplementedError("Phase 4+ trade_monitor main loop not implemented yet.")