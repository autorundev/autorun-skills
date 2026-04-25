---
name: commit
description: "Auto-commit and push. Triggers after each logical block of work — new feature, bugfix, config update, refactoring, documentation change, end of session. No questions asked."
---

# Commit

Automatic commit and push to remote.

## When to trigger

- Added new functionality
- Fixed a bug
- Updated config, documentation, or directives
- Finished refactoring
- End of work session (if there are uncommitted changes)

**No questions.** Do not ask "should I commit?", "push?", "what message?" — just do it.

---

## Workflow

### Step 1: Check status

```bash
git status
```

If no changes — do nothing, exit.

### Step 2: Stage files

```bash
git add <specific files by name>
```

**Rules:**
- NEVER use `git add .` or `git add -A`
- Add only specific changed files by name
- Review the diff before staging: `git diff <file>` if unsure

**Never commit:**
- `.env`, secrets, tokens, keys
- `tmp/`, `_tmp/` — temporary directories
- `__pycache__/`, `.DS_Store`, `node_modules/`
- Large binaries unless intentional

### Step 3: Commit

Use a conventional commit prefix matching project style. Check recent commits with `git log --oneline -5` to match the convention.

Common prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `deps:`, `test:`, `proto:`, `chore:`

```bash
git commit -m "$(cat <<'EOF'
prefix: concise description of what was done

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**Message rules:**
- One line, concise description of what was done
- Use English for commit messages
- Examples: `feat: YouTube parser`, `fix: export bug with empty fields`, `docs: update CLAUDE.md architecture section`

### Step 4: Push

```bash
git push
```

**If upstream is not set:**
```bash
git push -u origin $(git branch --show-current)
```

**If push fails:**
- No permissions / auth error — report to user, do not retry
- Diverged history — report to user, suggest `git pull --rebase` then push
- No remote configured — report to user

---

## Rules

- Work in the **current branch** — do not create new branches without being asked
- For isolated work use the `worktree` skill
- If working in a project subdirectory, use `git -C <project-root>` to ensure correct repo context

---

## Completion checklist

- [ ] `git status` — changes exist
- [ ] `git add` specific files (no .env, no tmp/, no secrets)
- [ ] `git commit` with conventional prefix and English message
- [ ] `git push` succeeded (or upstream set with `-u`)
