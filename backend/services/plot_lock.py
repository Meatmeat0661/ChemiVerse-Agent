"""Serialize matplotlib plot jobs so one small VM does not run several at once."""

from __future__ import annotations

import threading

_plot_lock = threading.Lock()


def try_acquire_plot_lock(timeout: float | None = 600.0) -> bool:
    """Wait up to `timeout` seconds for the plot lock (None = block forever)."""
    if timeout is None:
        return _plot_lock.acquire(blocking=True)
    return _plot_lock.acquire(blocking=True, timeout=timeout)


def release_plot_lock() -> None:
    if _plot_lock.locked():
        _plot_lock.release()
