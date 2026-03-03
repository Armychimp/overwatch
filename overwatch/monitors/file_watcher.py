"""File watcher monitor: glob + os.stat polling."""

from __future__ import annotations

import glob
import os
import time
from typing import Any

from rich.text import Text

from overwatch.monitors import BaseMonitor, register_monitor


@register_monitor("file_watcher")
class FileWatcherMonitor(BaseMonitor):
    title = "Files"
    refresh_interval = 5.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._patterns: list[str] = self.config.get("paths", [])
        self._prev_state: dict[str, float] = {}

    async def poll(self) -> Text:
        text = Text()

        if not self._patterns:
            text.append("No paths configured", style="dim")
            return text

        current_state: dict[str, float] = {}
        changed: list[str] = []
        new_files: list[str] = []

        for pattern in self._patterns:
            for path in glob.glob(pattern, recursive=True):
                try:
                    mtime = os.stat(path).st_mtime
                    current_state[path] = mtime

                    if path in self._prev_state:
                        if mtime != self._prev_state[path]:
                            changed.append(path)
                    else:
                        new_files.append(path)
                except OSError:
                    pass

        total = len(current_state)
        text.append(f"Watching {len(self._patterns)} pattern(s)\n", style="dim")
        text.append(f"{total} files matched\n", style="cyan")

        if changed:
            text.append(f"{len(changed)} changed\n", style="yellow")
            for f in changed[:3]:
                text.append(f"  {os.path.basename(f)}\n", style="yellow")

        if new_files and self._prev_state:  # Only show new after first poll
            text.append(f"{len(new_files)} new\n", style="green")
            for f in new_files[:3]:
                text.append(f"  {os.path.basename(f)}\n", style="green")

        self._prev_state = current_state

        # Remove trailing newline
        if text.plain.endswith("\n"):
            text.right_crop(1)

        return text
