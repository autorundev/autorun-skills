---
name: architecture-review
description: "Universal architecture review skill. Audits system design for complexity, coupling, scalability, maintainability, and security posture. Works on any codebase: backend services, bots, APIs, infrastructure. Triggers on: architecture review, design review, structural review, tech debt audit, coupling analysis, what is wrong with the architecture, how well is this designed, review the system design."
---

# Architecture Review

Universal system design audit. Adapt depth to project size: for a microservice — 20 min, for a full stack — several hours.

---

## Two Modes

**Single-pass (default):** orchestrator walks through all 7 steps below in one context. Best for small/medium projects (<50 files), or when you want a single coherent narrative.

**Parallel multi-agent (for large projects or deep audits):** dispatch 3 sub-agents with different focuses, then consolidate. Use when codebase is too large for one context or when you want independent perspectives that can disagree.

```
Agent A — boundaries & coupling      (Steps 1, 3)
Agent B — data flow & scalability    (Steps 2, 4)
Agent C — operations & security      (Steps 5, 7)
Orchestrator — Step 6 (complexity), consolidates findings, drafts the report
```

Each sub-agent gets: project root, relevant CLAUDE.md, list of entry points, and the steps they own from this skill. They return a markdown section ready for the final report. The orchestrator dedupes overlapping findings and resolves conflicts (e.g. one agent flags X as critical, another as nitpick — orchestrator decides).

**When to pick parallel mode:**
- Codebase >50 files or >10k LoC
- User asks for "deep audit" / "thorough review"
- Multiple subsystems with different concerns (e.g. backend + mini-app + infra)

**When NOT to pick parallel mode:**
- Single-file or small-component review
- Quick sanity check ("does this design look right?")
- User wants a fast verdict, not a comprehensive report

---

## Before You Start

Read before launching:
- Project's main CLAUDE.md (structure, conventions)
- README / docs/INFRA.md / docs/SERVICES.md if they exist
- Main entry points (main, router, bot handler)
- `git log --oneline -20` — understand the development direction
- Check for existing tests and CI configuration

Ask yourself three questions:
1. What does the system do (one sentence)?
2. What is the main invariant (what must never break)?
3. Where is the scariest part (the place you are most afraid to touch)?

---

## Review Protocol

### Step 1: Boundary Analysis

**What to check:** clarity of boundaries between components.

```
[ ] Each module has a single responsibility?
[ ] Dependencies flow one way (no cycles)?
[ ] Public interface is minimal (no unnecessary exports)?
[ ] Data does not leak across boundaries (no shared mutable state)?
[ ] Module boundaries align with domain boundaries?
```

**Analysis commands:**
```bash
# Python: find circular imports
grep -r "^from\|^import" src/ | sort | uniq -c | sort -rn | head -30

# Find God Objects (files > 300 lines)
find . -name "*.py" -exec wc -l {} + | sort -rn | head -20

# Count imports per file (high count = high coupling)
for f in $(find . -name "*.py" -path "*/src/*"); do
  echo "$(grep -c "^from\|^import" "$f") $f"
done | sort -rn | head -20
```

**Red flags:**
- Module imports > 10 other modules from the same project
- Single file > 500 lines
- Class does I/O, business logic, AND storage
- `utils.py` over 200 lines (junk drawer)
- Circular imports between packages

---

### Step 2: Data Flow Review

**What to check:** how data moves through the system.

```
[ ] Entry point (user input / webhook / API) is clearly marked?
[ ] Data is validated at the entry point, not mid-pipeline?
[ ] Data mutation happens in one place (single source of truth)?
[ ] No hidden side effects in read-only operations?
[ ] Errors propagate up to the caller, not swallowed silently?
[ ] Serialization/deserialization happens at boundaries only?
```

**Draw a diagram (even ASCII):**
```
User -> [Triage] -> [Router] -> [Module A] -> [DB] -> [Response]
                             \-> [Module B] -> [External API]
```

**Red flags:**
- No single point of input validation
- `try: ... except: pass` without logging
- Functions with `**kwargs` without documentation
- Global variables for state
- Data transformation scattered across multiple layers

---

### Step 3: Coupling & Cohesion

**What to check:** how independent the components are.

```
[ ] Can component A be replaced without touching B?
[ ] Tests for A do not require spinning up the entire system?
[ ] Configuration is injected, not hardcoded inside modules?
[ ] External dependencies (DB, API) are isolated behind an interface?
[ ] Shared data structures are immutable or explicitly owned?
```

**Coupling metric (manual):**
```bash
# How many files must change when renaming a key entity?
grep -r "YourEntity\|YourClass" src/ --include="*.py" -l | wc -l
# > 20 files = tight coupling

# Find which modules depend on a specific module
grep -r "from src.module_name\|import module_name" src/ --include="*.py" -l
```

**Red flags:**
- Changing storage format requires edits in 5+ files
- No abstraction over external API (raw `requests.get` everywhere)
- Test creates real files/connections without mock capability
- Configuration read from `os.environ` in the middle of business logic
- Shotgun surgery: one logical change requires touching many files

---

### Step 4: Scalability Posture

**What to check:** how the system will behave under load or growth.

```
[ ] No N+1 queries in loops?
[ ] Caching exists where needed?
[ ] Blocking I/O is not in the hot path?
[ ] Context/memory size is bounded (no unbounded growth)?
[ ] Timeouts set on all external calls?
[ ] Pagination/streaming for large data sets?
```

**Commands:**
```bash
# Find potential N+1 (queries inside loops)
grep -rn "for.*in" src/ --include="*.py" | head -20
# Check each loop for db/api calls inside

# Find missing timeouts
grep -r "requests\.\(get\|post\|put\|delete\)\|httpx\.\|aiohttp" src/ --include="*.py" | grep -v "timeout"

# Find unbounded collections
grep -rn "\.append\|\.extend\|\.add" src/ --include="*.py" | head -20
```

**Red flags:**
- `for item in all_items: db.query(item.id)` — N+1
- `context = load_entire_db()` without pagination
- `requests.get(url)` without timeout
- Accumulating logs/history without rotation or eviction
- In-memory caches without size limits or TTL

---

### Step 5: Operational Readiness

**What to check:** how ready the system is for production operation.

```
[ ] Logs contain enough for diagnostics (but no secrets)?
[ ] Errors are not lost (not swallowed in bare except)?
[ ] Health check / smoke test exists?
[ ] Graceful shutdown is implemented?
[ ] Secrets in env vars, not in code?
[ ] Backup / recovery is documented?
[ ] Deployment is repeatable (not manual steps)?
[ ] Monitoring / alerting covers critical paths?
```

**Commands:**
```bash
# Find logged secrets
grep -r "password\|token\|secret\|api_key" src/ --include="*.py" | grep -v "env\|config\|test" | grep "log\|print"

# Find bare except without logging
grep -rn "except:" src/ --include="*.py"

# Check for health check endpoints
grep -r "health\|ping\|status" src/ --include="*.py" -l

# Check Docker restart policy
grep -r "restart:" docker-compose*.yml 2>/dev/null
```

**Red flags:**
- `except Exception: pass` — error disappears silently
- Tokens/keys in source code
- No documentation for "what to do if it crashes"
- Docker without restart policy or healthcheck
- No structured logging (just `print()`)

---

### Step 6: Complexity Budget

**What to check:** whether the system is over-engineered for its task.

```
[ ] Every abstraction is justified (has 2+ usages or covers a known-future need)?
[ ] No architecture "for the future" without current necessity or vision doc reference?
[ ] A new developer can understand the system in a day?
[ ] Number of layers matches task complexity?
[ ] No premature optimization without profiling data?
```

**Key question:** if you were building this system from scratch today, which decisions would you NOT repeat?

**Red flags:**
- Microservices for a one-person project
- Event-driven architecture with a single consumer
- 4+ abstraction layers for CRUD
- "It is complicated, only I understand how it works"
- Framework/library choices that don't match the team size

---

### Step 7: Security Posture (High-Level)

**What to check:** basic security (deep audit is a separate dedicated skill).

```
[ ] User input is validated and sanitized?
[ ] Permissions are minimal (principle of least privilege)?
[ ] Dependencies are not critically outdated?
[ ] No authorization bypass paths?
[ ] Sensitive data encrypted at rest and in transit?
[ ] Rate limiting on public endpoints?
```

**Commands:**
```bash
# Python: check outdated dependencies with CVEs
pip-audit 2>/dev/null || (pip install pip-audit -q && pip-audit)

# Find potential injection points
grep -rn "eval\|exec\|os\.system\|subprocess.*shell=True\|__import__" src/ --include="*.py"

# Find SQL injection risks
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|\.format.*SELECT" src/ --include="*.py"
```

---

## Review Report Format

```markdown
# Architecture Review — {Project} — {DATE}

## TL;DR
{2-3 sentences: what is good, what is bad, main risk}

## Strengths
- ...

## Critical Issues (fix before next release)
| # | Issue | File/Component | Recommendation |
|---|-------|----------------|----------------|
| 1 | ...   | ...            | ...            |

## Debt Items (fix in next sprint)
- ...

## Design Questions (discuss with team)
- ...

## Verdict
**Complexity**: Low / Medium / High (relative to task)
**Maintainability**: 1-5
**Scalability**: 1-5
**Production readiness**: 1-5

## Next Steps
1. ...
2. ...
```

---

## Quick Heuristics

| Symptom | Diagnosis | Treatment |
|---------|-----------|-----------|
| "Don't touch that file, it's magic" | High coupling / No tests | Isolate behind an interface, cover with tests |
| Function > 100 lines | Missing decomposition | Split by Single Responsibility |
| `utils.py` > 200 lines | Missing domain model | Group by domain |
| Test spins up the whole system | Missing seams | Introduce dependency injection |
| "I'll add this for the future" | YAGNI violation | Remove it, add when actually needed |
| Change in one place breaks another | Hidden coupling | Explicit interfaces + tests |
| Same logic in 3+ places | DRY violation | Extract shared function or module |
| Config scattered across files | No single source of config | Centralize configuration |
