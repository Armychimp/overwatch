"""Thread-safe Unix socket writer for SDK metrics."""

from __future__ import annotations

import json
import os
import socket
import threading
from typing import Any


class _NullTransport:
    """No-op transport when not running under Overwatch."""

    def send(self, msg: dict[str, Any]) -> None:
        pass

    def close(self) -> None:
        pass


class _SocketTransport:
    """Thread-safe Unix domain socket writer with lazy connect."""

    def __init__(self, path: str):
        self._path = path
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._connected = False

    def _connect(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.connect(self._path)
            self._connected = True
            return True
        except (OSError, ConnectionRefusedError):
            self._sock = None
            self._connected = False
            return False

    def send(self, msg: dict[str, Any]) -> None:
        with self._lock:
            if not self._connected:
                if not self._connect():
                    return
            try:
                data = json.dumps(msg) + "\n"
                self._sock.sendall(data.encode("utf-8"))
            except (OSError, BrokenPipeError):
                # Lost connection, will retry next send
                self._connected = False
                self._sock = None

    def close(self) -> None:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
                self._connected = False


def get_transport() -> _NullTransport | _SocketTransport:
    """Return the appropriate transport based on environment."""
    path = os.environ.get("OVERWATCH_IPC")
    if path:
        return _SocketTransport(path)
    return _NullTransport()
