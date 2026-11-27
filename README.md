# cmdn — Process Resource Monitor & Comparison Tool

**Version 3.0** — Monitor, compare, and analyze process resource usage on Windows and Linux.

## Overview

`cmdn` (pronounced "command") is a cross-platform tool for measuring CPU, memory, disk I/O, and network usage of processes. It supports three modes:

| Mode | Purpose |
|------|---------|
| `run` | Launch a program and sample until it exits |
| `compare` | Monitor two existing process groups simultaneously with live dashboard |
| `stats` | Statistical comparison of multiple run summaries |

Output: CSV time-series + JSON run summary + optional live web dashboard (Chart.js).

---

## Installation

```bash
python3 -m pip install psutil
# cmdn.py is a single-file script — no installation needed
```

---

## Quick Start

### Mode 1: Run a command and capture its resource usage
```bash
python3 cmdn.py run --out ./my_run -- python3 -c "sum(range(10_000_000))"
# Output: my_run.csv, my_run.summary.json, my_run.run.json
```

### Mode 2: Compare two running processes (live dashboard)
```bash
# By PID (most accurate CPU%)
python3 cmdn.py compare -p1 1234 -p2 5678 --out ./compare_out

# By name substring (matches all processes containing the term)
python3 cmdn.py compare -p1 python -p2 node --out ./compare_out

# Open dashboard automatically at http://127.0.0.1:50080
python3 cmdn.py compare -p1 python -p2 node --out ./compare_out --no-open=false
```

### Mode 3: Statistical comparison across runs
```bash
python3 cmdn.py stats --out ./comparison.csv run1.summary.json run2.summary.json run3.summary.json
```

---

## Understanding CPU Percentage: Why You See > 100%

### The Core Concept

**`cpu_pct_one_core` = percentage of ONE logical CPU core used by the process(es).**

| Value | Meaning |
|-------|---------|
| 0% | Process is idle |
| 100% | One logical core fully busy |
| 200% | Two logical cores fully busy |
| 600% | Six logical cores fully busy |

### Why > 100% Is Normal

Modern CPUs have multiple **logical cores** (threads). A multi-threaded process can use more than one core simultaneously.

```
Example: 6-core CPU (12 logical with hyperthreading)
├── Process A: 4 threads → max 400% (or 600% if using all 6 physical cores)
├── Process B: 2 threads → max 200%
└── System total: 1200% (all 12 logical cores at 100%)
```

### cmdn Reports Two CPU Metrics

| Field | Formula | Range | Use Case |
|-------|---------|-------|----------|
| `cpu_pct_one_core` | Sum of each thread's CPU% | 0% to N×100% | **Primary metric** — shows actual compute pressure |
| `cpu_pct_host` | `cpu_pct_one_core / logical_cpu_count` | 0% to 100% | Share of total machine capacity |

### Example: Interpreting 600% on a 6-Core Machine

```csv
# cmdn output
cpu_pct_one_core,cpu_pct_host,logical_cpu_count
600.0,50.0,12
```

**Interpretation:**
- Process(es) using 600% of one core = 6 logical cores at 100%
- Host has 12 logical cores → process uses 50% of total machine capacity
- If this is a single 6-thread process: **fully utilizing 6 cores** ✓
- If this is many small processes: **combined they saturate 6 cores**

### How cmdn Calculates CPU%

1. **Baseline priming** — First call to `psutil.Process.cpu_percent(interval=None)` establishes t=0
2. **Delta measurement** — Each sample interval: `(user_time + system_time) / interval × 100`
3. **Aggregation** — Sum across all matching processes (including children if `--include-children`)
4. **Per-core normalization** — Result is "one-core equivalents"

```python
# Simplified from cmdn.py
cpu_pct = proc.cpu_percent(interval=None)  # Returns % of ONE core
totals["cpu_pct"] += cpu_pct  # Sum across all matching processes
cpu_pct_one_core = totals["cpu_pct"]  # Can exceed 100%
cpu_pct_host = cpu_pct_one_core / logical_cpu_count  # 0-100%
```

### Common Scenarios

| Scenario | cpu_pct_one_core | cpu_pct_host (12-core) | Interpretation |
|----------|------------------|------------------------|----------------|
| Single-threaded busy loop | ~100% | ~8.3% | One core maxed |
| 4-thread parallel workload | ~400% | ~33% | 4 cores maxed |
| 12-thread workload | ~1200% | 100% | Machine saturated |
| Many small processes | 600% | 50% | Combined = 6 cores |

---

## Units Reference

| Field | Unit | Description |
|-------|------|-------------|
| `elapsed_s` | seconds | Time since monitoring started |
| `sample_interval_actual_s` | seconds | Actual time between samples (≈ configured interval) |
| `cpu_pct_one_core` | % | CPU usage relative to **one logical core** |
| `cpu_pct_host` | % | CPU usage relative to **all logical cores** |
| `cpu_user_s`, `cpu_system_s` | seconds | Cumulative user/kernel CPU time |
| `rss_bytes` | bytes | Resident Set Size — physical RAM used |
| `rss_pct_ram` | % | RSS as % of total system RAM |
| `vms_bytes` | bytes | Virtual Memory Size — address space reserved |
| `uss_bytes` | bytes | **Linux only** — Unique Set Size (private RAM) |
| `pss_bytes` | bytes | **Linux only** — Proportional Set Size (shared RAM divided) |
| `process_io_read_bytes_per_s` | bytes/s | Process-attributed disk read rate |
| `process_io_write_bytes_per_s` | bytes/s | Process-attributed disk write rate |
| `system_disk_read_bytes_per_s` | bytes/s | **Whole-system** disk read rate |
| `system_disk_write_bytes_per_s` | bytes/s | **Whole-system** disk write rate |
| `system_net_sent_bytes_per_s` | bytes/s | **Whole-system** network send rate |
| `system_net_recv_bytes_per_s` | bytes/s | **Whole-system** network receive rate |
| `probe_latency_ms` | milliseconds | HTTP response time (if `--probe-url` configured) |

---

## Memory Metrics Explained

### RSS (Resident Set Size)
- **What:** Physical RAM pages currently mapped to the process
- **Includes:** Code, heap, stacks, shared libraries (counted per-process)
- **Caveat:** Shared memory counted multiple times across processes

### USS (Unique Set Size) — Linux only
- **What:** RAM pages **only** used by this process
- **Best for:** True memory footprint of a single process

### PSS (Proportional Set Size) — Linux only
- **What:** Shared pages divided by number of processes sharing them
- **Best for:** System-wide memory accounting

### When to Use Which
| Goal | Metric |
|------|--------|
| "How much RAM does this process appear to use?" | RSS |
| "How much RAM would be freed if I kill this process?" | USS |
| "Fair share of shared memory across processes" | PSS |

---

## Sampling Model (Important)

> **cmdn uses periodic polling, not continuous tracing.**

| Aspect | Behavior |
|--------|----------|
| CPU % | Covers activity **since previous sample** |
| Disk/Net rates | Bytes transferred **since previous sample** / elapsed time |
| Memory (RSS/VMS) | **Snapshot** at sample instant |
| Process list | Refreshed **each sample** (catches new children) |
| Target processes | **Never paused** — they run at full speed |

### Implications
- **Short spikes between samples are missed** — use shorter `--sample-interval` (default 0.25s) to catch more
- **CPU% is an average over the interval** — a 10ms burst in 250ms interval = ~4% not 100%
- **Memory is point-in-time** — RSS may differ from average over interval
- **Not a profiler** — use `perf`, `py-spy`, `vtune` for instruction-level analysis

---

## Command Reference

### `run` — Launch and Monitor
```bash
python3 cmdn.py run --out PATH [OPTIONS] -- COMMAND [ARGS...]

Options:
  --sample-interval FLOAT       Seconds between samples (default: 0.25)
  --memory-detail-interval FLOAT  USS/PSS sampling interval (default: 5.0)
  --max-duration FLOAT          Stop after N seconds (does not kill process)
  --start-at ISO_TIMESTAMP      Delayed synchronized start (e.g. 2030-01-01T12:00:00Z)
  --pair-id STRING              Trial identifier for cross-OS comparison
  --include-children / --no-include-children  Include child processes (default: yes)
  --probe-url URL               HTTP endpoint to probe for latency
  --probe-interval FLOAT        Seconds between probes (default: 1.0)
  --probe-timeout FLOAT         Probe timeout seconds (default: 3.0)
  --lag-threshold-ms FLOAT      Flag probes above this (default: 1000)
```

### `compare` — Live Dual-Process Dashboard
```bash
python3 cmdn.py compare -p1 TERM -p2 TERM --out DIR [OPTIONS]

Options:
  -p1, --p1 TERM       First process: name substring OR exact PID
  -p2, --p2 TERM       Second process: name substring OR exact PID
  --sample-interval FLOAT       (default: 0.25)
  --memory-detail-interval FLOAT (default: 5.0)
  --max-duration FLOAT          Optional stop time
  --probe-url1 URL              Probe for process 1
  --probe-url2 URL              Probe for process 2
  --probe-interval FLOAT        (default: 1.0)
  --probe-timeout FLOAT         (default: 3.0)
  --lag-threshold-ms FLOAT      (default: 1000)
  --host IP          Dashboard bind (default: 127.0.0.1)
  --port INT         Dashboard port (default: 50080)
  --no-open          Don't auto-open browser
```

**PID vs Name Matching:**
- `-p1 1234` → exact PID (cached Process object, accurate CPU%)
- `-p1 python` → case-insensitive substring match on process name/exe basename

### `stats` — Cross-Run Statistics
```bash
python3 cmdn.py stats --out comparison.csv SUMMARY1.json SUMMARY2.json ...
```
- Computes mean, median, SD, 95% CI per metric per OS
- Paired t-test for runs with same `--pair-id` across Windows/Linux
- Output: CSV with `metric, os, n_runs, mean, median, sd, ci_low, ci_high, ...`

---

## Dashboard

The `compare` mode serves a live dashboard at `http://host:port/`:

- **Real-time charts:** CPU, RSS, I/O, disk, network, system, HTTP probe
- **KPIs:** Mean, p95, peak for each metric
- **Lag analysis:** Flags HTTP responses above threshold
- **Statistics table:** Mean/p95/peak with P1−P2 difference
- **Time-range selector:** Last 1m/5m/15m/all
- **Pause/resume:** Toggle live updates

> Dashboard loads last 20,000 rows by default. Full history in CSV.

---

## Output Files

| File | Format | Description |
|------|--------|-------------|
| `*.csv` | CSV | Time-series samples (one row per interval) |
| `*.summary.json` | JSON | Run metadata + aggregate metrics |
| `*.run.json` | JSON | Raw run configuration (for `stats` mode) |

### CSV Columns (key fields)
```
timestamp_utc, elapsed_s, sample_interval_actual_s,
p1_cpu_pct_one_core, p1_cpu_pct_host, p1_rss_bytes, p1_rss_pct_ram,
p1_uss_bytes, p1_pss_bytes, p1_io_read_bytes_per_s, p1_io_write_bytes_per_s,
p2_cpu_pct_one_core, p2_cpu_pct_host, p2_rss_bytes, p2_rss_pct_ram,
p2_uss_bytes, p2_pss_bytes, p2_io_read_bytes_per_s, p2_io_write_bytes_per_s,
system_cpu_pct, system_memory_used_pct,
system_disk_read_bytes_per_s, system_disk_write_bytes_per_s,
system_net_sent_bytes_per_s, system_net_recv_bytes_per_s,
p1_probe_latency_ms, p2_probe_latency_ms, probe_latency_difference_ms, lag_suspected
```

---

## Cross-Platform Notes

| Feature | Linux | Windows |
|---------|-------|---------|
| RSS | ✓ | ✓ |
| VMS | ✓ | ✓ |
| USS/PSS | ✓ (via `/proc`) | ✗ (N/A) |
| Process I/O counters | ✓ | ✓ |
| Disk latency (read_time/write_time) | ✓ (if available) | ✓ (if available) |
| Thread count | ✓ | ✓ |
| Handle/FD count | ✓ (FDs) | ✓ (Handles) |
| Context switches | ✓ | ✓ |

---

## Accuracy & Limitations

### Verified Accurate
- **CPU%:** Matches `psutil.Process.cpu_percent()` baseline methodology
- **RSS:** Matches `/proc/<pid>/statm` (Linux) / `GetProcessMemoryInfo` (Windows)
- **Process I/O:** Tracks actual disk operations (not page cache)

### Known Limitations
| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Polling interval | Misses sub-interval spikes | Use `--sample-interval 0.05` |
| Page cache I/O | Process I/O shows 0 for cached writes | Use `system_disk_*` for total |
| USS/PSS Windows | Always `None` | Use RSS + PSS on Linux |
| Disk latency | Requires kernel support | May be `None` on some systems |
| Short-lived processes | May miss between samples | Use `run` mode for launched processes |

### Semaphore Warning
```
UserWarning: resource_tracker: There appear to be 5 leaked semaphore objects...
```
Cosmetic Python `multiprocessing` cleanup issue on shutdown. Does not affect data.

---

## Examples

### Basic CPU/Memory Profiling
```bash
# Profile a Python script (run mode)
python3 cmdn.py run --out ./profile -- python3 my_script.py

# With faster sampling (0.1s) for short-lived workloads
python3 cmdn.py run --out ./profile --sample-interval 0.1 -- python3 quick_task.py

# Profile with HTTP latency probe
python3 cmdn.py run --out ./webapp --probe-url http://localhost:8080/health -- python3 app.py
```

### Live Comparison Dashboard
```bash
# Compare two processes by PID (most accurate CPU%)
python3 cmdn.py compare -p1 12345 -p2 67890 --out ./cmp

# Compare by name (matches all processes containing term)
python3 cmdn.py compare -p1 python -p2 node --out ./cmp

# Compare with HTTP probes for lag detection
python3 cmdn.py compare -p1 nginx -p2 apache \
  --probe-url1 http://localhost:8080/ \
  --probe-url2 http://localhost:8081/ \
  --out ./webcmp

# Run headless (no browser) on custom port
python3 cmdn.py compare -p1 python -p2 node --out ./cmp --port 8080 --no-open
```

### Cross-Platform Benchmarking (Linux vs Windows)
```bash
# Linux machine
python3 cmdn.py run --out ./bench_linux --pair-id trial01 -- make -j$(nproc)

# Windows machine (PowerShell)
python3 cmdn.py run --out ./bench_win --pair-id trial01 -- msbuild /m:%NUMBER_OF_PROCESSORS%

# Compare results (run on either machine)
python3 cmdn.py stats --out ./bench_compare.csv bench_linux.summary.json bench_win.summary.json
```

### Statistical Analysis Across Multiple Runs
```bash
# Run same workload 5 times
for i in {1..5}; do
  python3 cmdn.py run --out ./run_$i --pair-id trial01 -- python3 workload.py
done

# Compare all runs
python3 cmdn.py stats --out ./stats.csv run_1.summary.json run_2.summary.json run_3.summary.json run_4.summary.json run_5.summary.json
```

### High-Frequency I/O Monitoring
```bash
# Sample every 50ms for disk-intensive workloads
python3 cmdn.py run --out ./io_test --sample-interval 0.05 -- dd if=/dev/zero of=test.dat bs=1M count=1000 oflag=direct
```

### Container/Docker Monitoring
```bash
# Monitor process inside container from host (using PID)
docker run -d --name myapp myimage
PID=$(docker inspect --format '{{.State.Pid}}' myapp)
python3 cmdn.py compare -p1 $PID -p2 systemd --out ./container_cmp
```

### CI/CD Integration
```bash
# GitHub Actions example
- name: Benchmark
  run: |
    python3 cmdn.py run --out ${{ github.workspace }}/bench --pair-id ${{ github.run_id }} -- pytest bench/
    python3 cmdn.py stats --out ${{ github.workspace }}/bench_compare.csv previous.summary.json bench.summary.json
  env:
    PYTHONPATH: ${{ github.workspace }}
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Issues and PRs welcome. Key areas:
- Windows USS/PSS approximation
- eBPF-based continuous sampling (Linux)
- Additional export formats (Parquet, InfluxDB)
- Remote dashboard authentication