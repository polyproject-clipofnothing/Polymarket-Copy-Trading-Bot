"""
Logger utility with colored output and file logging
+ Optional structured JSON logging (LOG_FORMAT=json) for PR20 observability

Key behaviors:
- LOG_FORMAT=text (default): human-friendly colored console output + daily log file
- LOG_FORMAT=json: one JSON object per line to stdout/stderr + daily log file
- BrokenPipe-safe: piping to `head` / `jq` won't crash the process
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# -------------------------
# Config (read env at runtime, not import-time)
# -------------------------
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log_format() -> str:
    return os.getenv("LOG_FORMAT", "text").lower().strip()  # "text" | "json"


def _now_iso() -> str:
    return datetime.now().isoformat()


def _now_ts() -> float:
    return datetime.now().timestamp()


def _safe_json(obj: Any) -> Any:
    """
    Best-effort JSON conversion for arbitrary objects.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe_json(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _safe_json(v) for k, v in obj.items()}
    return str(obj)


# -------------------------
# Colors (TEXT mode only)
# -------------------------
class _NoColorFore:
    RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = BLACK = WHITE = ""


class _NoColorStyle:
    RESET_ALL = BRIGHT = DIM = ""


Fore = _NoColorFore  # type: ignore
Style = _NoColorStyle  # type: ignore

if _log_format() != "json":
    # Only initialize colorama when we intend to print colored text.
    try:
        from colorama import init as _colorama_init, Fore as _Fore, Style as _Style  # type: ignore

        _colorama_init(autoreset=True)
        Fore = _Fore  # type: ignore
        Style = _Style  # type: ignore
    except Exception:
        # Keep no-color fallbacks
        pass


# -------------------------
# File logging
# -------------------------
def get_log_file_name() -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"bot-{date}.log"


def write_to_file(message: str) -> None:
    """
    Write a plain text line to the daily log file.
    """
    try:
        log_file = get_log_file_name()
        log_entry = f"[{_now_iso()}] {message}\n"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.open("a", encoding="utf-8").write(log_entry)
    except Exception:
        pass


def write_json_to_file(payload: Dict[str, Any]) -> None:
    """
    Write a JSON payload as a single line to the daily log file.
    """
    try:
        log_file = get_log_file_name()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


# -------------------------
# Console output (BrokenPipe-safe)
# -------------------------
def _print_safe(text: str, *, stream: Any) -> None:
    """
    Print that won't explode if the consumer closes the pipe (e.g. `| head`, `| jq`).
    """
    try:
        print(text, file=stream, flush=True)
    except BrokenPipeError:
        # Consumer closed the pipe early; stop emitting output quietly.
        return


def _emit(level: str, message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Unified log output.

    If LOG_FORMAT=json:
      - emit JSON to stdout/stderr (stderr only for error)
      - also append JSON line to daily log file

    If LOG_FORMAT=text:
      - emit colored message like before
      - also append plain text line to daily log file
    """
    fmt = _log_format()
    context = context or {}
    lvl = str(level).lower()

    if fmt == "json":
        payload: Dict[str, Any] = {
            "ts": _now_ts(),
            "ts_iso": _now_iso(),
            "level": lvl,
            "message": str(message),
            "context": _safe_json(context),
        }
        stream = sys.stderr if lvl == "error" else sys.stdout
        _print_safe(json.dumps(payload), stream=stream)
        write_json_to_file(payload)
        return

    # TEXT mode
    if lvl == "info":
        _print_safe(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {message}", stream=sys.stdout)
        write_to_file(f"INFO: {message}")
    elif lvl == "success":
        _print_safe(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}", stream=sys.stdout)
        write_to_file(f"SUCCESS: {message}")
    elif lvl == "warning":
        _print_safe(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}", stream=sys.stdout)
        write_to_file(f"WARNING: {message}")
    elif lvl == "error":
        _print_safe(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}", stream=sys.stderr)
        write_to_file(f"ERROR: {message}")
    else:
        _print_safe(str(message), stream=sys.stdout)
        write_to_file(str(message))


# -------------------------
# Public helpers (PR20)
# -------------------------
def log_event(event: Any) -> None:
    """
    Emit a canonical event (RunEvent from src/observability/events.py) or dict-like object.

    In LOG_FORMAT=json:
      - we merge event.context into top-level context
      - we keep the full event under context.event for traceability
    """
    if hasattr(event, "to_dict"):
        payload = event.to_dict()  # type: ignore[attr-defined]
    elif isinstance(event, dict):
        payload = event
    else:
        payload = {"level": "info", "message": str(event), "context": {}}

    level = str(payload.get("level", "info")).lower()
    message = str(payload.get("message", ""))
    ev_ctx = payload.get("context", {})
    if not isinstance(ev_ctx, dict):
        ev_ctx = {"context": str(ev_ctx)}

    if _log_format() == "json":
        merged: Dict[str, Any] = {"event": payload}
        merged.update(ev_ctx)
        _emit(level, message, context=merged)
    else:
        _emit(level, message, context=ev_ctx)


# -------------------------
# Existing helpers (same API)
# -------------------------
def format_address(address: str) -> str:
    return f"{address[:6]}...{address[-4:]}"


def mask_address(address: str) -> str:
    return f"{address[:6]}{'*' * 34}{address[-4:]}"


def header(title: str) -> None:
    if _log_format() == "json":
        _emit("info", "HEADER", context={"title": title})
        return

    _print_safe(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.CYAN}{Style.BRIGHT}  {title}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}\n", stream=sys.stdout)
    write_to_file(f"HEADER: {title}")


def info(message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
    _emit("info", message, context=context)


def success(message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
    _emit("success", message, context=context)


def warning(message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
    _emit("warning", message, context=context)


def error(message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
    _emit("error", message, context=context)


def trade(trader_address: str, action: str, details: dict) -> None:
    if _log_format() == "json":
        _emit(
            "info",
            "NEW_TRADE_DETECTED",
            context={"trader_address": trader_address, "action": action, "details": details},
        )
        return

    _print_safe(f"\n{Fore.MAGENTA}{'-' * 70}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.MAGENTA}{Style.BRIGHT}NEW TRADE DETECTED{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.MAGENTA}{'-' * 70}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Trader: {Fore.CYAN}{format_address(trader_address)}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Action: {Style.BRIGHT}{action}{Style.RESET_ALL}", stream=sys.stdout)

    if details.get("asset"):
        _print_safe(f"Asset:  {Style.DIM}{format_address(details['asset'])}{Style.RESET_ALL}", stream=sys.stdout)
    if details.get("side"):
        side_color = Fore.GREEN if details["side"] == "BUY" else Fore.RED
        _print_safe(f"Side:   {side_color}{Style.BRIGHT}{details['side']}{Style.RESET_ALL}", stream=sys.stdout)
    if details.get("amount"):
        _print_safe(f"Amount: {Fore.YELLOW}${details['amount']:.2f}{Style.RESET_ALL}", stream=sys.stdout)
    if details.get("price"):
        _print_safe(f"Price:  {Fore.CYAN}${details['price']:.4f}{Style.RESET_ALL}", stream=sys.stdout)
    if details.get("eventSlug") or details.get("slug"):
        slug = details.get("eventSlug") or details.get("slug")
        market_url = f"https://polymarket.com/event/{slug}"
        _print_safe(f"Market: {Fore.BLUE}{market_url}{Style.RESET_ALL}", stream=sys.stdout)
    if details.get("transactionHash"):
        tx_url = f"https://polygonscan.com/tx/{details['transactionHash']}"
        _print_safe(f"TX:     {Fore.BLUE}{tx_url}{Style.RESET_ALL}", stream=sys.stdout)

    _print_safe(f"{Fore.MAGENTA}{'-' * 70}{Style.RESET_ALL}\n", stream=sys.stdout)

    trade_log = f"TRADE: {format_address(trader_address)} - {action}"
    if details.get("side"):
        trade_log += f" | Side: {details['side']}"
    if details.get("amount"):
        trade_log += f" | Amount: ${details['amount']:.2f}"
    if details.get("price"):
        trade_log += f" | Price: ${details['price']:.4f}"
    if details.get("title"):
        trade_log += f" | Market: {details['title']}"
    if details.get("transactionHash"):
        trade_log += f" | TX: {details['transactionHash']}"
    write_to_file(trade_log)


def balance(my_balance: float, trader_balance: float, trader_address: str) -> None:
    if _log_format() == "json":
        _emit(
            "info",
            "BALANCE",
            context={"my_balance": my_balance, "trader_balance": trader_balance, "trader_address": trader_address},
        )
        return

    _print_safe("Capital (USDC + Positions):", stream=sys.stdout)
    _print_safe(f"  Your total capital:   {Fore.GREEN}{Style.BRIGHT}${my_balance:.2f}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(
        f"  Trader total capital: {Fore.BLUE}{Style.BRIGHT}${trader_balance:.2f}{Style.RESET_ALL} ({format_address(trader_address)})",
        stream=sys.stdout,
    )


def order_result(success_flag: bool, message: str) -> None:
    if _log_format() == "json":
        _emit("info" if success_flag else "error", "ORDER_RESULT", context={"ok": success_flag, "message": message})
        return

    if success_flag:
        _print_safe(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Order executed: {message}", stream=sys.stdout)
        write_to_file(f"ORDER SUCCESS: {message}")
    else:
        _print_safe(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Order failed: {message}", stream=sys.stderr)
        write_to_file(f"ORDER FAILED: {message}")


def monitoring(trader_count: int) -> None:
    ts_hms = datetime.now().strftime("%H:%M:%S")
    if _log_format() == "json":
        _emit("info", "MONITORING", context={"trader_count": trader_count, "ts_hms": ts_hms})
        return
    _print_safe(
        f"{Style.DIM}[{ts_hms}]{Style.RESET_ALL} {Fore.CYAN}[INFO]{Style.RESET_ALL} Monitoring {Fore.YELLOW}{trader_count}{Style.RESET_ALL} trader(s)",
        stream=sys.stdout,
    )


def startup(traders: List[str], my_wallet: str) -> None:
    if _log_format() == "json":
        _emit("info", "STARTUP", context={"traders": traders, "my_wallet": my_wallet})
        return

    title = "COPY TRADING BOT"
    tagline = "Copy the best, automate success"

    border = "=" * 70
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}{border}{Style.RESET_ALL}
{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}{'':^68}{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}
{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL} {Fore.MAGENTA}{Style.BRIGHT}{title:^66}{Style.RESET_ALL} {Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}
{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}{'':^68}{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}
{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL} {Style.DIM}{tagline:^66}{Style.RESET_ALL} {Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}
{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}{'':^68}{Fore.CYAN}{Style.BRIGHT}={Style.RESET_ALL}
{Fore.CYAN}{Style.BRIGHT}{border}{Style.RESET_ALL}
"""
    _print_safe(banner, stream=sys.stdout)
    _print_safe(f"{Fore.CYAN}{Style.BRIGHT}{'─' * 70}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.CYAN}{Style.BRIGHT}Tracking Traders:{Style.RESET_ALL}", stream=sys.stdout)
    for index, address in enumerate(traders, 1):
        _print_safe(f"  {index}. {Style.DIM}{address}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(
        f"\n{Fore.CYAN}{Style.BRIGHT}Your Wallet:{Style.RESET_ALL} {Style.DIM}{mask_address(my_wallet)}{Style.RESET_ALL}\n",
        stream=sys.stdout,
    )


def db_connection(traders: List[str], counts: List[int]) -> None:
    if _log_format() == "json":
        _emit("info", "DB_CONNECTION", context={"traders": traders, "counts": counts})
        return

    _print_safe(f"\n{Fore.CYAN}Database Status:{Style.RESET_ALL}", stream=sys.stdout)
    for address, count in zip(traders, counts):
        _print_safe(f"  {format_address(address)}: {Fore.YELLOW}{count}{Style.RESET_ALL} trades", stream=sys.stdout)
    _print_safe("", stream=sys.stdout)


def separator() -> None:
    if _log_format() == "json":
        _emit("info", "SEPARATOR", context={})
        return
    _print_safe(f"{Style.DIM}{'-' * 70}{Style.RESET_ALL}", stream=sys.stdout)


def waiting(trader_count: int, extra_info: Optional[str] = None) -> None:
    ts_hms = datetime.now().strftime("%H:%M:%S")
    msg = f"Waiting for trades from {trader_count} trader(s)"
    if extra_info:
        msg += f" ({extra_info})"

    if _log_format() == "json":
        _emit("info", "WAITING", context={"trader_count": trader_count, "extra_info": extra_info, "ts_hms": ts_hms})
        return

    try:
        print(
            f"{Style.DIM}[{ts_hms}]{Style.RESET_ALL} {Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}",
            end="\r",
        )
        sys.stdout.flush()
    except BrokenPipeError:
        return


def clear_line() -> None:
    if _log_format() == "json":
        return
    try:
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()
    except BrokenPipeError:
        return


def my_positions(
    wallet: str,
    count: int,
    top_positions: List[dict],
    overall_pnl: float,
    total_value: float,
    initial_value: float,
    current_balance: float,
) -> None:
    if _log_format() == "json":
        _emit(
            "info",
            "MY_POSITIONS",
            context={
                "wallet": wallet,
                "count": count,
                "overall_pnl": overall_pnl,
                "total_value": total_value,
                "initial_value": initial_value,
                "current_balance": current_balance,
                "top_positions": top_positions,
            },
        )
        return

    _print_safe(f"\n{Fore.MAGENTA}{Style.BRIGHT}Your Positions{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.MAGENTA}{'-' * 70}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Wallet: {Style.DIM}{format_address(wallet)}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe("", stream=sys.stdout)

    total_portfolio = current_balance + total_value
    _print_safe(f"Available Cash:    {Fore.YELLOW}{Style.BRIGHT}${current_balance:.2f}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Total Portfolio:   {Fore.CYAN}{Style.BRIGHT}${total_portfolio:.2f}{Style.RESET_ALL}", stream=sys.stdout)

    if count == 0:
        _print_safe(f"\n{Style.DIM}No open positions{Style.RESET_ALL}\n", stream=sys.stdout)
        return

    pnl_sign = "+" if overall_pnl >= 0 else ""
    pnl_color = Fore.GREEN if overall_pnl >= 0 else Fore.RED

    _print_safe("", stream=sys.stdout)
    _print_safe(f"Open Positions:    {Fore.GREEN}{count}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Invested:          {Style.DIM}${initial_value:.2f}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Current Value:     {Fore.CYAN}${total_value:.2f}{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"Profit/Loss:       {pnl_color}{pnl_sign}{overall_pnl:.1f}%{Style.RESET_ALL}", stream=sys.stdout)

    if top_positions:
        _print_safe(f"\n{Style.DIM}Top Positions:{Style.RESET_ALL}", stream=sys.stdout)
        for pos in top_positions:
            pnl_sign2 = "+" if pos.get("percentPnl", 0) >= 0 else ""
            avg_price = pos.get("avgPrice", 0)
            cur_price = pos.get("curPrice", 0)
            title = (pos.get("title", "") or "")[:45]
            if len(pos.get("title", "") or "") > 45:
                title += "..."
            _print_safe(f'  {pos.get("outcome", "")} - {Style.DIM}{title}{Style.RESET_ALL}', stream=sys.stdout)
            pnl_value = pos.get("percentPnl", 0)
            pnl_color_pos = Fore.CYAN if pnl_value >= 0 else Fore.RED
            _print_safe(
                f'    Value: ${pos.get("currentValue", 0):.2f} | PnL: {pnl_color_pos}{pnl_sign2}{pnl_value:.1f}%{Style.RESET_ALL}',
                stream=sys.stdout,
            )
            _print_safe(f"    Bought @ {(avg_price * 100):.1f}¢ | Current @ {(cur_price * 100):.1f}¢", stream=sys.stdout)
    _print_safe("", stream=sys.stdout)


def traders_positions(
    traders: List[str],
    position_counts: List[int],
    position_details: Optional[List[List[dict]]] = None,
    profitabilities: Optional[List[float]] = None,
) -> None:
    if _log_format() == "json":
        _emit(
            "info",
            "TRADERS_POSITIONS",
            context={
                "traders": traders,
                "position_counts": position_counts,
                "position_details": position_details,
                "profitabilities": profitabilities,
            },
        )
        return

    _print_safe(f"\n{Fore.CYAN}{Style.BRIGHT}Traders You Are Copying{Style.RESET_ALL}", stream=sys.stdout)
    _print_safe(f"{Fore.CYAN}{'-' * 70}{Style.RESET_ALL}", stream=sys.stdout)

    for idx, address in enumerate(traders):
        count = position_counts[idx]
        count_str = f"{count} position{'s' if count > 1 else ''}" if count > 0 else "0 positions"

        profit_str = ""
        if profitabilities and profitabilities[idx] is not None and count > 0:
            pnl = profitabilities[idx]
            pnl_sign = "+" if pnl >= 0 else ""
            pnl_color = Fore.GREEN if pnl >= 0 else Fore.RED
            profit_str = f" | PnL: {pnl_color}{pnl_sign}{pnl:.1f}%{Style.RESET_ALL}"

        _print_safe(f"  {Style.DIM}{format_address(address)}{Style.RESET_ALL}: {count_str}{profit_str}", stream=sys.stdout)

        if position_details and position_details[idx]:
            for pos in position_details[idx]:
                pnl_sign2 = "+" if pos.get("percentPnl", 0) >= 0 else ""
                avg_price = pos.get("avgPrice", 0)
                cur_price = pos.get("curPrice", 0)
                title = (pos.get("title", "") or "")[:40]
                if len(pos.get("title", "") or "") > 40:
                    title += "..."
                _print_safe(f'    {pos.get("outcome", "")} - {Style.DIM}{title}{Style.RESET_ALL}', stream=sys.stdout)
                pnl_value = pos.get("percentPnl", 0)
                pnl_color_pos = Fore.CYAN if pnl_value >= 0 else Fore.RED
                _print_safe(
                    f'      Value: ${pos.get("currentValue", 0):.2f} | PnL: {pnl_color_pos}{pnl_sign2}{pnl_value:.1f}%{Style.RESET_ALL}',
                    stream=sys.stdout,
                )
                _print_safe(f"      Bought @ {(avg_price * 100):.1f}¢ | Current @ {(cur_price * 100):.1f}¢", stream=sys.stdout)
    _print_safe("", stream=sys.stdout)