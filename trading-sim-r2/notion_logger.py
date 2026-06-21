"""Notion logging for the daily trading run.

Writes one page per day into the "Trading Sim — Round 2" database. If Notion
credentials are absent or the call fails, logging is skipped gracefully — it
must never block or crash the trading run.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from utils import log, log_error

# Notion caps a single rich-text element at 2000 chars; chunk anything longer.
_RICH_TEXT_LIMIT = 2000


def _rich_text(value: str) -> Dict[str, Any]:
    value = value or "—"
    chunks = [value[i : i + _RICH_TEXT_LIMIT] for i in range(0, len(value), _RICH_TEXT_LIMIT)]
    return {
        "rich_text": [
            {"type": "text", "text": {"content": chunk}} for chunk in chunks[:20]
        ]
    }


def _number(value: Any) -> Dict[str, Any]:
    try:
        return {"number": round(float(value), 2)}
    except (TypeError, ValueError):
        return {"number": None}


def _title(value: str) -> Dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": value or "—"}}]}


def log_daily_run(summary: Dict[str, Any]) -> bool:
    """Write one row to Notion. Returns True on success, False if skipped/failed.

    `summary` is expected to contain the keys produced by agent.build_summary().
    """
    api_key = os.getenv("NOTION_API_KEY", "").strip()
    database_id = os.getenv("NOTION_DATABASE_ID", "").strip()

    if not api_key or not database_id:
        log.info("Notion logging skipped (NOTION_API_KEY/NOTION_DATABASE_ID not set)")
        return False

    try:
        from notion_client import Client
    except ImportError as exc:  # pragma: no cover
        log_error("notion-client not installed — skipping Notion logging", exc)
        return False

    properties = {
        "Date": _title(summary.get("date", "")),
        "Portfolio Value": _number(summary.get("portfolio_value")),
        "Daily P&L $": _number(summary.get("daily_pnl")),
        "Daily P&L %": _number(summary.get("daily_pnl_pct")),
        "Cumulative P&L $": _number(summary.get("cumulative_pnl")),
        "Cumulative P&L %": _number(summary.get("cumulative_pnl_pct")),
        "Cash %": _number(summary.get("cash_pct")),
        "Positions": _rich_text(summary.get("positions_text", "")),
        "Trade Actions": _rich_text(summary.get("trade_actions_text", "")),
        "Market Assessment": _rich_text(summary.get("market_assessment", "")),
        "Reasoning": _rich_text(summary.get("reasoning", "")),
        "Top Headlines": _rich_text(summary.get("headlines_text", "")),
    }

    # Retry the create up to 3 times before giving up.
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            client = Client(auth=api_key)
            client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
            )
            log.info("Logged daily run to Notion")
            return True
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            log.warning("Notion logging failed (attempt %d/3): %s", attempt, exc)

    log_error("Notion logging failed after 3 attempts — continuing", last_exc)
    return False
