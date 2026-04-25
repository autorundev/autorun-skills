---
name: system-integrity-audit
description: "Deep system integrity audit: builds a complete inventory of all definitions (functions, methods, classes, constants, DB tables, config keys, events), then verifies every item is wired, reachable, and not blocked. Finds dead code, broken wiring, unreachable components, orphaned registrations, unused DB tables, and phantom config. Enriches with git blame and docs to classify intent."
---

# System Integrity Audit

Deep system wiring audit. Finds components that are defined but never called, registered but blocked, or connected but unreachable. Unlike code review (code quality) or architecture review (design) — this audit checks **wiring**: are all wires connected and does current flow through them.

---

## When to Use

- After a major refactoring (renames, module moves, subsystem replacement)
- At the end of a development cycle — before release
- When asked if everything works, if there are orphaned components, or dead code
- Periodically (every 2-4 weeks) for codebase hygiene

## When NOT to Use

- For code quality assessment — use `code-reviewer`
- For architecture assessment — use `architecture-review`
- For finding logic bugs — that's manual debugging
- For security audit — use `security-audit`

---

## Audit Protocol

### Phase 1: Understand the System

1. Read project CLAUDE.md — structure, entry points, conventions
2. `git log --oneline -30` — recent changes, what was added/removed
3. Identify the project language and framework to set grep patterns for Phase 2

### Phase 2: Build Complete Inventory

**This is the critical step that prevents missed findings.** Build an exhaustive list of everything defined in the project BEFORE checking wiring.

#### 2a. Function/Method Inventory

```bash
# Python
Grep pattern="^(def |    def |        def )" type="py" path="src/" output_mode="content"
# Also check standalone scripts, CLI entry points, etc.

# TypeScript/JavaScript
Grep pattern="^(export )?(async )?(function |const \w+ = )" type="ts" path="src/" output_mode="content"
```

For EVERY function/method found, record: `file:line function_name`. This is the master list — nothing should be skipped.

#### 2b. Class Inventory

```bash
Grep pattern="^class " type="py" path="src/" output_mode="content"
```

For each class, list ALL its methods. A class may be imported and used, but specific methods on it may be dead.

#### 2c. Constants and Enums

```bash
# Top-level constants (UPPER_CASE)
Grep pattern="^[A-Z][A-Z_]+ = " type="py" path="src/" output_mode="content"

# Enum definitions
Grep pattern="class \w+\(.*Enum" type="py" path="src/" output_mode="content"
```

#### 2d. Database Tables

```bash
# Table definitions in code
Grep pattern="CREATE TABLE|\.create_table|class \w+.*Model|__tablename__" path="src/" output_mode="content"

# Migration files
Glob pattern="**/migrations/**/*.py"
Glob pattern="**/migrations/**/*.sql"
```

#### 2e. Config/Environment Keys

```bash
# Keys read from env/config
Grep pattern="os\.environ|os\.getenv|config\[|config\.get|\.env\." path="src/" output_mode="content"

# Keys defined in .env.example, config files
Grep pattern="^[A-Z]" path=".env.example" output_mode="content"
```

#### 2f. Events/Signals

```bash
# Events emitted
Grep pattern="\.emit\(|\.send\(|\.publish\(|\.dispatch\(|signal\." path="src/" output_mode="content"

# Events listened to
Grep pattern="\.on\(|\.subscribe\(|\.connect\(|@receiver|\.add_listener" path="src/" output_mode="content"
```

#### 2g. Registries and Dispatch Tables

- Handler registrations (dict of name -> function)
- Schema/tool definitions (list of schemas)
- Scheduled jobs (cron, intervals)
- Weight/config tables (what types are defined)
- Export lists (`__init__.py`, `__all__`)
- Route registrations (URL -> handler, callback -> function)

### Phase 3: Trace Every Wire (parallel agents)

Split by domain — one agent per domain. **Each agent receives the inventory subset for their domain** (from Phase 2).

**How to split domains (adapt to project):**
- Agent 1: Core business logic (models, services, domain functions)
- Agent 2: API/handlers layer (routes, dispatch, callbacks, schemas)
- Agent 3: Infrastructure (DB tables, migrations, config, scheduled jobs, init/exports)
- Agent 4: Cross-cutting (events, constants, enums, utilities)

Add more agents for larger codebases. Each agent checks:

#### For every DEFINED function/method (from inventory):
```
1. Grep for the function name across ALL source files (not just its own file)
2. Is it called in runtime code? (exclude test files from this check)
3. Is it called ONLY from tests? → flag as TEST-ONLY
4. Is it imported but never actually called? (imported for type hints, re-export, etc.)
5. Can the call path actually be reached? (no always-false guards)
6. If registered in a dispatch table — does the key match what callers send?
```

**Critical: grep for the exact name, not just the file.** A function `process_order` might be defined in `orders.py` which is imported everywhere, but `process_order` itself is never called.

#### For every CLASS METHOD:
```
1. Is the class instantiated somewhere?
2. Is THIS SPECIFIC METHOD called on any instance?
3. Is it only called via parent class / ABC requirement?
4. Could it be called dynamically (getattr, __getattr__, etc.)?
```

#### For every CONSTANT/ENUM value:
```
1. Is the constant referenced outside its definition file?
2. For enums: is every enum member used, or only some?
3. Is it shadowed by a local variable with the same name?
```

#### For every DB TABLE:
```
1. Is there code that INSERTs into this table?
2. Is there code that SELECTs from this table?
3. Is there a migration that creates it but the table is never used in app code?
4. Is there app code referencing a table that no migration creates?
```

#### For every CONFIG/ENV KEY:
```
1. Is every key in .env.example actually read by code?
2. Is every key read by code defined in .env.example or has a default?
3. Are there keys with defaults that are never overridden? (dead config)
```

#### For every EVENT:
```
1. Every emitted event has at least one listener
2. Every listener has at least one emitter
3. Event name strings match exactly (no typos)
```

#### For every REGISTRATION (handler, schema, weight, schedule):
```
1. Does the registered function exist?
2. Does the registration key match what the system looks up?
3. Are all required companion registrations present?
   (e.g., handler + weight + time_window + recency_config)
4. Is there a default/fallback that silently swallows missing entries?
```

#### For every CONDITION/GATE:
```
1. Can the condition ever be true? (check data sources)
2. Is there a bootstrap problem? (needs X to start, but X is only set after start)
3. Does a "completed" flag permanently block re-entry when it shouldn't?
4. Is there a dependency on data that's never written?
```

#### For every IMPORT chain:
```
1. Does the import target exist? (renamed/moved files)
2. Are specific names available? (removed from __init__.py, renamed variables)
3. Will it crash at import time or only when called?
```

### Phase 4: Classify Intent (critical step)

For each finding, **before marking it as dead code**, check:

1. **Git blame**: when was it added? Is there a commit message explaining intent?
   ```bash
   git log --oneline --follow -5 -- path/to/file.py
   git log --all --oneline --grep="function_name"
   ```

2. **Code comments**: is there a `# TODO`, `# PLANNED`, `# DEPRECATED`, `# v2` marker?

3. **Documentation**: is it mentioned in specs, tasks.md, VISION.md, or CLAUDE.md as planned/future work?

4. **Tests**: does it have tests? Tests without production callers may indicate:
   - Planned feature (tests written first, integration pending)
   - Removed feature (integration removed, tests left behind)
   - Library function (used by external consumers)

5. **Dynamic dispatch**: could it be called via `getattr()`, string lookup, plugin system, or reflection?

Classify each finding:

| Classification | Meaning | Action |
|---|---|---|
| **DEAD** | No intent to use, no docs, stale | Remove or flag for removal |
| **ORPHANED** | Was connected, connection broken by refactor | Reconnect or remove |
| **PLANNED** | Docs/comments indicate future use | Leave, note in report |
| **DEPRECATED** | Replaced but not cleaned up | Remove, update docs |
| **BLOCKED** | Condition prevents execution | Fix condition or remove |
| **FRAGILE** | Works but depends on implicit assumptions | Add explicit check or doc |
| **TEST-ONLY** | Called from tests but no production path | Verify if intentional (helper/fixture) or orphaned |
| **PHANTOM** | Referenced in config/schema but no code exists | Create or remove reference |

### Phase 5: Report

```markdown
## System Integrity Audit — [Project Name]
**Date:** YYYY-MM-DD | **Scope:** X files, Y functions, Z tables audited

### Stats
- Total definitions scanned: N
- Verified wired: N (N%)
- Findings: N critical, N dead, N blocked, N fragile

### Critical (runtime crashes, data loss, broken imports)
| # | Component | File:Line | Problem | Classification | Evidence |
|---|-----------|-----------|---------|----------------|----------|

### Dead (defined, never called in production)
| # | Component | File:Line | Last touched | Classification | Evidence |
|---|-----------|-----------|-------------|----------------|----------|

### Blocked (called but condition prevents execution)
| # | Component | File:Line | Blocking condition | Classification | Evidence |
|---|-----------|-----------|-------------------|----------------|----------|

### Fragile (works but brittle wiring)
| # | Component | File:Line | Risk | Classification | Evidence |
|---|-----------|-----------|------|----------------|----------|

### OK (verified working)
Brief summary of what was checked and confirmed working.

### Recommendations
Prioritized list: what to fix now vs later vs never.
```

---

## Checklist for Each Domain

### Functions / Methods
- [ ] Every public function is called from at least one production path
- [ ] Every class method is called on at least one instance
- [ ] No functions exist only because tests reference them (unless intentional fixtures)
- [ ] No imported-but-never-called functions

### Handlers / Dispatch
- [ ] Every schema has a handler
- [ ] Every handler is in the dispatch table
- [ ] Dispatch keys match schema names exactly
- [ ] No handler references removed functions

### Registrations / Weights
- [ ] Every type in weights has a handler
- [ ] Every handler has all required weight entries
- [ ] Silent vs content generators are correctly categorized
- [ ] No type exists in one table but not others

### Database Tables
- [ ] Every defined table has both read and write code paths
- [ ] Every table referenced in code exists in migrations/schema
- [ ] No orphan migrations creating tables nothing uses
- [ ] Column names in code match actual schema

### Config / Environment
- [ ] Every .env.example key is read by code
- [ ] Every env read in code has a definition or default
- [ ] No dead config keys with hardcoded defaults that are never overridden

### Events / Signals
- [ ] Every emitted event has at least one listener
- [ ] Every listener has at least one emitter
- [ ] Event name strings match exactly between emit and listen

### Scheduled Jobs
- [ ] Every cron/interval job references an existing function
- [ ] Import paths in job registrations are correct
- [ ] Guard conditions (dormant, phase) don't permanently block

### Exports / Init Files
- [ ] Every re-export in `__init__.py` points to existing function
- [ ] Every `__all__` entry matches an actual export
- [ ] No alias exports that nothing imports through

### Constants / Enums
- [ ] Every constant is referenced outside its definition file
- [ ] Every enum member is used (not just the enum class)
- [ ] No shadowed constants

### Context / State
- [ ] Every context key that's read is also written somewhere
- [ ] No completed/done flags that permanently block features
- [ ] No circular dependencies in initialization

### Feature Flags / Gates
- [ ] Every feature gate can actually open
- [ ] No hardcoded `False` or impossible conditions
- [ ] Fallback paths work when feature is disabled

---

## Anti-patterns to Watch For

1. **Renamed but not everywhere**: function renamed in definition, old name in caller
2. **Moved but not re-exported**: module restructured, old import path broken
3. **Guard added, bootstrap missing**: condition checks for data that's only set after the guarded code runs
4. **Schema removed, handler stays**: tool schema deleted but dispatch entry and handler function remain
5. **Table created, code removed**: database table in schema but no code reads/writes it
6. **Re-export alias, no callers**: `__init__.py` exports alias but all callers import directly
7. **Default swallows missing**: `dict.get(key, default)` silently returns default for typo'd keys
8. **Test-only code**: functions exist only because tests call them, no production path
9. **Method on used class**: class is imported and instantiated, but specific method is never called
10. **Config defined, never read**: `.env.example` has keys that no code references
11. **Event emitted, nobody listens**: `.emit("event_name")` but no `.on("event_name")`
12. **Enum member unused**: `Status.ARCHIVED` defined but never checked or set
13. **Migration without model**: table exists in DB but no ORM model or query references it
14. **Dynamic key mismatch**: `handlers[msg.type]` but `msg.type` never equals a registered key

---

## Tips for Efficiency

- **Inventory first, trace second.** Never skip Phase 2 — it's what prevents missed findings.
- Use `Grep` with `output_mode: "files_with_matches"` to quickly find all files that reference a function
- Cross-reference definition files with import files — mismatches are findings
- For large codebases, audit one domain per agent (tools, heartbeats, vault, API, etc.)
- Start from registries and dispatch tables — they're the "switchboard" of the system
- Check `__init__.py` files — they're where broken re-exports hide
- `git log --diff-filter=D -- path` shows deleted files that might still be referenced
- When checking method calls, remember Python patterns: `getattr(obj, name)`, `**kwargs`, `super().method()`
- For constants, check both `from module import CONST` and `module.CONST` patterns
