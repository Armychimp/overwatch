"""Process stats monitor: CPU, memory, threads via psutil."""

from __future__ import annotations

from typing import Any

import psutil
from rich.text import Text

from overwatch.monitors import BaseMonitor, register_monitor


@register_monitor("process_stats")
class ProcessStatsMonitor(BaseMonitor):
    title = "Process"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._process_getter = config.get("_process_getter") if config else None

    async def poll(self) -> Text:
        text = Text()

        proc = self._process_getter() if self._process_getter else None
        if proc is None:
            text.append("No process", style="dim")
            return text

        try:
            with proc.oneshot():
                cpu = proc.cpu_percent(interval=0)
                mem = proc.memory_info()
                threads = proc.num_threads()
                try:
                    fds = proc.num_fds()
                except (psutil.AccessDenied, AttributeError):
                    fds = None

            mem_mb = mem.rss / (1024 * 1024)

            text.append("PID ", style="dim")
            text.append(str(proc.pid), style="bold cyan")
            text.append("\n")

            text.append("CPU ", style="dim")
            cpu_style = "green" if cpu < 50 else "yellow" if cpu < 80 else "red"
            text.append(f"{cpu:.1f}%", style=cpu_style)
            text.append("\n")

            text.append("MEM ", style="dim")
            mem_style = "green" if mem_mb < 256 else "yellow" if mem_mb < 512 else "red"
            text.append(f"{mem_mb:.1f} MB", style=mem_style)
            text.append("\n")

            text.append("THR ", style="dim")
            text.append(str(threads), style="cyan")

            if fds is not None:
                text.append("  FDs ", style="dim")
                text.append(str(fds), style="cyan")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            text.append("Process gone", style="red")

        return text
