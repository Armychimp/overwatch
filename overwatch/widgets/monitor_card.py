"""Single monitor display card widget."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from overwatch.monitors import BaseMonitor


class MonitorCard(Vertical):
    """A card that displays a single monitor's output with polling."""

    DEFAULT_CSS = """
    MonitorCard {
        height: auto;
        max-height: 12;
        border: solid $surface-lighten-2;
        padding: 0 1;
        margin-bottom: 1;
    }
    MonitorCard .card-title {
        text-style: bold;
        color: $text;
        padding: 0;
        margin: 0;
    }
    MonitorCard .card-body {
        padding: 0;
        margin: 0;
    }
    """

    def __init__(self, monitor: BaseMonitor, **kwargs):
        super().__init__(**kwargs)
        self.monitor = monitor
        self._title_widget = Static(monitor.title, classes="card-title")
        self._body_widget = Static("...", classes="card-body")
        self._timer = None

    def compose(self) -> ComposeResult:
        yield self._title_widget
        yield self._body_widget

    async def on_mount(self) -> None:
        await self.monitor.start()
        self._timer = self.set_interval(
            self.monitor.refresh_interval,
            self._poll,
        )
        # Initial poll
        await self._poll()

    async def _poll(self) -> None:
        try:
            result = await self.monitor.poll()
            if isinstance(result, Text):
                self._body_widget.update(result)
            else:
                self._body_widget.update(str(result))
        except Exception as e:
            self._body_widget.update(Text(f"Error: {e}", style="red"))

    async def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()
        await self.monitor.stop()
