# Overwatch Integration Guide

## Quick Start

Add Overwatch monitoring to any Python script in two steps:

### 1. Add the SDK to your script

```python
import sys, os
sys.path.insert(0, "/mnt/z/AI/tools/overwatch")
from sdk import metrics
```

### 2. Instrument your code

```python
# Gauges - current values that go up and down
metrics.gauge("queue_depth", 42)
metrics.gauge("temperature", 72.5, {"unit": "fahrenheit", "sensor": "main"})

# Counters - cumulative values that only increase
metrics.counter("requests_total")          # +1
metrics.counter("bytes_processed", 4096)   # +4096

# Timings - track durations in milliseconds
metrics.timing("request_duration_ms", 123.4)
metrics.timing("db_query_ms", 45.2)

# Heartbeat - prove the app is alive
metrics.heartbeat()
```

All calls are **no-ops** when not running under Overwatch. Zero overhead, no errors, no conditional logic needed.

### 3. Run under Overwatch

```bash
cd /mnt/z/AI/tools/overwatch
source venv/bin/activate

# Direct command
python -m overwatch "python /path/to/your/script.py"

# Or with a config file
python -m overwatch your_config.yaml
```

## YAML Config Template

Create a `your_config.yaml`:

```yaml
command: "python /path/to/your/script.py --your-args"

env:
  PYTHONUNBUFFERED: "1"
  # Any env vars your script needs:
  # API_KEY: "xxx"

log:
  max_lines: 10000
  wrap: true
  timestamp: false    # set true to prefix lines with HH:MM:SS

hotkeys:
  kill: "k"
  reload: "r"
  clear: "c"
  quit: "q"
  toggle_scroll: "s"
  toggle_sidebar: "b"

monitors:
  # Always include - shows PID, CPU, memory, threads
  - type: process_stats
    refresh: 2

  # Include if your script uses the SDK
  - type: custom_metrics

  # Include to watch output files
  - type: file_watcher
    paths: ["./output/*.png", "./logs/*.log"]
    refresh: 5

  # Include to monitor HTTP services
  - type: http_health
    endpoints:
      - url: "http://localhost:8080/health"
        label: "API"
        timeout: 3
    refresh: 10
```

## SDK Reference

### Import

```python
import sys, os
sys.path.insert(0, "/mnt/z/AI/tools/overwatch")
from sdk import metrics
```

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `gauge` | `gauge(name, value, labels=None)` | Set a current value (queue size, temperature, progress %) |
| `counter` | `counter(name, value=1)` | Increment a running total (requests, errors, items processed) |
| `timing` | `timing(name, value)` | Record a duration in ms (latency, processing time) |
| `heartbeat` | `heartbeat()` | Signal the process is alive |

### Labels

Gauges accept an optional `labels` dict for context:

```python
metrics.gauge("gpu_util", 85.2, {"device": "cuda:0"})
metrics.gauge("gpu_util", 42.1, {"device": "cuda:1"})
```

### Timing helper pattern

```python
import time

start = time.perf_counter()
do_work()
elapsed_ms = (time.perf_counter() - start) * 1000
metrics.timing("work_duration_ms", elapsed_ms)
```

### Heartbeat pattern

Call periodically in your main loop so the monitor shows time-since-last-heartbeat:

```python
for i, item in enumerate(work_items):
    process(item)
    if i % 10 == 0:
        metrics.heartbeat()
```

## Common Integration Patterns

### Batch processing script

```python
import sys, os, time
sys.path.insert(0, "/mnt/z/AI/tools/overwatch")
from sdk import metrics

items = load_items()
metrics.gauge("total_items", len(items))

for i, item in enumerate(items):
    start = time.perf_counter()
    result = process(item)
    elapsed = (time.perf_counter() - start) * 1000

    metrics.timing("process_ms", elapsed)
    metrics.counter("processed")
    metrics.gauge("progress_pct", round((i + 1) / len(items) * 100, 1))

    if i % 10 == 0:
        metrics.heartbeat()
```

### Web server / long-running service

```python
import sys, os
sys.path.insert(0, "/mnt/z/AI/tools/overwatch")
from sdk import metrics

# In your request handler:
def handle_request(request):
    start = time.perf_counter()
    metrics.gauge("active_connections", get_connection_count())

    response = do_work(request)

    metrics.timing("request_ms", (time.perf_counter() - start) * 1000)
    metrics.counter("requests_total")
    metrics.counter(f"status_{response.status_code}")
    metrics.heartbeat()
    return response
```

### ComfyUI / image generation workflow

```python
import sys, os
sys.path.insert(0, "/mnt/z/AI/tools/overwatch")
from sdk import metrics

for i, prompt in enumerate(prompts):
    metrics.gauge("current_prompt", i + 1, {"total": str(len(prompts))})

    start = time.perf_counter()
    result = generate_image(prompt)
    metrics.timing("generation_ms", (time.perf_counter() - start) * 1000)

    metrics.counter("images_generated")
    metrics.gauge("vram_used_mb", get_vram_usage())
    metrics.heartbeat()
```

## TUI Hotkeys

While Overwatch is running:

| Key | Action |
|-----|--------|
| `r` | Kill and restart the process |
| `k` | Kill the process (stays in Overwatch) |
| `c` | Clear the log panel |
| `s` | Toggle auto-scroll on/off |
| `b` | Toggle monitor sidebar on/off |
| `q` | Quit Overwatch (kills process) |

## Notes

- **PYTHONUNBUFFERED** is always set to `"1"` automatically so print output streams in real time
- **ANSI colors** are fully supported — use colorama, rich, or raw escape codes in your prints
- **stderr** is merged into stdout so all output appears in one log panel
- The SDK uses a **Unix domain socket** at `/tmp/overwatch-{pid}.sock` — set automatically via `OVERWATCH_IPC` env var
- If the socket is unavailable, all SDK calls silently no-op — your script runs fine standalone
