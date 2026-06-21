"""Shared helpers: structured logging, retry-with-backoff, and atomic file I/O.

Kept dependency-free (stdlib only) so every module can import it safely.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import tempfile
import time
from typing import Any, Callable, TypeVar

HERE = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG = os.path.join(HERE, "errors.log")

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Logging — console + errors.log
# --------------------------------------------------------------------------- #
def _build_logger() -> logging.Logger:
    logger = logging.getLogger("trading_sim")
    if logger.handlers:  # already configured (e.g. re-import)
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Errors (and worse) are persisted to errors.log for unattended runs.
    file_handler = logging.FileHandler(ERROR_LOG)
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Info+ goes to the console for live visibility.
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    return logger


log = _build_logger()


def log_error(message: str, exc: Exception | None = None) -> None:
    """Record an error to both console and errors.log."""
    if exc is not None:
        log.error("%s -> %s: %s", message, type(exc).__name__, exc)
    else:
        log.error(message)


# --------------------------------------------------------------------------- #
# Retry decorator — exponential backoff
# --------------------------------------------------------------------------- #
def retry(
    attempts: int = 3,
    base_delay: float = 2.0,
    label: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a callable up to `attempts` times with exponential backoff.

    Re-raises the final exception if every attempt fails so callers can decide
    how to degrade gracefully.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        name = label or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentional broad retry
                    last_exc = exc
                    if attempt < attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        log.warning(
                            "%s failed (attempt %d/%d): %s — retrying in %.0fs",
                            name, attempt, attempts, exc, delay,
                        )
                        time.sleep(delay)
                    else:
                        log_error(f"{name} failed after {attempts} attempts", exc)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
# Atomic JSON read / write — never corrupt portfolio.json
# --------------------------------------------------------------------------- #
def read_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json_atomic(path: str, data: Any) -> None:
    """Write JSON by dumping to a temp file in the same dir, then atomic rename.

    A crash mid-write leaves the original file untouched.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)  # atomic on POSIX and Windows
    except Exception:
        # Clean up the temp file on failure so we don't litter the directory.
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
