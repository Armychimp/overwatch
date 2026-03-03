"""Public SDK API: gauge(), counter(), timing(), heartbeat().

All functions are no-ops when OVERWATCH_IPC is not set.
"""

from __future__ import annotations

from typing import Any

from sdk._transport import get_transport

# Singleton transport, initialized on first use
_transport = None


def _get_transport():
    global _transport
    if _transport is None:
        _transport = get_transport()
    return _transport


def gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Set a gauge metric."""
    _get_transport().send({
        "type": "gauge",
        "name": name,
        "value": value,
        "labels": labels or {},
    })


def counter(name: str, value: float = 1) -> None:
    """Increment a counter metric."""
    _get_transport().send({
        "type": "counter",
        "name": name,
        "value": value,
    })


def timing(name: str, value: float) -> None:
    """Record a timing metric in milliseconds."""
    _get_transport().send({
        "type": "timing",
        "name": name,
        "value": value,
    })


def heartbeat() -> None:
    """Send a heartbeat signal."""
    _get_transport().send({"type": "heartbeat"})
