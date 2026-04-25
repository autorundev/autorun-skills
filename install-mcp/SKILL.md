---
name: install-mcp
description: >
  Install, remove, configure, or debug MCP servers for Claude Code. Covers correct
  claude mcp add syntax, scope options, common errors and fixes. Triggers on: "install mcp",
  "add mcp server", "mcp not working", "configure mcp", "remove mcp", "mcp timeout",
  "mcp connection error", "setup mcp".
allowed-tools: Bash
---

# Installing MCP Servers for Claude Code

## Prerequisites

- **OS:** macOS / Linux
- **Node:** v20+ with npx available
- **Claude CLI:** installed and in PATH
- **MCP config:** `~/.claude.json` contains `mcpServers` section

---

## Correct Command Format

```bash
claude mcp add --transport stdio --env KEY=value <server_name> -- npx -y @namespace/package
```

### Critical Rules

1. **All flags BEFORE the server name:** `--transport`, `--env`, `--scope`
2. **`--` separates the launch command** from Claude CLI arguments
3. **Always use `-y` with npx** -- otherwise npx waits for confirmation and stdio hangs
4. **Default scope = local** (saves to `~/.claude.json`)

---

## Installation Examples

### Playwright (browser automation)
```bash
claude mcp add --transport stdio playwright -- npx -y @playwright/mcp@latest --output-dir tmp/.playwright-mcp
```

### GitHub
```bash
claude mcp add --transport stdio --env GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx github -- npx -y @modelcontextprotocol/server-github
```

### Context7 (library documentation)
```bash
claude mcp add --transport stdio --env CONTEXT7_API_KEY=ctx7sk-xxx context7 -- npx -y @upstash/context7-mcp@latest
```

### Figma
```bash
claude mcp add --transport stdio --env FIGMA_ACCESS_TOKEN=fig_xxx figma -- npx -y figma-developer-mcp --stdio
```

### n8n
```bash
claude mcp add --transport stdio --env N8N_API_URL=https://xxx --env N8N_API_KEY=xxx --env MCP_MODE=stdio --env LOG_LEVEL=error n8n -- npx -y n8n-mcp
```

### Python-based MCP server (via uvx)
```bash
claude mcp add --transport stdio <server_name> -- uvx <package_name>
```

### HTTP/SSE server (no npx)
```bash
claude mcp add --transport http <server_name> <url>
```

---

## Scope: Where Config Is Saved

| Flag | Config file | When to use |
|------|-------------|-------------|
| (default / `--scope local`) | `~/.claude.json` | Personal server, this machine only |
| `--scope project` | `.mcp.json` in project root | Shared with team (committed to git) |
| `--scope user` | `~/.claude.json` | Cross-project personal server |

---

## Management and Debugging

```bash
claude mcp list                 # list all servers and their status
claude mcp get <name>           # show details for a specific server
claude mcp remove <name>        # remove a server
```

Inside Claude Code: type `/mcp` to see status of all servers + OAuth authorization.

### Updating a server

There is no `update` command. Remove and re-add:
```bash
claude mcp remove <name> && claude mcp add --transport stdio <name> -- npx -y @namespace/package@latest
```

### If a server is not working

1. Verify the package runs standalone: `npx -y @namespace/package --help`
2. Increase startup timeout: `MCP_TIMEOUT=10000 claude`
3. Increase output limit: `MAX_MCP_OUTPUT_TOKENS=50000 claude`
4. Check logs: `~/.claude/logs/`
5. Test with verbose output: run the npx command directly and check stderr

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Flags are ignored | Written after the server name | Move all flags BEFORE the server name |
| `Connection closed` | npx waiting for confirmation | Add `-y` flag to npx |
| Timeout on startup | Slow package download | Set `MCP_TIMEOUT=10000` |
| Duplicate configs | Both `~/.claude.json` and `~/.claude/mcp_servers.json` exist | Remove the duplicate |
| `ENOENT` / command not found | npx not in PATH or wrong package name | Verify: `which npx`, check package name on npm |
| Server shows "errored" in `/mcp` | Crash during init | Run the npx command manually to see the error |
