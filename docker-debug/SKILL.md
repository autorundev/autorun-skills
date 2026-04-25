---
name: docker-debug
description: "Docker and docker-compose debugging skill. Use when containers crash, fail to start, consume too much memory, have networking issues, volume problems, or when logs show errors. Covers container inspection, log analysis, network debugging, volume issues, resource limits, and common failure patterns. Triggers on: container crash, docker not starting, cannot connect, container keeps restarting, OOM killed, docker network issue, volume not mounting, port in use, docker compose up fails, docker debug, container exited."
allowed-tools: Bash,Read,Edit,Grep
---

# Docker Debug

Diagnosing and fixing problems with Docker containers and docker-compose stacks.

---

## Quick Triage (start here)

```bash
# Overview -- what's running, what's down
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Recent Docker daemon events
docker events --since 30m --until now 2>/dev/null | tail -20

# Current resource usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Problematic containers (not running)
docker ps -a --filter "status=exited" --filter "status=restarting"
```

---

## Step 1: Log Analysis

```bash
# Last 100 lines
docker logs <container> --tail 100

# With timestamps
docker logs <container> --timestamps --tail 50

# Follow in real-time
docker logs -f <container>

# Only stderr (errors)
docker logs <container> 2>&1 | grep -i "error\|fatal\|exception\|traceback" | tail -30

# Logs from the last N minutes
docker logs <container> --since 10m

# If container is already removed -- check journald
journalctl -u docker.service --since "30 min ago" | grep <container_name>
```

### Error Patterns

```bash
# Python traceback
docker logs <container> 2>&1 | grep -A 10 "Traceback"

# OOM Kill (killed by kernel due to memory)
docker logs <container> 2>&1 | grep -i "killed\|oom"
dmesg | grep -i "oom\|killed" | tail -10

# Port already in use
docker logs <container> 2>&1 | grep "address already in use\|bind:"

# Permission denied
docker logs <container> 2>&1 | grep "permission denied\|EACCES"
```

---

## Step 2: Container Inspection

```bash
# Full container configuration
docker inspect <container>

# Specific fields
docker inspect <container> --format '{{.State.Status}}'
docker inspect <container> --format '{{.State.ExitCode}}'
docker inspect <container> --format '{{.State.Error}}'
docker inspect <container> --format '{{.HostConfig.RestartPolicy}}'

# Environment variables (filter out secrets!)
docker inspect <container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -v "PASSWORD\|TOKEN\|SECRET\|KEY"

# Mounted volumes
docker inspect <container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.Mode}}){{println}}{{end}}'

# Network settings
docker inspect <container> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}: {{$v.IPAddress}}{{println}}{{end}}'
```

---

## Step 3: Shell into Container

```bash
# Running container
docker exec -it <container> bash
docker exec -it <container> sh  # if bash is not available

# Crashed container -- start with overridden entrypoint
docker run -it --entrypoint sh <image>

# Start with the same env vars as in compose
docker compose run --rm <service> bash

# Start with root privileges
docker exec -it -u root <container> bash
```

### Inside the container -- what to check

```bash
# Processes
ps aux

# Open ports
ss -tlnp  # or netstat -tlnp

# Disk space
df -h

# Files in the working directory
ls -la /app  # or wherever code lives

# File permissions
stat /app/vault.db
ls -la /app/data/

# Environment variables
env | grep -v "PASSWORD\|TOKEN\|SECRET"

# Can we reach other services?
curl -s http://nginx:80/health || wget -q -O- http://nginx:80/health
ping -c 2 <service_name>
```

---

## Step 4: Networking Issues

```bash
# List networks
docker network ls

# Inspect network -- who's in it
docker network inspect <network_name>

# Verify containers are in the same network
docker inspect <container1> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'
docker inspect <container2> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'

# DNS resolution inside container
docker exec <container> nslookup <service_name>
docker exec <container> cat /etc/hosts
docker exec <container> cat /etc/resolv.conf

# Ports on host
ss -tlnp | grep <port>
sudo lsof -i :<port>

# Is the port used by another container?
docker ps --format '{{.Names}}\t{{.Ports}}' | grep <port>
```

### Common Network Problems

| Symptom | Cause | Solution |
|---------|-------|----------|
| `Connection refused` | Service not listening or not started | Check logs, verify the service started |
| `Name or service not known` | Container not in the same network | Add to the same network in compose |
| `Address already in use` | Port occupied on host | `ss -tlnp \| grep <port>`, kill the process |
| `Connection timeout` | Firewall / UFW blocking | `ufw status`, check rules |

---

## Step 5: Volume Issues

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect <volume_name>

# Physical location of volume data
docker volume inspect <volume_name> --format '{{.Mountpoint}}'

# Check what's in the volume
docker run --rm -v <volume_name>:/data alpine ls -la /data

# Permissions on bind mount
ls -la /path/to/project/data/

# Common problem: file created as directory (or vice versa)
# If a volume mount creates a directory instead of a file:
file /path/to/expected/file.db

# Fix: remove the directory, create the file
rm -rf /path/to/expected/file.db
touch /path/to/expected/file.db
```

---

## Step 6: Resource Problems

```bash
# OOM -- container killed due to memory
docker inspect <container> --format '{{.State.OOMKilled}}'

# Memory limits
docker inspect <container> --format '{{.HostConfig.Memory}}'  # 0 = no limit

# Set limit in compose:
# deploy:
#   resources:
#     limits:
#       memory: 512M

# Disk space problems
df -h /var/lib/docker
docker system df  # how much space images/containers/volumes use

# Clean up unused resources (careful!)
docker system prune -f          # containers + networks + dangling images
docker volume prune -f          # ONLY unused volumes
docker image prune -a -f        # all unused images
```

---

## Step 7: Docker Compose Specific

```bash
# View final compose config (with .env resolved)
docker compose config

# Validate compose file
docker compose config --quiet && echo "OK"

# Recreate only one service
docker compose up -d --force-recreate <service>

# Rebuild image and restart
docker compose up -d --build <service>

# View service dependencies
docker compose config --services

# Start with verbose output
docker compose --verbose up

# Verify .env loaded correctly
docker compose run --rm <service> env | grep MY_VAR
```

### Common Compose Problems

```bash
# "Service X depends on Y which has failed"
docker compose logs <failing_service>  # check the dependency logs

# .env changed but container didn't pick it up
docker compose down && docker compose up -d

# "network not found" after docker system prune
docker compose down && docker compose up -d  # recreates networks

# Startup order (depends_on does NOT guarantee service readiness)
# Add healthcheck in compose:
# healthcheck:
#   test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
#   interval: 10s
#   retries: 3
```

---

## Step 8: Rebuilding from Scratch

When nothing else works:

```bash
# 1. Back up data
docker exec <container> cp /app/vault.db /tmp/vault.db.backup
docker cp <container>:/tmp/vault.db.backup ./vault.db.backup

# 2. Full stop
cd ~/docker && docker compose down -v  # -v removes volumes! only if certain
# or without removing volumes:
docker compose down

# 3. Clean service images
docker compose build --no-cache <service>

# 4. Bring back up
docker compose up -d

# 5. Check logs immediately
docker compose logs -f --tail 50
```

---

## Cheatsheet: Exit Codes

| Exit Code | Meaning | What to Do |
|-----------|---------|------------|
| 0 | Normal termination | Normal for one-shot containers |
| 1 | Application error | Check logs, Python traceback |
| 137 | OOM Kill (128+9) | Increase memory limit or optimize |
| 139 | Segfault (128+11) | Bug in a native library |
| 143 | SIGTERM (128+15) | Normal shutdown (docker stop) |
| 125 | Docker daemon error | Check docker inspect, permissions |
| 126 | Entrypoint not executable | chmod +x or fix entrypoint |
| 127 | Entrypoint not found | Check path in CMD/ENTRYPOINT |
