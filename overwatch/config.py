"""YAML config loading into dataclasses."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LogConfig:
    max_lines: int = 10000
    wrap: bool = True
    timestamp: bool = False


@dataclass
class HotkeyConfig:
    kill: str = "k"
    reload: str = "r"
    clear: str = "c"
    quit: str = "q"
    toggle_scroll: str = "s"
    toggle_sidebar: str = "b"


@dataclass
class MonitorEntry:
    type: str = "process_stats"
    refresh: float = 2.0
    paths: list[str] = field(default_factory=list)
    endpoints: list[dict] = field(default_factory=list)


@dataclass
class AppConfig:
    command: str = ""
    env: dict[str, str] = field(default_factory=dict)
    log: LogConfig = field(default_factory=LogConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    monitors: list[MonitorEntry] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return cls._from_dict(raw)

    @classmethod
    def _from_dict(cls, d: dict) -> AppConfig:
        log_raw = d.get("log", {})
        log = LogConfig(**{k: v for k, v in log_raw.items() if k in LogConfig.__dataclass_fields__})

        hk_raw = d.get("hotkeys", {})
        hotkeys = HotkeyConfig(**{k: v for k, v in hk_raw.items() if k in HotkeyConfig.__dataclass_fields__})

        monitors = []
        for m in d.get("monitors", []):
            monitors.append(MonitorEntry(
                type=m.get("type", "process_stats"),
                refresh=m.get("refresh", 2.0),
                paths=m.get("paths", []),
                endpoints=m.get("endpoints", []),
            ))

        env = d.get("env", {})
        # Ensure strings
        env = {str(k): str(v) for k, v in env.items()}

        return cls(
            command=d.get("command", ""),
            env=env,
            log=log,
            hotkeys=hotkeys,
            monitors=monitors,
        )

    @classmethod
    def default(cls, command: str) -> AppConfig:
        """Create a default config for a command with no YAML file."""
        return cls(
            command=command,
            env={"PYTHONUNBUFFERED": "1"},
            monitors=[MonitorEntry(type="process_stats", refresh=2.0)],
        )
