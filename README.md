# autorun-skills

Custom skills for [Claude Code](https://claude.com/claude-code). Written for real projects — VPN setup, deployment, security audits, Docker debugging, and more. Russian-first, battle-tested.

## Installation

```bash
# Single skill
cp -r security-audit ~/.claude/skills/

# All skills
cp -r */ ~/.claude/skills/
```

Skills are available immediately as `/skill-name` in Claude Code.

## Skills

### Development Workflow
| Skill | Description |
|-------|-------------|
| `commit` | Auto-commit, push and .env backup. Triggers after each logical block of work. |
| `deploy` | Manual deploy to any server via Docker + Git (first deploy + updates). |
| `worktree` | Git worktree management for parallel Claude agents on one project. |
| `db-migrations` | Database migration management for SQLite and PostgreSQL (Alembic, raw SQL). |

### Code Quality & Security
| Skill | Description |
|-------|-------------|
| `system-integrity-audit` | Deep wiring audit: builds complete inventory of all definitions, then traces every wire. Finds dead code, orphaned registrations, unused DB tables, phantom config. |
| `architecture-review` | System design audit: complexity, coupling, scalability, maintainability, security posture. |
| `security-audit` | AI application security: prompt injection, tool abuse, data exfiltration, credential exposure, multi-user isolation, context poisoning, output sanitization. Works with any LLM-based app. |
| `performance-profiler` | Python/Docker performance profiling: cProfile, memory_profiler, py-spy, async profiling, container metrics. |

### Infrastructure
| Skill | Description |
|-------|-------------|
| `docker` | Docker containerization for projects. |
| `docker-debug` | Docker/compose debugging: container inspection, log analysis, network, volumes. |
| `ssh-connect` | Reliable SSH connections via expect. Handles hangs, password auth, SCP/rsync. |
| `3x-ui-setup` | Complete VPN server setup: server hardening + 3x-ui (Xray) with VLESS Reality or VLESS TLS. |
| `install-mcp` | MCP server installation, removal, configuration and debugging for Claude Code. |

### Integrations
| Skill | Description |
|-------|-------------|
| `tavily` | Web search and URL content extraction via Tavily API. Fallback when WebFetch fails. |

## Other Skills We Use (not included)

Generic English-language skills we also install. Not customized — similar versions available on [skills.sh](https://skills.sh):

| Skill | Description |
|-------|-------------|
| `tdd` | Test-driven development (RED-GREEN-REFACTOR cycle) |
| `frontend-design` | Production-grade frontend interfaces |
| `game-design` | Game mechanics design and tuning |
| `qa-expert` | QA testing process (Google Testing Standards) |
| `mcp-builder` | Build MCP servers (Python FastMCP / Node) |
| `docs-cleaner` | Consolidate redundant documentation |
| `ux-writing` | UI copy: microcopy, errors, empty states, CTAs |

## Skill Format

Each skill is a directory with a `SKILL.md` file:

```yaml
---
name: skill-name
description: "What the skill does and when to use it."
---

# Skill Title

Instructions for the AI agent...
```

## License

MIT
