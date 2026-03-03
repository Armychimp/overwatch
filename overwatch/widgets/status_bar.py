"""Bottom status bar with hotkey hints and process status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from overwatch.config import HotkeyConfig
from overwatch.process import ProcessState


class StatusBar(Horizontal):
    """Bottom bar showing hotkey hints and process status."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    StatusBar .hotkeys {
        width: 1fr;
    }
    StatusBar .status {
        width: auto;
        text-align: right;
    }
    """

    process_state: reactive[str] = reactive("STOP")
    scroll_active: reactive[bool] = reactive(True)

    def __init__(self, hotkeys: HotkeyConfig, **kwargs):
        super().__init__(**kwargs)
        self._hotkeys = hotkeys
        self._hotkey_text = Static("", classes="hotkeys")
        self._status_text = Static("", classes="status")

    def compose(self) -> ComposeResult:
        yield self._hotkey_text
        yield self._status_text

    def on_mount(self) -> None:
        self._update_hotkeys()
        self._update_status()

    def _update_hotkeys(self) -> None:
        hk = self._hotkeys
        scroll_label = "scroll:on" if self.scroll_active else "scroll:off"
        parts = [
            f"[{hk.reload}]eload",
            f"[{hk.kill}]ill",
            f"[{hk.clear}]lear",
            f"[{hk.toggle_scroll}]{scroll_label}",
            f"[{hk.toggle_sidebar}]sidebar",
            f"[{hk.quit}]uit",
        ]
        self._hotkey_text.update(" ".join(parts))

    def watch_process_state(self, state: str) -> None:
        self._update_status()

    def watch_scroll_active(self, active: bool) -> None:
        self._update_hotkeys()

    def _update_status(self) -> None:
        state = self.process_state
        if state == "RUN":
            icon = "\u25b6"
            style = "green"
        elif state == "STOP":
            icon = "\u25a0"
            style = "red"
        elif state == "START":
            icon = "\u25b7"
            style = "yellow"
        elif state == "KILL":
            icon = "\u2716"
            style = "yellow"
        else:
            icon = "?"
            style = "dim"
        self._status_text.update(f"[{style}]{icon} {state}[/{style}]")
