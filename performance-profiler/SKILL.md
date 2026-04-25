---
name: performance-profiler
description: "Python/Docker performance profiling skill. Use when diagnosing slow code, high memory usage, CPU spikes, slow API responses, or bot latency issues. Covers cProfile, memory_profiler, py-spy, async profiling, Docker container metrics, and actionable optimization recommendations. Triggers on: performance profiling, slow response, high memory usage, memory leak, CPU spike, bot latency, optimize performance, why is it slow, profile this, find bottleneck."
---

# Performance Profiler

Diagnostics and optimization for Python services and Docker containers.

---

## Before You Start

Read before launching:
- Symptoms: what exactly is slow? (specific handler, startup, memory growth over time)
- Baseline metrics: `docker stats`, `htop`, bot response time
- Recent changes: `git log --oneline -10`

**Do not optimize blindly.** Measure first, then fix.

---

## Step 1: Quick System Check

```bash
# Containers — CPU/Memory right now
docker stats --no-stream

# Processes inside a container
docker exec <container> top -bn1 | head -20

# Memory consumption of the Python process
docker exec <container> ps aux --sort=-%mem | head -10

# Open file descriptors (sign of a leak)
docker exec <container> ls /proc/1/fd | wc -l

# Swap usage (if swap is active — already a problem)
free -h && swapon --show

# Disk I/O — check if the disk is a bottleneck
iostat -x 1 3 2>/dev/null || (apt-get install -y sysstat -q && iostat -x 1 3)
```

**Red flags:**
- Container > 80% of Memory limit -> risk of OOM kill
- fd count grows over time -> descriptor leak
- CPU constantly > 70% when idle -> something spinning in the background
- High iowait% -> disk is the bottleneck, not CPU

---

## Step 2: Python CPU Profiling

### Option A — cProfile (built-in, no code changes)

```bash
# Run script with profiling
python3 -m cProfile -o profile.out src/main.py

# Analyze results
python3 -c "
import pstats
s = pstats.Stats('profile.out')
s.sort_stats('cumulative')
s.print_stats(20)
"
```

### Option B — py-spy (production-safe, no process restart)

**Important:** When profiling inside Docker, the container needs `SYS_PTRACE` capability:
```yaml
# docker-compose.yml
services:
  myservice:
    cap_add:
      - SYS_PTRACE
```

```bash
pip install py-spy -q

# Find the PID of the Python process
docker exec <container> ps aux | grep python

# Flame graph (open in browser)
# Run from HOST if container has SYS_PTRACE, or from inside the container
py-spy record -o flamegraph.svg --pid <PID> --duration 30

# Top functions in real time
py-spy top --pid <PID>
```

**Reading a flame graph:**
- Width = time spent (wider = slower)
- Height = call stack depth
- Look for wide bars near the top — those are the actual slow functions
- Narrow-but-tall towers = deep call stacks (possible over-abstraction)

### Option C — line_profiler (line-by-line profiling)

```python
# Add decorator to the suspect function
from line_profiler import LineProfiler

profiler = LineProfiler()
profiler.add_function(your_slow_function)
profiler.enable_by_count()

# After running:
profiler.print_stats()
```

```bash
pip install line_profiler -q
kernprof -l -v script.py
```

---

## Step 3: Memory Profiling

### Baseline — tracemalloc (built-in)

```python
import tracemalloc

tracemalloc.start()

# ... your code ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)

# Compare two snapshots to find growth
snapshot1 = tracemalloc.take_snapshot()
# ... more code ...
snapshot2 = tracemalloc.take_snapshot()
top_stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in top_stats[:10]:
    print(stat)
```

### Memory over time — memory_profiler

```bash
pip install memory_profiler -q

# Add @profile decorator to the function, then:
python3 -m memory_profiler script.py

# mprof — memory consumption graph over time
mprof run python3 script.py
mprof plot  # requires matplotlib
```

### Leaks — objgraph

```bash
pip install objgraph -q
```

```python
import objgraph

# Top objects in memory
objgraph.show_most_common_types(limit=10)

# What is growing between two snapshots
objgraph.show_growth()

# Reference graph for a suspicious object
objgraph.show_backrefs(obj, max_depth=3)
```

### Common memory leak patterns in Python
- **Unclosed connections/files**: use `with` statements or explicit `.close()`
- **Growing caches without eviction**: use `functools.lru_cache(maxsize=N)` with a bound
- **Circular references with `__del__`**: prevent garbage collection
- **Global lists/dicts that accumulate**: add TTL or max-size pruning
- **Event handler accumulation**: unsubscribe when done

---

## Step 4: Async Profiling (asyncio / aiogram)

```python
import asyncio
import cProfile

# Profiling an async function
async def main():
    # your code
    pass

profiler = cProfile.Profile()
profiler.enable()
asyncio.run(main())
profiler.disable()
profiler.print_stats(sort='cumulative')
```

### Slow async tasks — asyncio debug mode

```python
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
asyncio.get_event_loop().set_debug(True)
# Logs coroutines that execute for > 100ms (blocking the event loop)
```

### aiogram-specific — timing middleware

```python
from aiogram import BaseMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class TimingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        start = time.perf_counter()
        result = await handler(event, data)
        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > 500:  # > 500ms — log it
            logger.warning(
                "SLOW handler: %.0fms | %s",
                elapsed, type(event).__name__
            )
        return result
```

### Finding event loop blockers

```python
# Add to startup to detect blocking calls in async code
import asyncio

loop = asyncio.get_event_loop()
loop.slow_callback_duration = 0.1  # 100ms threshold

# Any callback taking longer than this will be logged as WARNING
```

---

## Step 5: I/O and Database Bottlenecks

```bash
# strace — which syscalls are hanging (run inside container)
# Requires SYS_PTRACE capability
apt-get install -y strace -q
strace -p <PID> -e trace=network,file -c  # summary over 10 seconds, Ctrl+C to stop

# lsof — open connections
docker exec <container> lsof -i 2>/dev/null | grep ESTABLISHED | wc -l

# Network latency to external services
docker exec <container> timeout 5 bash -c 'echo | nc -w3 api.example.com 443 && echo "OK" || echo "TIMEOUT"'
```

### SQLite slow queries

```python
import sqlite3
import time
import logging

logger = logging.getLogger(__name__)

# Log all queries with timing
class TimedConnection:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    def execute(self, sql, params=()):
        start = time.perf_counter()
        result = self.conn.execute(sql, params)
        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > 50:  # > 50ms
            logger.warning("SLOW query (%.0fms): %s", elapsed, sql[:200])
        return result
```

```bash
# Check query plans
sqlite3 database.db "EXPLAIN QUERY PLAN SELECT ...;"
# "SCAN TABLE" = full table scan = needs an index
# "SEARCH ... USING INDEX" = good
```

### Finding N+1 queries in code

```bash
# Find loops that might contain DB/API calls
grep -rn "for.*in" src/ --include="*.py" | head -20
# Check each loop — are there db/file/network operations inside?

# Find repeated DB connections (should use connection pooling)
grep -rn "connect\|Connection" src/ --include="*.py" | grep -v "test\|#"
```

---

## Step 6: Docker Resource Limits

```bash
# Current container limits
docker inspect <container> | python3 -c "
import json, sys
data = json.load(sys.stdin)[0]
hc = data['HostConfig']
mem = hc.get('Memory', 0)
print('Memory limit:', f'{mem // 1024 // 1024} MB' if mem else 'unlimited')
print('CPU quota:', hc.get('CpuQuota', 0) or 'unlimited')
print('CPU period:', hc.get('CpuPeriod', 0) or 'default')
print('PID limit:', hc.get('PidsLimit', 0) or 'unlimited')
"

# Live metrics stream (Ctrl+C to stop)
docker stats <container> --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
```

### Add limits in docker-compose.yml

```yaml
services:
  myservice:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 128M
    # Also set Python-level memory controls
    environment:
      - PYTHONMALLOC=malloc  # better memory tracking with tracemalloc
```

---

## Step 7: Optimization Checklist

After profiling — apply fixes in order of ROI (highest impact, lowest effort first):

```
[ ] Cache results of expensive calls (functools.lru_cache, Redis, dict cache with TTL)
[ ] Batch DB queries (eliminate N+1)
[ ] Lazy loading — do not load entire dataset on every request
[ ] Async I/O — replace blocking calls with async (aiofiles, aiosqlite, aiohttp)
[ ] Connection pooling — do not create a new connection per request
[ ] Indexes in SQLite/PostgreSQL — EXPLAIN QUERY PLAN reveals full scans
[ ] Reduce context/payload size — do not send everything every time
[ ] Pre-compute / materialize — cache derived data instead of recalculating
[ ] Compress large payloads (gzip for HTTP, compact formats for storage)
[ ] Set memory limits on caches and collections (maxsize, TTL)
```

---

## Profiling Report Format

```markdown
# Performance Report — {service} — {DATE}

## Symptoms
{what was observed, when it started}

## Measurements (before)
- Response time: Xms (p50), Xms (p95)
- Memory: X MB RSS
- CPU: X% avg

## Bottlenecks Found
| # | Function/Component | Time/Memory | Root Cause |
|---|-------------------|-------------|------------|
| 1 | ...               | ...         | ...        |

## Changes Made
- ...

## Measurements (after)
- Response time: Xms (p50), Xms (p95)
- Memory: X MB RSS
- Improvement: X%

## Remaining Issues
- ... (if any, with estimated effort to fix)
```
