"""Main Textual App for Overwatch TUI."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from overwatch.config import AppConfig
from overwatch.ipc import IPCServer
from overwatch.process import ProcessManager, ProcessInfo, ProcessState
from overwatch.widgets.log_panel import LogPanel
from overwatch.widgets.monitor_sidebar import MonitorSidebar
from overwatch.widgets.status_bar import StatusBar


class OverwatchApp(App):
    """TUI process monitor application."""

    CSS_PATH = "app.tcss"
    TITLE = "Overwatch"

    BINDINGS = []  # We handle keys manually via on_key

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._ipc = IPCServer()
        self._process: ProcessManager | None = None
        self._log_panel: LogPanel | None = None
        self._sidebar: MonitorSidebar | None = None
        self._status_bar: StatusBar | None = None
        self._sidebar_visible = True

    def compose(self) -> ComposeResult:
        self._log_panel = LogPanel(
            max_lines=self.config.log.max_lines,
            wrap=self.config.log.wrap,
            show_timestamp=self.config.log.timestamp,
            id="log-panel",
        )
        yield self._log_panel

        # Build monitor context with injected getters
        monitor_context = {
            "process_stats": {
                "_process_getter": lambda: (
                    self._process.get_psutil_process() if self._process else None
                ),
            },
            "custom_metrics": {
                "_store_getter": lambda: self._ipc.store.snapshot(),
            },
        }

        self._sidebar = MonitorSidebar(
            self.config.monitors,
            context=monitor_context,
            id="monitor-sidebar",
        )
        yield self._sidebar

        self._status_bar = StatusBar(self.config.hotkeys)
        yield self._status_bar

    async def on_mount(self) -> None:
        # Start IPC server
        socket_path = await self._ipc.start()

        # Create and start process
        self._process = ProcessManager(
            command=self.config.command,
            env=self.config.env,
            on_output=self._on_process_output,
            on_state_change=self._on_state_change,
            ipc_socket_path=socket_path,
        )
        await self._process.start()

    async def _on_process_output(self, line: str) -> None:
        if self._log_panel:
            self._log_panel.write_line(line)

    async def _on_state_change(self, info: ProcessInfo) -> None:
        if self._status_bar:
            self._status_bar.process_state = info.state.value

    async def on_key(self, event) -> None:
        hk = self.config.hotkeys
        key = event.character or event.key

        if key == hk.quit:
            await self._do_quit()
        elif key == hk.kill:
            await self._do_kill()
        elif key == hk.reload:
            await self._do_reload()
        elif key == hk.clear:
            self._do_clear()
        elif key == hk.toggle_scroll:
            self._do_toggle_scroll()
        elif key == hk.toggle_sidebar:
            self._do_toggle_sidebar()

    async def _shutdown(self) -> None:
        """Clean up process and IPC on exit."""
        if self._process and self._process.is_running:
            await self._process.kill()
        await self._ipc.stop()

    async def _do_quit(self) -> None:
        await self._shutdown()
        self.exit()

    async def _do_kill(self) -> None:
        if self._process and self._process.is_running:
            if self._log_panel:
                self._log_panel.write_line("\x1b[33m--- process killed ---\x1b[0m")
            await self._process.kill()

    async def _do_reload(self) -> None:
        if self._process:
            if self._log_panel:
                self._log_panel.write_line("\x1b[36m--- reloading ---\x1b[0m")
            self._ipc.store.clear()
            await self._process.reload()

    def _do_clear(self) -> None:
        if self._log_panel:
            self._log_panel.clear()

    def _do_toggle_scroll(self) -> None:
        if self._log_panel:
            active = self._log_panel.toggle_auto_scroll()
            if self._status_bar:
                self._status_bar.scroll_active = active

    def _do_toggle_sidebar(self) -> None:
        if self._sidebar:
            self._sidebar_visible = not self._sidebar_visible
            self._sidebar.display = self._sidebar_visible

    async def action_quit(self) -> None:
        """Handle Textual's built-in quit (ctrl+c)."""
        await self._shutdown()
        self.exit()
