"""Email notifications for the daily trading run.

Uses stdlib smtplib (no extra dependencies). Sends a summary email after each
successful cycle and a louder alert if a cycle fails outright. If SMTP settings
are absent, email is skipped gracefully — it must never block the trading run.

Configure via .env:
    EMAIL_TO         comma-separated recipient(s)   (required to enable email)
    SMTP_HOST        e.g. smtp.gmail.com            (required to enable email)
    SMTP_PORT        587 (STARTTLS) or 465 (SSL); default 587
    SMTP_USER        SMTP username (often = from address)
    SMTP_PASSWORD    SMTP password / app password
    EMAIL_FROM       From address; defaults to SMTP_USER
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate
from typing import Any, Dict, List

from utils import log, log_error


def _config() -> Dict[str, Any] | None:
    """Return SMTP config, or None if email isn't fully configured."""
    to = os.getenv("EMAIL_TO", "").strip()
    host = os.getenv("SMTP_HOST", "").strip()
    if not to or not host:
        return None
    user = os.getenv("SMTP_USER", "").strip()
    return {
        "to": [addr.strip() for addr in to.split(",") if addr.strip()],
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587").strip() or "587"),
        "user": user,
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("EMAIL_FROM", "").strip() or user or "trading-sim-r2",
    }


def _send(subject: str, body: str) -> bool:
    """Send one email. Returns True on success, False if skipped/failed."""
    cfg = _config()
    if cfg is None:
        log.info("Email skipped (EMAIL_TO / SMTP_HOST not set)")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = ", ".join(cfg["to"])
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body)

    # Retry up to 3 times with exponential backoff.
    import time

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            context = ssl.create_default_context()
            if cfg["port"] == 465:
                with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=30) as s:
                    if cfg["user"]:
                        s.login(cfg["user"], cfg["password"])
                    s.send_message(msg)
            else:
                with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as s:
                    s.ehlo()
                    s.starttls(context=context)
                    s.ehlo()
                    if cfg["user"]:
                        s.login(cfg["user"], cfg["password"])
                    s.send_message(msg)
            log.info("Sent email: %s", subject)
            return True
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            log.warning("Email send failed (attempt %d/3): %s", attempt, exc)
            if attempt < 3:
                time.sleep(2 * (2 ** (attempt - 1)))

    log_error("Email send failed after 3 attempts — continuing", last_exc)
    return False


def send_daily_summary(summary: Dict[str, Any]) -> bool:
    """Email the daily run summary."""
    arrow = "🟢" if summary["daily_pnl"] > 0 else ("🔴" if summary["daily_pnl"] < 0 else "⚪")
    subject = (
        f"{arrow} Trading Sim R2 — {summary['date']} | "
        f"${summary['portfolio_value']:,.0f} "
        f"({summary['cumulative_pnl_pct']:+.2f}% total)"
    )

    lines: List[str] = [
        f"TRADING SIM — ROUND 2   |   {summary['date']}",
        "=" * 56,
        f"Portfolio Value : ${summary['portfolio_value']:,.2f}",
        f"Cash            : ${summary['cash']:,.2f}  ({summary['cash_pct']:.1f}%)",
        f"Daily P&L       : ${summary['daily_pnl']:,.2f}  ({summary['daily_pnl_pct']:+.2f}%)",
        f"Cumulative P&L  : ${summary['cumulative_pnl']:,.2f}  ({summary['cumulative_pnl_pct']:+.2f}%)",
        "",
        f"Market read: {summary.get('market_assessment') or '—'}",
        "",
        "Positions:",
    ]
    if summary["positions"]:
        for ticker, p in summary["positions"].items():
            lines.append(
                f"  - {ticker}: {p['quantity']:.4f} @ avg ${p['avg_price']:,.2f} "
                f"-> ${p['market_value']:,.2f} ({p['weight_pct']:.1f}%)"
            )
    else:
        lines.append("  - 100% cash, no open positions.")

    lines += ["", "Today's actions:"]
    lines += [f"  - {a}" for a in summary["trade_actions"]]

    lines += ["", "Top headlines:"]
    lines += [f"  - {h}" for h in summary["headlines"][:5]] or ["  - (none)"]

    lines += ["", "Reasoning:", summary.get("reasoning") or "—"]

    return _send(subject, "\n".join(lines))


def send_failure_alert(date: str, error: str) -> bool:
    """Email a loud alert when a cycle fails outright."""
    subject = f"🚨 Trading Sim R2 — RUN FAILED ({date})"
    body = (
        f"The trading cycle for {date} failed.\n\n"
        f"Error: {error}\n\n"
        "The portfolio was NOT modified (atomic writes protect it). "
        "Check errors.log on the host for the full traceback."
    )
    return _send(subject, body)
