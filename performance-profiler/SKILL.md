---
name: performance-profiler
description: Python/Docker performance profiling skill. Use when diagnosing slow code, high memory usage, CPU spikes, slow API responses, or Telegram bot latency issues. Covers cProfile, memory_profiler, py-spy, async profiling, Docker container metrics, and actionable optimization recommendations. Triggers on: "профилирование", "performance profiling", "медленно работает", "тормозит", "высокое потребление памяти", "memory leak", "утечка памяти", "CPU spike", "латентность бота", "slow response", "оптимизация производительности".
---

# Performance Profiler

Диагностика и оптимизация производительности Python-сервисов и Docker-контейнеров.

---

## Before You Start

Прочитай перед запуском:
- Симптомы: что именно медленно? (конкретный handler, startup, memory over time)
- Метрики baseline: `docker stats`, `htop`, время ответа бота
- Последние изменения: `git log --oneline -10`

**Не оптимизируй вслепую.** Сначала измерь, потом фикси.

---

## Step 1: Quick System Check

```bash
# Контейнеры — CPU/Memory прямо сейчас
docker stats --no-stream

# Процессы внутри контейнера
docker exec <container> top -bn1 | head -20

# Сколько памяти жрёт Python процесс
docker exec <container> ps aux --sort=-%mem | head -10

# Открытые файловые дескрипторы (признак утечки)
docker exec <container> ls /proc/1/fd | wc -l

# Swap usage (если swap активен — уже плохо)
free -h && swapon --show
```

**Red flags:**
- Контейнер > 80% от Memory limit → риск OOM kill
- fd count растёт со временем → утечка дескрипторов
- CPU постоянно > 70% в idle → что-то крутится фоном

---

## Step 2: Python CPU Profiling

### Вариант A — cProfile (встроенный, без изменений кода)

```bash
# Запустить скрипт с профилированием
python3 -m cProfile -o profile.out src/main.py

# Анализ результатов
python3 -c "
import pstats, io
s = pstats.Stats('profile.out')
s.sort_stats('cumulative')
s.print_stats(20)
"
```

### Вариант B — py-spy (production-safe, без остановки процесса)

```bash
pip install py-spy -q

# Найти PID Python процесса
docker exec <container> ps aux | grep python

# Flame graph (открыть в браузере)
py-spy record -o flamegraph.svg --pid <PID> --duration 30

# Топ функций в реальном времени
py-spy top --pid <PID>
```

### Вариант C — line_profiler (построчное профилирование)

```python
# Добавить декоратор к подозрительной функции
from line_profiler import LineProfiler

profiler = LineProfiler()
profiler.add_function(your_slow_function)
profiler.enable_by_count()

# После запуска:
profiler.print_stats()
```

```bash
pip install line_profiler -q
kernprof -l -v script.py
```

---

## Step 3: Memory Profiling

### Baseline — tracemalloc (встроенный)

```python
import tracemalloc

tracemalloc.start()

# ... твой код ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

### Memory over time — memory_profiler

```bash
pip install memory_profiler -q

# Декоратор на функцию
# @profile  ← добавь в код
python3 -m memory_profiler script.py

# Mprof — график потребления памяти за время
mprof run python3 script.py
mprof plot  # требует matplotlib
```

### Утечки — objgraph

```bash
pip install objgraph -q
```

```python
import objgraph

# Топ объектов в памяти
objgraph.show_most_common_types(limit=10)

# Что растёт между двумя снимками
objgraph.show_growth()

# Граф ссылок на подозрительный объект
objgraph.show_backrefs(obj, max_depth=3)
```

---

## Step 4: Async Profiling (asyncio / aiogram)

```python
import asyncio
import cProfile

# Профилирование async функции
async def main():
    # твой код
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
# Логирует coroutines которые выполняются > 100ms
```

### aiogram-specific — middleware для измерения

```python
from aiogram import BaseMiddleware
import time

class TimingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        start = time.perf_counter()
        result = await handler(event, data)
        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > 500:  # > 500ms — логируем
            print(f"SLOW handler: {elapsed:.0f}ms | {type(event).__name__}")
        return result
```

---

## Step 5: I/O и Database Bottlenecks

```bash
# strace — какие syscalls висят (запускать внутри контейнера)
apt-get install -y strace -q
strace -p <PID> -e trace=network,file -c  # summary за 10 сек

# lsof — открытые соединения
docker exec <container> lsof -i | grep ESTABLISHED | wc -l
```

### SQLite slow queries

```python
import sqlite3
import time

conn = sqlite3.connect('vault.db')
conn.set_trace_callback(print)  # логировать все запросы

# Или через EXPLAIN QUERY PLAN
cursor = conn.execute("EXPLAIN QUERY PLAN SELECT ...")
print(cursor.fetchall())
```

### Найти N+1 запросы в коде

```bash
grep -n "for.*in" src/*.py | head -20
# Проверить каждый цикл — нет ли внутри db/file операций
```

---

## Step 6: Docker Resource Limits

```bash
# Текущие лимиты контейнера
docker inspect <container> | python3 -c "
import json, sys
data = json.load(sys.stdin)[0]
hc = data['HostConfig']
print('Memory limit:', hc.get('Memory', 0) // 1024 // 1024, 'MB')
print('CPU quota:', hc.get('CpuQuota', 0))
print('CPU period:', hc.get('CpuPeriod', 0))
"

# История метрик (если есть)
docker stats <container> --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

### Добавить лимиты в docker-compose.yml

```yaml
services:
  vectoros:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 128M
```

---

## Step 7: Optimization Checklist

После профилирования — применяй в порядке ROI:

```
□ Кэшировать результаты дорогих вызовов (lru_cache, Redis)
□ Батчить DB запросы (убрать N+1)
□ Lazy loading — не загружать vault целиком при каждом запросе
□ Async I/O — заменить blocking calls на async (aiofiles, aiosqlite)
□ Connection pooling — не создавать новое соединение на каждый запрос
□ Индексы в SQLite — EXPLAIN QUERY PLAN покажет full scan
□ Уменьшить размер context window — не грузить весь vault в каждый промпт
```

---

## Profiling Report Format

```markdown
# Performance Report — {service} — {DATE}

## Симптомы
{что наблюдалось}

## Измерения (до)
- Время ответа: Xms (p50), Xms (p95)
- Memory: X MB RSS
- CPU: X% avg

## Найденные узкие места
| # | Функция/Компонент | Время/Память | Причина |
|---|-------------------|--------------|---------|
| 1 | ...               | ...          | ...     |

## Изменения
- ...

## Измерения (после)
- Время ответа: Xms (p50), Xms (p95)
- Memory: X MB RSS
- Улучшение: X%
```
