"""Unix domain socket IPC server + MetricsStore."""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MetricValue:
    name: str
    type: str  # gauge, counter, timing
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    updated_at: float = 0.0


class MetricsStore:
    """Thread-safe store for metrics received over IPC."""

    def __init__(self):
        self._gauges: dict[str, MetricValue] = {}
        self._counters: dict[str, float] = {}
        self._timings: dict[str, list[float]] = {}
        self._last_heartbeat: float = 0.0

    def process_message(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        name = msg.get("name", "")
        value = msg.get("value", 0)
        labels = msg.get("labels", {})
        now = time.time()

        if msg_type == "gauge":
            self._gauges[name] = MetricValue(
                name=name, type="gauge", value=value,
                labels=labels, updated_at=now,
            )
        elif msg_type == "counter":
            self._counters[name] = self._counters.get(name, 0) + value
        elif msg_type == "timing":
            if name not in self._timings:
                self._timings[name] = []
            self._timings[name].append(value)
            # Keep last 100
            if len(self._timings[name]) > 100:
                self._timings[name] = self._timings[name][-100:]
        elif msg_type == "heartbeat":
            self._last_heartbeat = now

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        result: dict[str, Any] = {}

        for name, mv in self._gauges.items():
            result[name] = {"type": "gauge", "value": mv.value, "labels": mv.labels}

        for name, total in self._counters.items():
            result[name] = {"type": "counter", "value": total}

        for name, values in self._timings.items():
            if values:
                result[name] = {
                    "type": "timing",
                    "last": values[-1],
                    "avg": sum(values) / len(values),
                    "count": len(values),
                }

        if self._last_heartbeat > 0:
            result["_heartbeat"] = {
                "type": "heartbeat",
                "ago": round(now - self._last_heartbeat, 1),
            }

        return result

    def clear(self) -> None:
        self._gauges.clear()
        self._counters.clear()
        self._timings.clear()
        self._last_heartbeat = 0.0


class IPCServer:
    """Async Unix domain socket server for receiving SDK metrics."""

    def __init__(self):
        self.store = MetricsStore()
        self._server: asyncio.AbstractServer | None = None
        self._socket_path: str = ""

    @property
    def socket_path(self) -> str:
        return self._socket_path

    async def start(self) -> str:
        self._socket_path = f"/tmp/overwatch-{os.getpid()}.sock"
        # Clean up stale socket
        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)

        self._server = await asyncio.start_unix_server(
            self._handle_client, path=self._socket_path,
        )
        return self._socket_path

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            buf = b""
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        self.store.process_message(msg)
                    except json.JSONDecodeError:
                        pass
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if self._socket_path and os.path.exists(self._socket_path):
            os.unlink(self._socket_path)
