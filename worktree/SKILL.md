---
name: worktree
description: "Create and manage git worktrees for parallel isolated work. Use when multiple Claude agents need to work on the same project simultaneously, for isolated experiments with easy rollback, or for feature branches that should not touch main."
---

# Git Worktree Manager

Manage isolated working copies of a project via git worktree. Enables multiple Claude agents to work in parallel on the same project without interfering with each other.

## When to activate

- User says: "create worktree", "work in a separate branch", "do this in isolation"
- User wants parallel work: "do X and Y in parallel", "run this separately"
- User wants an experiment with rollback: "try this but make it reversible"
- User says: "merge worktree", "delete worktree", "list worktrees"

## Important: use absolute paths

All commands MUST use absolute paths. CWD resets between bash calls. Use `git -C <PROJECT_ROOT>` for git commands targeting a specific repo.

Example: if project is at `/home/anton/ernest`, use:
```bash
git -C /home/anton/ernest worktree add ...
```

---

## Operations

### 1. Create worktree

**Argument:** `$ARGUMENTS` = worktree name (e.g.: `research`, `content`, `experiment`)
**Requires:** `$PROJECT_ROOT` = absolute path to the project (e.g.: `/home/anton/ernest`)

```bash
# Safety: verify .claude/worktrees/ is actually ignored (covers wildcards, parent .gitignore, global ignore)
if ! git -C $PROJECT_ROOT check-ignore -q .claude/worktrees/.test 2>/dev/null; then
  echo '.claude/worktrees/' >> $PROJECT_ROOT/.gitignore
  git -C $PROJECT_ROOT add .gitignore
  git -C $PROJECT_ROOT commit -m "chore: ignore .claude/worktrees/" --no-verify
fi

# Create worktree with a dedicated branch
git -C $PROJECT_ROOT worktree add $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS -b worktree-$ARGUMENTS
```

**Why `git check-ignore` instead of `grep`:** grep misses wildcard rules (e.g. `.claude/*`), inherited rules from parent `.gitignore`, and global gitignore. `git check-ignore` asks git directly — single source of truth. If the directory is not ignored, worktree contents leak into commits.

After creation, tell the user:
```
Worktree "$ARGUMENTS" created.
- Path: $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS/
- Branch: worktree-$ARGUMENTS
- All file operations will now target this worktree.

When done — say "merge worktree $ARGUMENTS" to bring changes into the main branch.
```

**After creation — switch ALL work to the worktree:**
- ALL file reads/writes use `$PROJECT_ROOT/.claude/worktrees/$ARGUMENTS/path/to/file`
- Run scripts: `cd $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS && python3 ...`
- Do NOT touch files in the project root

### 2. List all worktrees

```bash
git -C $PROJECT_ROOT worktree list
```

### 3. Merge worktree

**Argument:** `$ARGUMENTS` = worktree name to merge

```bash
# 1. Stage and check for uncommitted changes in the worktree
git -C $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS add -A && git -C $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS status
```

If there are changes to commit:
```bash
git -C $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS commit -m "$(cat <<'EOF'
worktree $ARGUMENTS: description of changes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

```bash
# 2. Merge from the project root
git -C $PROJECT_ROOT merge worktree-$ARGUMENTS --no-edit
```

If merge conflict — show conflicting files to the user and help resolve. Then `git -C $PROJECT_ROOT add <files>` + `git -C $PROJECT_ROOT commit`.

After successful merge, ask: "Delete worktree $ARGUMENTS? Changes are already in the main branch."

### 4. Delete worktree

**Argument:** `$ARGUMENTS` = worktree name to delete

```bash
git -C $PROJECT_ROOT worktree remove $PROJECT_ROOT/.claude/worktrees/$ARGUMENTS
git -C $PROJECT_ROOT branch -d worktree-$ARGUMENTS
```

### 5. Cleanup stale worktrees

Run after deleting worktree directories manually or if git reports stale entries:

```bash
git -C $PROJECT_ROOT worktree prune
```

---

## Rules for working inside a worktree

1. **All paths** — via `$PROJECT_ROOT/.claude/worktrees/<name>/`, NEVER via project root
2. **Scripts** — `cd $PROJECT_ROOT/.claude/worktrees/<name> && python3 ...`
3. **Results/temp files** — in `$PROJECT_ROOT/.claude/worktrees/<name>/tmp/...`
4. **Commit often** — small commits = clean merge
5. **Do not touch the project root** — only your worktree
6. **CLAUDE.md and skills** — read from the project root (shared across all worktrees)
7. **Two agents MUST NOT write to the same file** — split work by file boundaries

---

## Error handling

| Error | Resolution |
|-------|------------|
| `fatal: is not a git repository` | Project not initialized as git repo. Run `git init` in the project root |
| `fatal: '$ARGUMENTS' is already checked out` | Worktree with this name already exists. Show `git worktree list` |
| `error: branch 'worktree-X' not found` | Branch already deleted. Remove directory: `rm -rf $PROJECT_ROOT/.claude/worktrees/X` and run `git worktree prune` |
| Merge conflict | Show conflicting files, help resolve, then `git add` + `git commit` |
| `fatal: '$PATH' is a missing but locked worktree` | Remove lock: `git -C $PROJECT_ROOT worktree unlock $PATH` then `git worktree prune` |
