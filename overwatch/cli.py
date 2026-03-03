"""CLI entry point: argparse, load config, launch app."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from overwatch.config import AppConfig


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="overwatch",
        description="TUI process monitor with pluggable monitors",
    )
    parser.add_argument(
        "config_or_command",
        nargs="?",
        help="Path to overwatch.yaml config file, or a command to run",
    )
    parser.add_argument(
        "--command", "-c",
        help="Command to run (overrides config file command)",
    )
    args = parser.parse_args(argv)

    config: AppConfig | None = None

    if args.config_or_command:
        p = Path(args.config_or_command)
        if p.suffix in (".yaml", ".yml") and p.exists():
            config = AppConfig.from_yaml(p)
        else:
            # Treat as a command
            config = AppConfig.default(args.config_or_command)

    if args.command:
        if config is None:
            config = AppConfig.default(args.command)
        else:
            config.command = args.command

    if config is None:
        # Try default config file
        default_path = Path("overwatch.yaml")
        if default_path.exists():
            config = AppConfig.from_yaml(default_path)
        else:
            parser.print_help()
            sys.exit(1)

    if not config.command:
        print("Error: no command specified", file=sys.stderr)
        sys.exit(1)

    from overwatch.app import OverwatchApp

    app = OverwatchApp(config)
    app.run()
