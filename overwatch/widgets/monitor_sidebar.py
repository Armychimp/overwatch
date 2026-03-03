"""Monitor sidebar: vertical container of monitor cards."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll

from overwatch.config import MonitorEntry
from overwatch.monitors import create_monitor
from overwatch.widgets.monitor_card import MonitorCard


class MonitorSidebar(VerticalScroll):
    """Scrollable sidebar containing monitor cards."""

    DEFAULT_CSS = """
    MonitorSidebar {
        width: 28;
        min-width: 24;
        border-left: solid $surface-lighten-2;
        scrollbar-size: 1 1;
    }
    """

    def __init__(
        self,
        monitor_configs: list[MonitorEntry],
        context: dict | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._monitor_configs = monitor_configs
        self._context = context or {}
        self._cards: list[MonitorCard] = []

    def compose(self) -> ComposeResult:
        for entry in self._monitor_configs:
            config = {
                "refresh": entry.refresh,
                "paths": entry.paths,
                "endpoints": entry.endpoints,
            }
            # Inject context (process getter, store getter, etc.)
            config.update(self._context.get(entry.type, {}))

            try:
                monitor = create_monitor(entry.type, config)
                card = MonitorCard(monitor)
                self._cards.append(card)
                yield card
            except ValueError as e:
                # Unknown monitor type - skip
                pass
