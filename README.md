# Overwatch

TUI process monitor that wraps any Python subprocess with live ANSI log streaming, configurable hotkeys (kill/reload/clear/quit), and a pluggable monitor sidebar (CPU/mem, custom metrics, file watchers, HTTP health). Instrument your app with a zero-dependency SDK to push gauges, counters, and timings over a Unix socket.

```
┌──────────────────────────────────┬──────────────────┐
│  Live Logs (ANSI colors)         │  Monitors        │
│                                  │  ┌──────────────┐│
│  [0001] REQUEST status=200       │  │ Process      ││
│  [0002] ENQUEUE +3 (depth=7)     │  │ PID 48291    ││
│  [0003] INFO: Processing batch   │  │ CPU 12.3%    ││
│  [0004] REQUEST status=201       │  │ MEM 45.2 MB  ││
│  [0005] DEQUEUE -2 (depth=5)     │  │ THR 4        ││
│  [0006] ERROR: Something broke!  │  └──────────────┘│
│  [0007] REQUEST status=200       │  ┌──────────────┐│
│                                  │  │ Metrics      ││
│                                  │  │ queue_depth 5││
│                                  │  │ requests  47 ││
│                                  │  │ ♥ 2.1s ago   ││
│                                  │  └──────────────┘│
├──────────────────────────────────┴──────────────────┤
│ [r]eload [k]ill [c]lear [s]scroll [b]sidebar [q]uit│
└─────────────────────────────────────────────────────┘
```

## Install

```bash
git clone https://github.com/Armychimp/overwatch.git
cd overwatch
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Requires Python 3.10+, Linux only (Unix domain sockets).

## Quick Start

Run any command:

```bash
python -m overwatch "python my_script.py --verbose"
```

Run with a config file:

```bash
python -m overwatch overwatch.yaml
```

Try the included demo:

```bash
python -m overwatch "python demo_app.py"
```

## Hotkeys

| Key | Action |
|-----|--------|
| `r` | Kill and restart the process |
| `k` | Kill the process |
| `c` | Clear the log panel |
| `s` | Toggle auto-scroll |
| `b` | Toggle monitor sidebar |
| `q` | Quit (kills process and exits) |

All hotkeys are remappable via config.

## Configuration

Create an `overwatch.yaml`:

```yaml
command: "python my_app.py --verbose"

env:
  PYTHONUNBUFFERED: "1"
  MY_VAR: "value"

log:
  max_lines: 10000
  wrap: true
  timestamp: false

hotkeys:
  kill: "k"
  reload: "r"
  clear: "c"
  quit: "q"
  toggle_scroll: "s"
  toggle_sidebar: "b"

monitors:
  - type: process_stats
    refresh: 2

  - type: custom_metrics

  - type: file_watcher
    paths: ["./output/*.png", "./logs/*.log"]
    refresh: 5

  - type: http_health
    endpoints:
      - url: "http://localhost:8080/health"
        label: "API"
        timeout: 3
    refresh: 10
```

When running without a config file, Overwatch uses sensible defaults: `process_stats` monitor enabled, `PYTHONUNBUFFERED=1`, standard hotkey bindings.

## Monitors

Four built-in monitor types display in the sidebar:

| Monitor | What it shows | Config |
|---------|--------------|--------|
| `process_stats` | PID, CPU %, memory (MB), thread count, open FDs | `refresh` |
| `custom_metrics` | Gauges, counters, timings pushed via SDK | `refresh` |
| `file_watcher` | File count, changes, and new files matching glob patterns | `paths`, `refresh` |
| `http_health` | Endpoint status with response codes or DOWN/TIMEOUT | `endpoints`, `refresh` |

Monitors are pluggable. Add your own by subclassing `BaseMonitor` and registering with `@register_monitor("my_type")`.

## SDK

Instrument your Python app to push live metrics into the Overwatch sidebar. The SDK has **zero dependencies** (stdlib only) and all calls are **silent no-ops** when not running under Overwatch.

### Setup

```python
import sys
sys.path.insert(0, "/path/to/overwatch")
from sdk import metrics
```

### API

```python
# Gauges - current values that go up and down
metrics.gauge("queue_depth", 42)
metrics.gauge("gpu_util", 85.2, {"device": "cuda:0"})

# Counters - cumulative totals
metrics.counter("requests_total")       # +1
metrics.counter("bytes_sent", 4096)     # +4096

# Timings - durations in milliseconds
metrics.timing("request_ms", 123.4)

# Heartbeat - prove the process is alive
metrics.heartbeat()
```

### Example

```python
import sys, time
sys.path.insert(0, "/path/to/overwatch")
from sdk import metrics

items = load_items()
metrics.gauge("total_items", len(items))

for i, item in enumerate(items):
    start = time.perf_counter()
    process(item)
    elapsed_ms = (time.perf_counter() - start) * 1000

    metrics.timing("process_ms", elapsed_ms)
    metrics.counter("processed")
    metrics.gauge("progress_pct", round((i + 1) / len(items) * 100, 1))

    if i % 10 == 0:
        metrics.heartbeat()
```

This script works identically standalone or under Overwatch. No conditional imports, no try/except, no config flags.

### How it works

Overwatch creates a Unix domain socket at `/tmp/overwatch-{pid}.sock` and passes the path to the child process via the `OVERWATCH_IPC` environment variable. The SDK connects lazily on first metric call and sends newline-delimited JSON. If the socket isn't available, a null transport silently drops all messages.

## Architecture

```
overwatch/
├── cli.py                   # Argparse + config loading + app launch
├── config.py                # YAML → dataclasses
├── app.py                   # Textual App (compose, hotkeys, wiring)
├── app.tcss                 # Layout CSS
├── process.py               # Async subprocess lifecycle
├── ipc.py                   # Unix socket server + MetricsStore
├── monitors/
│   ├── __init__.py          # BaseMonitor ABC + @register_monitor
│   ├── process_stats.py     # psutil: CPU/mem/threads
│   ├── custom_metrics.py    # Reads MetricsStore snapshots
│   ├── file_watcher.py      # Glob + os.stat polling
│   └── http_health.py       # httpx async polling
└── widgets/
    ├── log_panel.py         # RichLog + Text.from_ansi()
    ├── monitor_card.py      # Polled monitor display card
    ├── monitor_sidebar.py   # Vertical card container
    └── status_bar.py        # Hotkey hints + state indicator

sdk/
├── __init__.py              # Public API re-exports
├── metrics.py               # gauge(), counter(), timing(), heartbeat()
└── _transport.py            # Null/Socket transport with lazy connect
```

### Key design decisions

- **Single event loop**: Subprocess I/O, IPC server, and monitor polling all run in Textual's async event loop. No threads on the TUI side.
- **Process group kill**: Child processes start with `start_new_session=True`. Kill sends `SIGTERM` to the process group via `os.killpg`, with `SIGKILL` fallback after 5 seconds.
- **ANSI passthrough**: Rich's `Text.from_ansi()` parses subprocess color codes. Carriage returns are handled for progress bar compatibility.
- **SDK singleton**: Transport is initialized once on first call. `_NullTransport` when `OVERWATCH_IPC` is unset, `_SocketTransport` with `threading.Lock` otherwise.

## Dependencies

| Package | Purpose |
|---------|---------|
| [textual](https://github.com/Textualize/textual) | TUI framework |
| [pyyaml](https://pyyaml.org/) | Config file loading |
| [psutil](https://github.com/giampaolo/psutil) | Process stats monitor |
| [httpx](https://www.python-httpx.org/) | HTTP health check monitor |

The SDK (`sdk/`) uses only the Python standard library.

## License

MIT
