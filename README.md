# autorun-skills

Custom skills (slash commands) for [Claude Code](https://claude.com/claude-code).

## Installation

Copy any skill directory into `~/.claude/skills/`:

```bash
# Single skill
cp -r system-integrity-audit ~/.claude/skills/

# All skills
cp -r */ ~/.claude/skills/
```

Skills are available immediately as `/skill-name` in Claude Code.

## Skills

### Development Workflow
| Skill | Description |
|-------|-------------|
| `commit` | Auto-commit, push and .env backup |
| `deploy` | Manual deploy via Docker + Git |
| `tdd` | Test-driven development with RED-GREEN-REFACTOR cycle |
| `worktree` | Git worktree management for parallel work |
| `db-migrations` | Database migration management (SQLite, PostgreSQL) |

### Code Quality
| Skill | Description |
|-------|-------------|
| `system-integrity-audit` | Deep wiring audit: finds dead code, broken connections, unreachable components |
| `architecture-review` | System design audit: complexity, coupling, scalability |
| `docs-cleaner` | Consolidate redundant documentation |
| `simplify` | Review changed code for reuse and efficiency |
| `qa-expert` | Comprehensive QA testing process |
| `promptfoo-evaluation` | LLM prompt evaluation with Promptfoo |

### Frontend & Design
| Skill | Description |
|-------|-------------|
| `frontend-design` | Production-grade frontend interfaces |
| `design-review` | Visual design quality review |
| `interface-design` | Persistent design system management |
| `tailwind-theme-builder` | Tailwind v4 + shadcn/ui setup |
| `a11y-audit` | WCAG 2.1 accessibility audit |
| `web-design-guidelines` | Web Interface Guidelines compliance |

### UX Research
| Skill | Description |
|-------|-------------|
| `empathy-map` | 4-quadrant empathy map synthesis |
| `journey-map` | End-to-end user journey mapping |
| `experience-map` | Holistic experience ecosystem map |
| `card-sort-analysis` | Card sorting results analysis |
| `jobs-to-be-done` | JTBD framework mapping |
| `opportunity-framework` | Impact-effort prioritization |
| `ux-writing` | UI copy: microcopy, errors, empty states |

### Infrastructure
| Skill | Description |
|-------|-------------|
| `docker` | Docker containerization |
| `docker-debug` | Docker/compose debugging |
| `ssh-connect` | Reliable SSH connections via expect |
| `3x-ui-setup` | VPN server setup (VLESS Reality) |
| `performance-profiler` | Python/Docker performance profiling |

### Integrations
| Skill | Description |
|-------|-------------|
| `install-mcp` | MCP server installation for Claude Code |
| `mcp-builder` | Build MCP servers (Python/Node) |
| `claude-api` | Build apps with Claude API / Anthropic SDK |
| `tavily` | Web search and URL extraction via Tavily |

### Project-Specific
| Skill | Description |
|-------|-------------|
| `vectoros-security-audit` | Security audit for VectorOS |

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
