"""Daily autonomous trading simulation agent.

Orchestrates: load portfolio -> fetch prices -> fetch news -> Claude decision
-> execute trades -> mark-to-market -> log (Notion + history) -> print summary.

Entry points:
    python agent.py --run-now                 run one cycle immediately
    python agent.py                           schedule a daily run at 06:00 PT
    python agent.py --backtest --date DATE     run one cycle for a given date
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

import email_notifier
import heartbeat
import news
import prices as price_mod
from decision_engine import get_trade_decision
from notion_logger import log_daily_run
from utils import ERROR_LOG, log, log_error, read_json, write_json_atomic

HERE = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_PATH = os.path.join(HERE, "portfolio.json")
HISTORY_PATH = os.path.join(HERE, "history.json")

# Trading constraints (enforced best-effort on execution).
MAX_POSITIONS = 5

load_dotenv(os.path.join(HERE, ".env"))


# --------------------------------------------------------------------------- #
# Portfolio I/O
# --------------------------------------------------------------------------- #
def load_portfolio() -> Dict[str, Any]:
    portfolio = read_json(PORTFOLIO_PATH)
    if portfolio is None:
        raise FileNotFoundError(f"portfolio.json not found at {PORTFOLIO_PATH}")
    portfolio.setdefault("positions", {})
    portfolio.setdefault("trades", [])
    portfolio.setdefault("cash", portfolio.get("capital", 100000))
    return portfolio


def save_portfolio(portfolio: Dict[str, Any]) -> None:
    write_json_atomic(PORTFOLIO_PATH, portfolio)


def append_history(entry: Dict[str, Any]) -> None:
    history = read_json(HISTORY_PATH, default=[]) or []
    history.append(entry)
    write_json_atomic(HISTORY_PATH, history)


def last_total_value(portfolio: Dict[str, Any]) -> float:
    """Yesterday's portfolio value, for daily P&L. Falls back to capital."""
    history = read_json(HISTORY_PATH, default=[]) or []
    if history:
        prev = history[-1].get("portfolio_value")
        if isinstance(prev, (int, float)):
            return float(prev)
    return float(portfolio.get("capital", 100000))


# --------------------------------------------------------------------------- #
# Trade execution
# --------------------------------------------------------------------------- #
def _price_for(ticker: str, prices: Dict[str, Any], fallback: float) -> float:
    entry = prices.get(ticker)
    if entry and isinstance(entry.get("price"), (int, float)):
        return float(entry["price"])
    return float(fallback)


def execute_trades(
    portfolio: Dict[str, Any],
    trades: List[Dict[str, Any]],
    prices: Dict[str, Any],
    today: str,
) -> List[str]:
    """Apply BUY/SELL/HOLD trades to the portfolio in place.

    Returns a list of human-readable action strings (also used for logging).
    Constraints are enforced defensively so a bad decision can't break state.
    """
    actions: List[str] = []
    positions: Dict[str, Any] = portfolio["positions"]

    for trade in trades:
        action = str(trade.get("action", "")).upper()
        ticker = str(trade.get("asset", "")).upper().strip()
        conviction = trade.get("conviction", "")
        catalyst = trade.get("catalyst", "")

        if action == "HOLD" or not ticker:
            if ticker:
                actions.append(f"HOLD {ticker} ({catalyst})")
            continue

        try:
            qty = float(trade.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            actions.append(f"SKIP {action} {ticker}: non-positive quantity")
            log_error(f"Skipped {action} {ticker}: bad quantity {trade.get('quantity')}")
            continue

        price = _price_for(ticker, prices, trade.get("price", 0) or 0)
        if price <= 0:
            actions.append(f"SKIP {action} {ticker}: no price available")
            log_error(f"Skipped {action} {ticker}: no price")
            continue

        if action == "BUY":
            cost = qty * price
            # Enforce max positions for *new* tickers.
            if ticker not in positions and len(positions) >= MAX_POSITIONS:
                actions.append(f"SKIP BUY {ticker}: max {MAX_POSITIONS} positions")
                log_error(f"Skipped BUY {ticker}: position cap reached")
                continue
            if cost > portfolio["cash"] + 1e-6:
                # Buy as much as the cash allows rather than rejecting outright.
                affordable_qty = portfolio["cash"] / price
                if affordable_qty <= 0:
                    actions.append(f"SKIP BUY {ticker}: insufficient cash")
                    log_error(f"Skipped BUY {ticker}: insufficient cash")
                    continue
                log.warning("Trimming BUY %s from %.4f to %.4f (cash limit)",
                            ticker, qty, affordable_qty)
                qty = affordable_qty
                cost = qty * price

            held = positions.get(ticker, {"quantity": 0.0, "avg_price": 0.0})
            new_qty = held["quantity"] + qty
            new_avg = (
                (held["quantity"] * held["avg_price"] + qty * price) / new_qty
                if new_qty
                else price
            )
            positions[ticker] = {
                "quantity": round(new_qty, 8),
                "avg_price": round(new_avg, 6),
                "asset_class": prices.get(ticker, {}).get("asset_class", "unknown"),
            }
            portfolio["cash"] = round(portfolio["cash"] - cost, 6)
            actions.append(
                f"BUY {qty:.4f} {ticker} @ ${price:,.2f} "
                f"(${cost:,.0f}, {conviction}) — {catalyst}"
            )
            portfolio["trades"].append(
                {"date": today, "action": "BUY", "asset": ticker, "quantity": qty,
                 "price": price, "dollar_amount": round(cost, 2),
                 "conviction": conviction, "catalyst": catalyst}
            )

        elif action == "SELL":
            held = positions.get(ticker)
            if not held or held["quantity"] <= 0:
                actions.append(f"SKIP SELL {ticker}: no open position")
                log_error(f"Skipped SELL {ticker}: no position")
                continue
            sell_qty = min(qty, held["quantity"])
            proceeds = sell_qty * price
            remaining = held["quantity"] - sell_qty
            if remaining <= 1e-9:
                positions.pop(ticker, None)
            else:
                held["quantity"] = round(remaining, 8)
            portfolio["cash"] = round(portfolio["cash"] + proceeds, 6)
            actions.append(
                f"SELL {sell_qty:.4f} {ticker} @ ${price:,.2f} "
                f"(${proceeds:,.0f}, {conviction}) — {catalyst}"
            )
            portfolio["trades"].append(
                {"date": today, "action": "SELL", "asset": ticker,
                 "quantity": sell_qty, "price": price,
                 "dollar_amount": round(proceeds, 2),
                 "conviction": conviction, "catalyst": catalyst}
            )
        else:
            actions.append(f"SKIP unknown action '{action}' for {ticker}")
            log_error(f"Unknown action '{action}' for {ticker}")

    return actions or ["No trades — holding all positions."]


def mark_to_market(portfolio: Dict[str, Any], prices: Dict[str, Any]) -> float:
    """Total portfolio value = cash + market value of all positions."""
    total = float(portfolio["cash"])
    for ticker, held in portfolio["positions"].items():
        price = _price_for(ticker, prices, held.get("avg_price", 0))
        total += held["quantity"] * price
    return round(total, 2)


# --------------------------------------------------------------------------- #
# Summary building + terminal output
# --------------------------------------------------------------------------- #
def build_summary(
    today: str,
    portfolio: Dict[str, Any],
    prices: Dict[str, Any],
    decision: Dict[str, Any],
    actions: List[str],
    headlines: List[str],
    prev_value: float,
) -> Dict[str, Any]:
    total_value = mark_to_market(portfolio, prices)
    capital = float(portfolio.get("capital", 100000))

    daily_pnl = round(total_value - prev_value, 2)
    daily_pnl_pct = round((daily_pnl / prev_value) * 100, 2) if prev_value else 0.0
    cumulative_pnl = round(total_value - capital, 2)
    cumulative_pnl_pct = round((cumulative_pnl / capital) * 100, 2) if capital else 0.0
    cash_pct = round((portfolio["cash"] / total_value) * 100, 2) if total_value else 0.0

    # Positions with current mark + unrealized P&L for readability.
    positions_view: Dict[str, Any] = {}
    for ticker, held in portfolio["positions"].items():
        price = _price_for(ticker, prices, held.get("avg_price", 0))
        mkt_val = round(held["quantity"] * price, 2)
        positions_view[ticker] = {
            "quantity": held["quantity"],
            "avg_price": held["avg_price"],
            "current_price": price,
            "market_value": mkt_val,
            "weight_pct": round((mkt_val / total_value) * 100, 2) if total_value else 0.0,
        }

    return {
        "date": today,
        "portfolio_value": total_value,
        "cash": round(portfolio["cash"], 2),
        "cash_pct": cash_pct,
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": daily_pnl_pct,
        "cumulative_pnl": cumulative_pnl,
        "cumulative_pnl_pct": cumulative_pnl_pct,
        "positions": positions_view,
        "positions_text": json.dumps(positions_view, indent=2),
        "trade_actions": actions,
        "trade_actions_text": "\n".join(actions),
        "market_assessment": decision.get("market_assessment", ""),
        "reasoning": decision.get("reasoning", ""),
        "headlines": headlines,
        "headlines_text": "\n".join(f"- {h}" for h in headlines),
    }


def print_summary(summary: Dict[str, Any]) -> None:
    def sign(v: float) -> str:
        return "🟢" if v > 0 else ("🔴" if v < 0 else "⚪")

    line = "═" * 64
    print(f"\n{line}")
    print(f"📊  TRADING SIM — ROUND 2   |   {summary['date']}")
    print(line)
    print(f"💼  Portfolio Value : ${summary['portfolio_value']:,.2f}")
    print(f"💵  Cash            : ${summary['cash']:,.2f}  ({summary['cash_pct']:.1f}%)")
    print(f"{sign(summary['daily_pnl'])}  Daily P&L       : "
          f"${summary['daily_pnl']:,.2f}  ({summary['daily_pnl_pct']:+.2f}%)")
    print(f"{sign(summary['cumulative_pnl'])}  Cumulative P&L  : "
          f"${summary['cumulative_pnl']:,.2f}  ({summary['cumulative_pnl_pct']:+.2f}%)")

    print(f"\n🧠  Market Read     : {summary['market_assessment'] or '—'}")

    print("\n📈  Positions:")
    if summary["positions"]:
        for ticker, p in summary["positions"].items():
            print(f"    • {ticker:<6} {p['quantity']:>12.4f} @ ${p['avg_price']:<12,.2f}"
                  f" → ${p['market_value']:>12,.2f}  ({p['weight_pct']:.1f}%)")
    else:
        print("    • 100% cash — no open positions.")

    print("\n🔁  Today's Actions:")
    for action in summary["trade_actions"]:
        print(f"    • {action}")

    print("\n📰  Top Headlines:")
    for h in summary["headlines"][:5]:
        print(f"    • {h}")
    if not summary["headlines"]:
        print("    • (none available)")
    print(f"{line}\n")


# --------------------------------------------------------------------------- #
# Main cycle
# --------------------------------------------------------------------------- #
def run_cycle(today: Optional[str] = None, backtest: bool = False) -> Dict[str, Any]:
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mode = "BACKTEST" if backtest else "LIVE"
    log.info("=== Trading cycle start (%s) for %s ===", mode, today)

    # 1. Load state (read-only until we have a validated decision).
    portfolio = load_portfolio()
    prev_value = last_total_value(portfolio)

    # 2. Market data.
    prices = price_mod.fetch_all_prices()
    headlines = news.fetch_headlines(limit=10)

    # 3. Yesterday's decision (last history entry's decision, if any).
    history = read_json(HISTORY_PATH, default=[]) or []
    yesterday_decision = history[-1].get("decision") if history else None

    # 4. Claude decision.
    decision = get_trade_decision(today, portfolio, prices, headlines, yesterday_decision)

    # 5. Execute (skip if the engine returned a safe HOLD on failure).
    if decision.get("_engine_error"):
        log.warning("Engine error — holding all positions, no trades executed.")
        actions = ["⚠️  Decision engine failed — held all positions."]
    else:
        actions = execute_trades(portfolio, decision.get("trades", []), prices, today)

    # 6. Persist portfolio atomically (temp file -> rename).
    summary = build_summary(today, portfolio, prices, decision, actions, headlines, prev_value)
    portfolio["last_value"] = summary["portfolio_value"]
    portfolio["last_updated"] = today
    try:
        save_portfolio(portfolio)
    except Exception as exc:  # noqa: BLE001
        log_error("Failed to save portfolio.json — aborting before history write", exc)
        raise

    # 7. Append to history.json.
    append_history({
        "date": today,
        "mode": mode,
        "portfolio_value": summary["portfolio_value"],
        "cash": summary["cash"],
        "daily_pnl": summary["daily_pnl"],
        "cumulative_pnl": summary["cumulative_pnl"],
        "positions": summary["positions"],
        "actions": actions,
        "headlines": headlines,
        "prices": prices,
        "decision": decision,
    })

    # 8. Notion logging + email summary (both best-effort).
    log_daily_run(summary)
    email_notifier.send_daily_summary(summary)

    # 9. Terminal summary.
    print_summary(summary)
    log.info("=== Trading cycle complete for %s ===", today)
    return summary


def safe_run_cycle(today: Optional[str] = None, backtest: bool = False) -> None:
    """Run a cycle; on any uncaught failure, email an alert and log it.

    Used by the scheduler and CLI so an unattended run that crashes still
    notifies you instead of failing silently.
    """
    day = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    heartbeat.ping_start()
    try:
        summary = run_cycle(today=today, backtest=backtest)
        # Reset the dead man's switch — a missed ping is what triggers the alert.
        heartbeat.ping_success(
            f"{day}: ${summary['portfolio_value']:,.0f} "
            f"({summary['cumulative_pnl_pct']:+.2f}% total)"
        )
    except Exception as exc:  # noqa: BLE001 - top-level per-run safety net
        log_error(f"Trading cycle for {day} failed", exc)
        email_notifier.send_failure_alert(day, f"{type(exc).__name__}: {exc}")
        heartbeat.ping_failure(f"{day}: {type(exc).__name__}: {exc}")
        raise


# --------------------------------------------------------------------------- #
# CLI / scheduler
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Daily autonomous trading sim agent")
    parser.add_argument("--run-now", action="store_true",
                        help="Run one trading cycle immediately and exit.")
    parser.add_argument("--backtest", action="store_true",
                        help="Run in backtest mode (use with --date).")
    parser.add_argument("--date", type=str, default=None,
                        help="Date (YYYY-MM-DD) for backtest mode.")
    args = parser.parse_args()

    try:
        if args.backtest:
            safe_run_cycle(today=args.date, backtest=True)
            return
        if args.run_now:
            safe_run_cycle()
            return

        # Default: schedule a daily run at 06:00 (server local time; set the
        # box to PT, or run via cron — see README). The scheduled job swallows
        # exceptions (after emailing an alert) so one bad day can't kill the
        # long-running scheduler.
        import schedule

        def scheduled_job() -> None:
            try:
                safe_run_cycle()
            except Exception:  # noqa: BLE001 - already logged + emailed
                pass

        schedule.every().day.at("06:00").do(scheduled_job)
        log.info("⏰ Scheduled daily run at 06:00. Waiting... (Ctrl-C to exit)")
        log.info("    Errors are written to %s", ERROR_LOG)
        import time
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("Interrupted — exiting.")
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        log_error("Fatal error in agent main loop", exc)
        raise


if __name__ == "__main__":
    main()
