"""Dead man's switch via an external cron monitor (healthchecks.io-style).

The agent can't detect its own missed runs — if the process never starts, no
code runs to notice. So we ping an external monitor on every successful cycle.
If a ping doesn't arrive within the window you configure on that service, *it*
alerts you (email/SMS/Slack). On failure we hit the `/fail` endpoint so the
monitor flags the run immediately instead of waiting for the grace period.

Compatible with healthchecks.io, Better Stack, Cronitor, etc. — set
HEARTBEAT_URL to your check's ping URL. If unset, heartbeats are skipped.

    HEARTBEAT_URL   e.g. https://hc-ping.com/<uuid>
"""

from __future__ import annotations

import os

import requests

from utils import log

PING_TIMEOUT = 10


def _base_url() -> str | None:
    url = os.getenv("HEARTBEAT_URL", "").strip()
    return url.rstrip("/") or None


def _ping(suffix: str = "", payload: str | None = None) -> bool:
    """Hit the heartbeat URL (+ optional suffix). Never raises."""
    base = _base_url()
    if not base:
        return False
    url = base + suffix
    for attempt in range(1, 4):
        try:
            requests.post(url, data=(payload or "").encode("utf-8"), timeout=PING_TIMEOUT)
            log.info("Heartbeat ping%s sent", suffix or " (success)")
            return True
        except Exception as exc:  # noqa: BLE001 - heartbeat must never break a run
            log.warning("Heartbeat ping%s failed (attempt %d/3): %s",
                        suffix or "", attempt, exc)
            if attempt < 3:
                import time
                time.sleep(2 * attempt)
    return False


def ping_start() -> bool:
    """Signal that a run has begun (lets the monitor measure run duration)."""
    return _ping("/start")


def ping_success(message: str | None = None) -> bool:
    """Signal a successful run — resets the dead man's switch timer."""
    return _ping("", message)


def ping_failure(message: str | None = None) -> bool:
    """Signal a failed run — flags the monitor immediately."""
    return _ping("/fail", message)
