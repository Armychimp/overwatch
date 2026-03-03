#!/usr/bin/env python3
"""
Example instrumented app for Overwatch.

Run with:
    cd /mnt/z/AI/tools/overwatch
    source venv/bin/activate
    python -m overwatch "python example_app.py"

Or standalone (SDK calls become no-ops):
    python example_app.py
"""

import sys
import os
import time
import random

# --- Overwatch SDK setup (2 lines) ---
sys.path.insert(0, "/mnt/z/AI/tools/overwatch")
from sdk import metrics


def main():
    print("\033[1;36m=== Example App Started ===\033[0m")
    print(f"PID: {os.getpid()}")

    items = list(range(100))
    metrics.gauge("total_items", len(items))

    for i, item in enumerate(items):
        # Simulate work
        duration = random.uniform(0.1, 0.8)
        time.sleep(duration)

        # Track timing
        metrics.timing("process_ms", duration * 1000)

        # Track progress
        metrics.counter("processed")
        metrics.gauge("progress_pct", round((i + 1) / len(items) * 100, 1))

        # Simulate occasional errors
        if random.random() < 0.05:
            metrics.counter("errors")
            print(f"\033[31m[ERROR] Item {item} failed\033[0m")
        else:
            print(f"\033[32m[OK]\033[0m Processed item {item} in {duration*1000:.0f}ms")

        # Heartbeat every 5 items
        if i % 5 == 0:
            metrics.heartbeat()

    print("\033[1;36m=== Done ===\033[0m")


if __name__ == "__main__":
    main()
