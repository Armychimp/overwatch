"""Subprocess lifecycle management with asyncio."""

from __future__ import annotations

import asyncio
import os
import signal
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Awaitable

import psutil


class ProcessState(Enum):
    STOPPED = "STOP"
    RUNNING = "RUN"
    STARTING = "START"
    STOPPING = "KILL"


@dataclass
class ProcessInfo:
    pid: int | None = None
    state: ProcessState = ProcessState.STOPPED
    return_code: int | None = None


class ProcessManager:
    """Manages a subprocess lifecycle with kill/reload support."""

    def __init__(
        self,
        command: str,
        env: dict[str, str] | None = None,
        on_output: Callable[[str], Awaitable[None]] | None = None,
        on_state_change: Callable[[ProcessInfo], Awaitable[None]] | None = None,
        ipc_socket_path: str | None = None,
    ):
        self.command = command
        self.extra_env = env or {}
        self.on_output = on_output
        self.on_state_change = on_state_change
        self.ipc_socket_path = ipc_socket_path
        self._process: asyncio.subprocess.Process | None = None
        self._info = ProcessInfo()
        self._read_task: asyncio.Task | None = None

    @property
    def info(self) -> ProcessInfo:
        return self._info

    @property
    def is_running(self) -> bool:
        return self._info.state == ProcessState.RUNNING

    async def start(self) -> None:
        if self._process and self._process.returncode is None:
            return

        await self._set_state(ProcessState.STARTING)

        env = os.environ.copy()
        env.update(self.extra_env)
        env["PYTHONUNBUFFERED"] = "1"
        if self.ipc_socket_path:
            env["OVERWATCH_IPC"] = self.ipc_socket_path

        args = shlex.split(self.command)

        self._process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

        self._info.pid = self._process.pid
        self._info.return_code = None
        await self._set_state(ProcessState.RUNNING)

        self._read_task = asyncio.create_task(self._read_output())

    async def _read_output(self) -> None:
        assert self._process and self._process.stdout
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                # Strip trailing newline but keep ANSI
                text = text.rstrip("\n")
                # Handle carriage returns (progress bars)
                if "\r" in text:
                    parts = text.split("\r")
                    text = parts[-1]
                if self.on_output and text:
                    await self.on_output(text)
        except asyncio.CancelledError:
            pass
        finally:
            if self._process:
                await self._process.wait()
                self._info.return_code = self._process.returncode
                await self._set_state(ProcessState.STOPPED)

    async def kill(self) -> None:
        if not self._process or self._process.returncode is not None:
            return

        await self._set_state(ProcessState.STOPPING)

        try:
            pgid = os.getpgid(self._process.pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

        try:
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                pgid = os.getpgid(self._process.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        self._info.return_code = self._process.returncode
        await self._set_state(ProcessState.STOPPED)

    async def reload(self) -> None:
        await self.kill()
        await self.start()

    async def _set_state(self, state: ProcessState) -> None:
        self._info.state = state
        if self.on_state_change:
            await self.on_state_change(self._info)

    def get_psutil_process(self) -> psutil.Process | None:
        if self._info.pid and self._info.state == ProcessState.RUNNING:
            try:
                return psutil.Process(self._info.pid)
            except psutil.NoSuchProcess:
                return None
        return None
