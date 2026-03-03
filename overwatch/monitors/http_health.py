"""HTTP health check monitor: async polling via httpx."""

from __future__ import annotations

from typing import Any

import httpx
from rich.text import Text

from overwatch.monitors import BaseMonitor, register_monitor


@register_monitor("http_health")
class HttpHealthMonitor(BaseMonitor):
    title = "Health"
    refresh_interval = 10.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._endpoints: list[dict] = self.config.get("endpoints", [])
        self._client: httpx.AsyncClient | None = None
        self._statuses: dict[str, tuple[str, str]] = {}  # label → (status, style)

    async def start(self) -> None:
        self._client = httpx.AsyncClient()

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()

    async def poll(self) -> Text:
        text = Text()

        if not self._endpoints:
            text.append("No endpoints", style="dim")
            return text

        if not self._client:
            self._client = httpx.AsyncClient()

        for ep in self._endpoints:
            url = ep.get("url", "")
            label = ep.get("label", url)
            timeout = ep.get("timeout", 3)

            try:
                resp = await self._client.get(url, timeout=timeout)
                if resp.status_code < 400:
                    self._statuses[label] = (f"{resp.status_code}", "green")
                else:
                    self._statuses[label] = (f"{resp.status_code}", "red")
            except httpx.TimeoutException:
                self._statuses[label] = ("TIMEOUT", "red")
            except httpx.ConnectError:
                self._statuses[label] = ("DOWN", "red")
            except Exception as e:
                self._statuses[label] = ("ERROR", "red")

        for label, (status, style) in self._statuses.items():
            indicator = "\u25cf" if style == "green" else "\u25cb"
            text.append(f"{indicator} ", style=style)
            text.append(f"{label} ", style="bold")
            text.append(f"{status}\n", style=style)

        if text.plain.endswith("\n"):
            text.right_crop(1)

        return text
