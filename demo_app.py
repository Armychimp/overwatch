#!/usr/bin/env python3
"""Demo app for testing Overwatch TUI.

Prints colored output and pushes SDK metrics.
Run with: python -m overwatch overwatch.yaml.example
"""

import os
import sys
import time
import random
import math

# Add parent dir so sdk import works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk import metrics

COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def colorize(text: str, *styles: str) -> str:
    prefix = "".join(COLORS.get(s, "") for s in styles)
    return f"{prefix}{text}{COLORS['reset']}"


def main():
    print(colorize("=== Demo App Started ===", "bold", "cyan"))
    print(colorize(f"PID: {os.getpid()}", "dim"))
    print(colorize(f"IPC: {os.environ.get('OVERWATCH_IPC', 'not set')}", "dim"))
    print()

    queue_depth = 0
    request_count = 0
    iteration = 0

    try:
        while True:
            iteration += 1

            # Simulate work
            action = random.choice(["request", "enqueue", "dequeue", "error", "info"])

            if action == "request":
                duration = random.uniform(10, 500)
                status = random.choice([200, 200, 200, 201, 400, 500])
                color = "green" if status < 400 else "yellow" if status < 500 else "red"
                print(colorize(
                    f"[{iteration:04d}] {action.upper()} status={status} duration={duration:.1f}ms",
                    color,
                ))
                request_count += 1
                metrics.counter("requests_total")
                metrics.timing("request_duration_ms", duration)

            elif action == "enqueue":
                n = random.randint(1, 5)
                queue_depth += n
                print(colorize(f"[{iteration:04d}] ENQUEUE +{n} (depth={queue_depth})", "blue"))
                metrics.gauge("queue_depth", queue_depth)

            elif action == "dequeue":
                n = min(random.randint(1, 3), queue_depth)
                queue_depth -= n
                print(colorize(f"[{iteration:04d}] DEQUEUE -{n} (depth={queue_depth})", "magenta"))
                metrics.gauge("queue_depth", queue_depth)

            elif action == "error":
                print(colorize(f"[{iteration:04d}] ERROR: Something went wrong!", "bold", "red"))

            else:
                cpu_sim = 30 + 20 * math.sin(iteration / 10)
                print(colorize(
                    f"[{iteration:04d}] INFO: Processing batch, simulated_load={cpu_sim:.0f}%",
                    "dim",
                ))
                metrics.gauge("simulated_load", round(cpu_sim, 1), {"unit": "percent"})

            # Heartbeat every 5 iterations
            if iteration % 5 == 0:
                metrics.heartbeat()

            # Sleep to simulate work
            time.sleep(random.uniform(0.5, 2.0))

    except KeyboardInterrupt:
        print(colorize("\n=== Demo App Shutting Down ===", "bold", "yellow"))
        sys.exit(0)


if __name__ == "__main__":
    main()
