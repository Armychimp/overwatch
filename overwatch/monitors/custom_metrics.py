"""Custom metrics monitor: reads IPC MetricsStore snapshots."""

from __future__ import annotations

from typing import Any, Callable

from rich.text import Text

from overwatch.monitors import BaseMonitor, register_monitor


@register_monitor("custom_metrics")
class CustomMetricsMonitor(BaseMonitor):
    title = "Metrics"
    refresh_interval = 1.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._store_getter: Callable | None = config.get("_store_getter") if config else None

    async def poll(self) -> Text:
        text = Text()

        if not self._store_getter:
            text.append("No IPC", style="dim")
            return text

        snapshot = self._store_getter()
        if not snapshot:
            text.append("No metrics yet", style="dim")
            return text

        for name, info in snapshot.items():
            if name.startswith("_"):
                # Special entries like _heartbeat
                if name == "_heartbeat":
                    ago = info.get("ago", "?")
                    style = "green" if isinstance(ago, (int, float)) and ago < 10 else "yellow"
                    text.append("\u2764 ", style=style)
                    text.append(f"{ago}s ago\n", style=style)
                continue

            mtype = info.get("type", "")
            if mtype == "gauge":
                text.append(f"{name} ", style="dim")
                text.append(f"{info['value']}", style="bold cyan")
                labels = info.get("labels", {})
                if labels:
                    label_str = " ".join(f"{k}={v}" for k, v in labels.items())
                    text.append(f" ({label_str})", style="dim")
                text.append("\n")
            elif mtype == "counter":
                text.append(f"{name} ", style="dim")
                text.append(f"{info['value']}", style="bold green")
                text.append("\n")
            elif mtype == "timing":
                text.append(f"{name} ", style="dim")
                text.append(f"{info['last']:.1f}ms", style="bold yellow")
                text.append(f" avg={info['avg']:.1f}ms", style="dim")
                text.append("\n")

        # Remove trailing newline
        if text.plain.endswith("\n"):
            text.right_crop(1)

        return text
