---
name: system-integrity-audit
description: "Deep system integrity audit: finds dead code, broken wiring, unreachable components, blocked conditions, and orphaned registrations. Checks that every defined component is actually called, every registration leads to execution, and no condition permanently blocks a code path. Enriches findings with git blame, code comments, and docs to classify intent (dead vs planned vs deprecated)."
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
- For security audit — use a dedicated security audit skill

---

## Audit Protocol

### Phase 1: Understand the System

1. Read project CLAUDE.md — structure, entry points, conventions
2. `git log --oneline -30` — recent changes, what was added/removed
3. Identify key registries and dispatch tables:
   - Handler registrations (dict of name → function)
   - Schema/tool definitions (list of schemas)
   - Scheduled jobs (cron, intervals)
   - Weight/config tables (what types are defined)
   - Export lists (`__init__.py`, `__all__`)
   - Route registrations (URL → handler, callback → function)

### Phase 2: Trace Every Wire (parallel agents recommended)

Launch 3-5 research agents in parallel, each covering one domain. Each agent should check:

#### For every DEFINED component:
```
1. Is it imported somewhere outside its own file?
2. Is it called/referenced in runtime code (not just tests)?
3. Can the call path actually be reached? (no always-false guards)
4. If registered in a dispatch table — does the key match what callers send?
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

### Phase 3: Classify Intent (critical step)

For each finding, **before marking it as dead code**, check:

1. **Git blame**: when was it added? By whom? Is there a commit message explaining intent?
   ```bash
   git log --oneline --follow -5 -- path/to/file.py
   git log --all --oneline --grep="function_name"
   ```

2. **Code comments**: is there a `# TODO`, `# PLANNED`, `# DEPRECATED`, `# v2` marker?

3. **Documentation**: is it mentioned in specs, tasks.md, or CLAUDE.md as planned/future work?

4. **Tests**: does it have tests? Tests without production callers may indicate:
   - Planned feature (tests written first, integration pending)
   - Removed feature (integration removed, tests left behind)
   - Library function (used by external consumers)

Classify each finding:

| Classification | Meaning | Action |
|---|---|---|
| **DEAD** | No intent to use, no docs, stale | Remove or flag for removal |
| **ORPHANED** | Was connected, connection broken by refactor | Reconnect or remove |
| **PLANNED** | Docs/comments indicate future use | Leave, note in report |
| **DEPRECATED** | Replaced but not cleaned up | Remove, update docs |
| **BLOCKED** | Condition prevents execution | Fix condition or remove |
| **FRAGILE** | Works but depends on implicit assumptions | Add explicit check or doc |

### Phase 4: Report

Structure the report as follows:

```markdown
## System Integrity Audit — [Project Name]

### Critical (runtime crashes, data loss)
| # | Component | Problem | Classification | Evidence |
|---|-----------|---------|----------------|----------|

### Dead (defined, never called)
| # | Component | Last touched | Classification | Evidence |
|---|-----------|-------------|----------------|----------|

### Blocked (called but condition prevents execution)
| # | Component | Blocking condition | Classification | Evidence |
|---|-----------|-------------------|----------------|----------|

### Fragile (works but brittle wiring)
| # | Component | Risk | Classification | Evidence |
|---|-----------|------|----------------|----------|

### OK (verified working)
Brief summary of what was checked and confirmed working.

### Recommendations
Prioritized list: what to fix now vs later vs never.
```

---

## Checklist for Each Domain

### Handlers / Dispatch
- [ ] Every schema has a handler
- [ ] Every handler is in the dispatch table
- [ ] Dispatch keys match schema names exactly
- [ ] No handler references removed functions

### Registrations / Weights
- [ ] Every type in weights has a handler
- [ ] Every handler has all required weight entries (base, time_window, recency)
- [ ] Silent vs content generators are correctly categorized
- [ ] No type exists in one table but not others

### Scheduled Jobs
- [ ] Every cron/interval job references an existing function
- [ ] Import paths in job registrations are correct
- [ ] Guard conditions (dormant, phase) don't permanently block

### Exports / Init Files
- [ ] Every re-export in `__init__.py` points to existing function
- [ ] Every `__all__` entry matches an actual export
- [ ] No alias exports that nothing imports through

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

---

## Tips for Efficiency

- Use `Grep` with `output_mode: "files_with_matches"` to quickly find all files that reference a function
- Cross-reference definition files with import files — mismatches are findings
- For large codebases, audit one domain per agent (tools, heartbeats, vault, API, etc.)
- Start from registries and dispatch tables — they're the "switchboard" of the system
- Check `__init__.py` files — they're where broken re-exports hide
- `git log --diff-filter=D -- path` shows deleted files that might still be referenced
