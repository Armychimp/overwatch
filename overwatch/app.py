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

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._ipc = IPCServer()
        self._process: ProcessManager | None = None
        self._log_panel: LogPanel | None = None
        self._sidebar: MonitorSidebar | None = None
        self._status_bar: StatusBar | None = None
        self._sidebar_visible = True

        # Build BINDINGS from config hotkeys
        hk = config.hotkeys
        self._bindings_list = [
            Binding(hk.quit, "ow_quit", "Quit", priority=True),
            Binding(hk.kill, "ow_kill", "Kill", priority=True),
            Binding(hk.reload, "ow_reload", "Reload", priority=True),
            Binding(hk.clear, "ow_clear", "Clear", priority=True),
            Binding(hk.toggle_scroll, "ow_toggle_scroll", "Scroll", priority=True),
            Binding(hk.toggle_sidebar, "ow_toggle_sidebar", "Sidebar", priority=True),
        ]

    def compose(self) -> ComposeResult:
        # Docked widgets first
        self._status_bar = StatusBar(self.config.hotkeys)
        yield self._status_bar

        # Main content area (horizontal layout from CSS)
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

    async def on_mount(self) -> None:
        # Register bindings dynamically (from config hotkeys)
        for binding in self._bindings_list:
            self._bindings.bind(
                binding.key, binding.action, binding.description,
                priority=binding.priority,
            )

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

    async def _shutdown(self) -> None:
        """Clean up process and IPC on exit."""
        if self._process and self._process.is_running:
            await self._process.kill()
        await self._ipc.stop()

    async def action_ow_quit(self) -> None:
        await self._shutdown()
        self.exit()

    async def action_ow_kill(self) -> None:
        if self._process and self._process.is_running:
            if self._log_panel:
                self._log_panel.write_line("\x1b[33m--- process killed ---\x1b[0m")
            await self._process.kill()

    async def action_ow_reload(self) -> None:
        if self._process:
            if self._log_panel:
                self._log_panel.write_line("\x1b[36m--- reloading ---\x1b[0m")
            self._ipc.store.clear()
            await self._process.reload()

    def action_ow_clear(self) -> None:
        if self._log_panel:
            self._log_panel.clear()

    def action_ow_toggle_scroll(self) -> None:
        if self._log_panel:
            active = self._log_panel.toggle_auto_scroll()
            if self._status_bar:
                self._status_bar.scroll_active = active

    def action_ow_toggle_sidebar(self) -> None:
        if self._sidebar:
            self._sidebar_visible = not self._sidebar_visible
            self._sidebar.display = self._sidebar_visible

    async def action_quit(self) -> None:
        """Handle Textual's built-in quit (ctrl+c)."""
        await self._shutdown()
        self.exit()
