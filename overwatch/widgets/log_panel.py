"""Log panel widget with RichLog + ANSI color support."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import RichLog


class LogPanel(RichLog):
    """Scrollable log panel that renders ANSI-colored subprocess output."""

    DEFAULT_CSS = """
    LogPanel {
        border: solid $surface-lighten-2;
        scrollbar-size: 1 1;
    }
    """

    def __init__(
        self,
        max_lines: int = 10000,
        wrap: bool = True,
        show_timestamp: bool = False,
        **kwargs,
    ):
        super().__init__(
            highlight=False,
            markup=False,
            wrap=wrap,
            max_lines=max_lines,
            auto_scroll=True,
            **kwargs,
        )
        self._show_timestamp = show_timestamp
        self._auto_scroll = True

    def write_line(self, line: str) -> None:
        """Write a line with ANSI color parsing."""
        text = Text.from_ansi(line)
        if self._show_timestamp:
            import datetime
            ts = datetime.datetime.now().strftime("%H:%M:%S ")
            prefix = Text(ts, style="dim")
            text = Text.assemble(prefix, text)
        self.write(text)

    def toggle_auto_scroll(self) -> bool:
        """Toggle auto-scroll and return new state."""
        self._auto_scroll = not self._auto_scroll
        self.auto_scroll = self._auto_scroll
        return self._auto_scroll
