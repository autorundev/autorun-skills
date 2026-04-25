---
name: docker
description: "Docker containerization skill for service projects. Use when the user creates a service (bot, API, web app), mentions Docker or containers, asks to deploy a project to a server, or asks to run/configure a service. Covers Dockerfile creation, docker-compose setup, stack auto-detection, smart rebuild strategy, security practices, and layer caching. Triggers on: dockerfile, docker-compose, containerize, deploy service, run in docker, docker setup."
allowed-tools: Bash,Read,Write,Edit,Glob,Grep
---

# Docker: Project Containerization

Use when: user creates a service (bot, API, web application), mentions Docker/containers, asks to deploy a project to a server, or asks to run/configure a service.

Do NOT use for: one-off scripts, parsers, utilities, content projects.

---

## Core Rule

All service projects (bots, APIs, web applications) -- ONLY through Docker. No questions, no "maybe without Docker?". If a project runs continuously -- it goes in a container.

## What to Create

For every service project, always create:
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

## Stack Auto-Detection

Detect the stack from project files:

| File | Stack | Base Image |
|------|-------|------------|
| `requirements.txt` / `pyproject.toml` | Python | `python:3.x-slim` |
| `package.json` | Node.js | `node:lts-alpine` |
| `go.mod` | Go | `golang:1.x-alpine` (build) + `alpine` (runtime) |
| `Cargo.toml` | Rust | `rust:1.x` (build) + `debian:slim` (runtime) |

If the stack cannot be determined -- ask the user.

## Smart Rebuild Strategy

**Do NOT rebuild the container after every code change!**

| What Changed | Action |
|-------------|--------|
| Code (`.py`, `.js`, `.go`, etc.) | NO rebuild. Use **volumes** -- code is mapped into the container, changes are instant |
| Dependencies (`requirements.txt`, `package.json`, `go.mod`) | Rebuild: `docker compose up --build` |
| `Dockerfile` or `docker-compose.yml` | Rebuild: `docker compose up --build` |
| Deploy to server | Always full rebuild |

## Security

- Pass `.env` via `env_file` in docker-compose
- **NEVER** copy `.env` into the image (no `COPY .env`)
- **NEVER** hardcode secrets in Dockerfile
- Add `.env` to `.dockerignore`

## Dockerfile Best Practices

1. **Slim/alpine images** -- minimal size
2. **Non-root user** -- do not run the application as root
3. **Multi-stage build** for production (especially Go, Rust, frontend)
4. **Layer caching** -- copy dependencies first, then code:
   ```dockerfile
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   ```
5. **HEALTHCHECK** -- for services with HTTP endpoints
6. **Explicit EXPOSE** -- document the port the service listens on
7. **Pin versions** -- use specific image tags, not `latest`

## docker-compose.yml Template

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./src:/app/src  # live-reload for development
    ports:
      - "${PORT:-8000}:8000"
```

## .dockerignore Template

```
.env
.git
__pycache__
*.pyc
node_modules
.venv
venv
tmp/
*.log
.DS_Store
```

## Step-by-Step Workflow

1. Detect the project stack (auto-detect or ask)
2. Create `Dockerfile` following best practices
3. Create `docker-compose.yml` with volumes for dev
4. Create `.dockerignore`
5. Verify build: `docker compose build`
6. Start: `docker compose up -d`
7. Check logs: `docker compose logs -f`

## Common Patterns

### Python Bot (aiogram / Flask / FastAPI)

```dockerfile
FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
USER app

CMD ["python", "-m", "src.main"]
```

### Node.js App

```dockerfile
FROM node:lts-alpine

RUN addgroup -S app && adduser -S app -G app
WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
USER app

EXPOSE 3000
CMD ["node", "src/index.js"]
```

### Multi-Stage Go Build

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o app ./cmd/main.go

FROM alpine:3.19
RUN adduser -D app
WORKDIR /app
COPY --from=builder /build/app .
USER app
CMD ["./app"]
```
