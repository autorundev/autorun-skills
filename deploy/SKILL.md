---
name: deploy
description: "Manual deploy of any project to a remote server via Docker + Git. Handles first deploy (clone + build) and updates (git pull + rebuild). Triggers on: /deploy, deploy, update on server."
trigger: manual
---

# Deploy: Ship to Server

**Use when:** user says "/deploy", "deploy", "update on server", "ship it", "push to production".

**Do NOT use for:** changing server configs without deploying, working with n8n (has its own workflow).

---

## Environment Variables

Server connection variables (from the `ssh-connect` skill or project `.env`):

```env
SERVER_HOST=192.168.1.100
SERVER_PORT=22
SERVER_USER=root
SERVER_SSH_KEY=~/.ssh/id_ed25519
SERVER_PASSWORD=
SERVER_SUDO_PASSWORD=
```

Deploy-specific variables:

```env
DEPLOY_PATH=/opt/myproject       # project path on the server
DEPLOY_BRANCH=main               # branch to deploy (default: main or master)
```

If `DEPLOY_PATH` is missing — ask the user and suggest `/opt/<project-name>/`.
If `DEPLOY_BRANCH` is missing — use current branch from `git branch --show-current`.

---

## Step 0: Pre-flight checks (local)

Run ALL checks before deploying:

| # | Check | Command | If failed |
|---|-------|---------|-----------|
| 1 | Dockerfile exists | `test -f Dockerfile` | "No Dockerfile. Run `/docker`?" |
| 2 | docker-compose.yml exists | `test -f docker-compose.yml` | "No docker-compose.yml. Run `/docker`?" |
| 3 | Git remote configured | `git remote get-url origin` | "No remote. Create a GitHub repo and add remote" |
| 4 | All changes committed | `git status --porcelain` | Suggest committing first |
| 5 | Commits pushed | `git log @{u}..HEAD 2>/dev/null` | Suggest pushing first |
| 6 | .env has SERVER_HOST | `grep SERVER_HOST .env` | Ask for server credentials |
| 7 | SSH to server works | ssh ... `echo ok` (via ssh-connect) | "Server unreachable" |

If checks 1-5 fail — suggest fixing and wait. Do NOT deploy with dirty state.

---

## Step 1: Determine deploy type

```bash
# Via ssh-connect:
ssh ... "test -d <DEPLOY_PATH>/.git && echo UPDATE || echo FIRST"
```

- `FIRST` -- go to **Step 2A: First Deploy**
- `UPDATE` -- go to **Step 2B: Update**

Tell the user: "Detected [FIRST DEPLOY / UPDATE] for `<project-name>` on `<SERVER_HOST>`"

---

## Step 2A: First Deploy

### 2A.1. Create directory on server

```bash
ssh ... "mkdir -p <DEPLOY_PATH>"
```

If Permission denied — use sudo:
```bash
ssh ... "sudo mkdir -p <DEPLOY_PATH> && sudo chown <SERVER_USER>:<SERVER_USER> <DEPLOY_PATH>"
```

### 2A.2. Verify GitHub access from server

```bash
ssh ... "git ls-remote <REPO_URL> HEAD 2>/dev/null && echo OK || echo FAIL"
```

If FAIL (private repo) — provide instructions:

```
Private repo. Configure access on the server:

Option 1 — PAT (Personal Access Token):
1. GitHub -> Settings -> Developer Settings -> Fine-grained tokens -> Generate
2. On the server:
   git config --global credential.helper store
   git clone https://<USERNAME>:<PAT>@github.com/<OWNER>/<REPO>.git

Option 2 — Deploy Key:
1. On server: ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
2. Copy public key: cat ~/.ssh/deploy_key.pub
3. GitHub -> Repo -> Settings -> Deploy Keys -> Add
4. git clone git@github.com:<OWNER>/<REPO>.git
```

Wait for the user to configure access. Then retry the check.

### 2A.3. Clone the repo

```bash
ssh ... "git clone <REPO_URL> <DEPLOY_PATH> && cd <DEPLOY_PATH> && git checkout <DEPLOY_BRANCH>"
```

If DEPLOY_PATH already exists and is non-empty (but no .git):
```bash
ssh ... "cd <DEPLOY_PATH> && git init && git remote add origin <REPO_URL> && git fetch && git checkout -f <DEPLOY_BRANCH>"
```

### 2A.4. Copy .env to server

```bash
# Via ssh-connect (SCP pattern):
scp ... .env <SERVER_USER>@<SERVER_HOST>:<DEPLOY_PATH>/.env
```

If no local .env — warn: "No local .env file. If the server needs one, create it and re-run `/deploy`."

### 2A.5. Build and start

```bash
ssh ... "cd <DEPLOY_PATH> && docker compose up -d --build"
```

If `docker compose` not found — try legacy command:
```bash
ssh ... "cd <DEPLOY_PATH> && docker-compose up -d --build"
```

### 2A.6. Proceed to **Step 3: Verification**

---

## Step 2B: Update

### 2B.1. Git pull

```bash
ssh ... "cd <DEPLOY_PATH> && git pull origin <DEPLOY_BRANCH>"
```

If git pull fails:

| Error | Resolution |
|-------|------------|
| `uncommitted changes` | Ask user: "Server has local changes. Reset? (git reset --hard origin/BRANCH)" |
| `merge conflict` | Ask: "Merge conflict. Reset to remote? (git reset --hard origin/BRANCH)" |
| `authentication failed` | Token expired. Provide PAT renewal instructions |

### 2B.2. Check .env sync

```bash
# Download server .env to temp file
scp ... <SERVER_USER>@<SERVER_HOST>:<DEPLOY_PATH>/.env /tmp/server_env_check

# Compare
diff .env /tmp/server_env_check
rm /tmp/server_env_check
```

If differences found — ask: "Local .env differs from server. Update on server?"

If user confirms:
```bash
scp ... .env <SERVER_USER>@<SERVER_HOST>:<DEPLOY_PATH>/.env
```

### 2B.3. Rebuild and restart

```bash
ssh ... "cd <DEPLOY_PATH> && docker compose up -d --build"
```

### 2B.4. Proceed to **Step 3: Verification**

---

## Step 3: Verification

### 3.1. Are containers running?

```bash
ssh ... "cd <DEPLOY_PATH> && docker compose ps"
```

All containers must be "Up". If any are down — show logs for the failed container.

### 3.2. Logs clean?

```bash
ssh ... "cd <DEPLOY_PATH> && docker compose logs --tail=30 2>&1"
```

If logs contain `Error`, `Exception`, `FATAL`, `Traceback` — show to the user.

### 3.3. Print summary

```
Deploy complete!
- Project: <name>
- Server: <SERVER_HOST>
- Path: <DEPLOY_PATH>
- Containers: <list with status>
- Logs: clean / <N warnings>
```

---

## Rollback

If user says "rollback", "revert", "go back to previous version":

```bash
# Show recent commits
ssh ... "cd <DEPLOY_PATH> && git log --oneline -5"

# Ask which commit to roll back to

# Roll back (creates detached HEAD)
ssh ... "cd <DEPLOY_PATH> && git checkout <COMMIT_HASH> && docker compose up -d --build"
```

To return to the branch tip:
```bash
ssh ... "cd <DEPLOY_PATH> && git checkout <DEPLOY_BRANCH> && docker compose up -d --build"
```

---

## Managing .env on server

| Action | Command |
|--------|---------|
| View | `ssh ... "cat <DEPLOY_PATH>/.env"` |
| Update from local | `scp ... .env <USER>@<HOST>:<DEPLOY_PATH>/.env` |
| Restart after update | `ssh ... "cd <DEPLOY_PATH> && docker compose restart"` |

---

## Error handling

| Error | Resolution |
|-------|------------|
| `git clone` fails | Private repo -- configure PAT/Deploy Key (see step 2A.2) |
| `docker compose build` fails | Show build logs. Try `--no-cache` |
| Container won't start (exit 1) | `docker compose logs <service>` -- show to user |
| Port already in use | `ssh ... "sudo lsof -i :<PORT>"` -- suggest alternative port |
| Disk full | `ssh ... "df -h"` -- suggest `docker system prune` |
| Docker not installed | Instructions: `curl -fsSL https://get.docker.com \| sh` |
| git not installed | `sudo apt install git` / `sudo yum install git` |

---

## Important rules

- All SSH commands go through the **ssh-connect** skill (expect templates). No raw ssh/scp
- All projects deploy via **Docker** (docker compose). No exceptions
- Code is delivered via **git** (clone/pull), NOT via scp
- **Do NOT touch** containers or files belonging to other projects on the server
- **Do NOT delete** anything on the server without user confirmation
