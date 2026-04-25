---
name: ssh-connect
description: >
  Reliable SSH connection to any server via expect. Use when you need to connect to a server,
  run SSH commands, transfer files (SCP/rsync), or when SSH hangs/drops. Triggers on: "ssh to",
  "connect to server", "run command on server", "copy file to server", "scp", "rsync", "deploy via ssh".
trigger: automatic
allowed-tools: Bash, AskUserQuestion
---

# SSH Connection via expect

**NEVER use bare `ssh`/`scp`/`rsync` -- ALWAYS wrap in `expect`.** Without expect, any interactive prompt will block execution forever.

## Prerequisites

Ensure `expect` is installed:
```bash
which expect || sudo apt-get install -y expect
```

## .env Variables

```env
SERVER_HOST=192.168.1.100
SERVER_PORT=22                       # default: 22
SERVER_USER=root
SERVER_SSH_KEY=~/.ssh/id_ed25519    # for key-based auth
SERVER_PASSWORD=                     # for password-based auth
SERVER_SUDO_PASSWORD=                # if sudo is needed
```

If variables are missing, ask the user via AskUserQuestion.

## Algorithm

1. Read `.env` and extract `SERVER_*` variables
2. No `SERVER_HOST` → ask the user for connection parameters
3. `SERVER_SSH_KEY` present → key-based auth. `SERVER_PASSWORD` present → password-based. Both → key-based (preferred)
4. Build expect script from the appropriate template, substitute parameters
5. On error → see troubleshooting table

## SSH Options (ALWAYS include)

```
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3"
```

## Template: Single Command (Key-Based)

```bash
expect -c '
set timeout 30
spawn ssh -i <KEY> -p <PORT> -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 <USER>@<HOST> "<COMMAND>"
expect {
    timeout { puts "ERROR: Connection timed out"; exit 1 }
    "yes/no" { send "yes\r"; exp_continue }
    "assword:" { send "<PASSWORD>\r"; exp_continue }
    "Connection refused" { puts "ERROR: Connection refused"; exit 1 }
    "Permission denied" { puts "ERROR: Permission denied"; exit 1 }
    "No route to host" { puts "ERROR: Host unreachable"; exit 1 }
    eof
}
foreach {pid spawnid os_error_flag value} [wait] break
exit $value
'
```

## Template: Single Command (Password-Based)

Add `-o PubkeyAuthentication=no` to force password auth.

```bash
expect -c '
set timeout 30
spawn ssh -o PubkeyAuthentication=no -p <PORT> -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 <USER>@<HOST> "<COMMAND>"
expect {
    timeout { puts "ERROR: Connection timed out"; exit 1 }
    "yes/no" { send "yes\r"; exp_continue }
    "assword:" { send "<PASSWORD>\r"; exp_continue }
    "Connection refused" { puts "ERROR: Connection refused"; exit 1 }
    "Permission denied" { puts "ERROR: Permission denied"; exit 1 }
    "No route to host" { puts "ERROR: Host unreachable"; exit 1 }
    eof
}
foreach {pid spawnid os_error_flag value} [wait] break
exit $value
'
```

## Template: Command with sudo

The `-t` flag is **required** for sudo (allocates a PTY).

```bash
expect -c '
set timeout 30
spawn ssh -t -i <KEY> -p <PORT> -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 <USER>@<HOST> "sudo <COMMAND>"
expect {
    timeout { puts "ERROR: Connection timed out"; exit 1 }
    "yes/no" { send "yes\r"; exp_continue }
    "assword" { send "<SUDO_PASSWORD>\r"; exp_continue }
    "Permission denied" { puts "ERROR: Wrong sudo password"; exit 1 }
    eof
}
foreach {pid spawnid os_error_flag value} [wait] break
exit $value
'
```

## Template: Multiple Commands (Interactive Session)

```bash
expect -c '
set timeout 30
spawn ssh -i <KEY> -p <PORT> -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 <USER>@<HOST>
expect {
    timeout { puts "ERROR: Connection timed out"; exit 1 }
    "yes/no" { send "yes\r"; exp_continue }
    "assword:" { send "<PASSWORD>\r"; exp_continue }
    -re {\$ $|# $}
}
send "<COMMAND_1>\r"
expect -re {\$ $|# $}
send "<COMMAND_2>\r"
expect -re {\$ $|# $}
send "exit\r"
expect eof
'
```

## SCP via expect

```bash
# Upload: <LOCAL> <USER>@<HOST>:<REMOTE>
# Download: <USER>@<HOST>:<REMOTE> <LOCAL>
# For password auth: the "assword:" handler covers it
expect -c '
set timeout 120
spawn scp -i <KEY> -P <PORT> -o StrictHostKeyChecking=accept-new <LOCAL> <USER>@<HOST>:<REMOTE>
expect {
    timeout { puts "ERROR: Transfer timed out"; exit 1 }
    "yes/no" { send "yes\r"; exp_continue }
    "assword:" { send "<PASSWORD>\r"; exp_continue }
    "Permission denied" { puts "ERROR: Permission denied"; exit 1 }
    eof
}
foreach {pid spawnid os_error_flag value} [wait] break
exit $value
'
```

## rsync via expect

```bash
expect -c '
set timeout 300
spawn rsync -avz -e "ssh -i <KEY> -p <PORT> -o StrictHostKeyChecking=accept-new" <LOCAL> <USER>@<HOST>:<REMOTE>
expect {
    timeout { puts "ERROR: rsync timed out"; exit 1 }
    "yes/no" { send "yes\r"; exp_continue }
    "assword:" { send "<PASSWORD>\r"; exp_continue }
    "Permission denied" { puts "ERROR: Permission denied"; exit 1 }
    eof
}
foreach {pid spawnid os_error_flag value} [wait] break
exit $value
'
```

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | `ssh-keygen -R [<HOST>]:<PORT>` -- **ask the user first** (could be MITM) |
| `Connection timed out` | Increase ConnectTimeout=30, verify reachability: `nc -z -w5 <HOST> <PORT>` |
| `Permissions too open` | `chmod 600 <KEY_PATH>` |
| `a terminal is required` (sudo) | Add `-t` flag to ssh |
| `Connection refused` after retries | Likely Fail2Ban. **Do NOT retry auth more than 2 times!** Wait or ask the user |
| `expect: command not found` | Install: `sudo apt-get install -y expect` |

## Safety Rules

- **Do NOT delete files** on the server without user confirmation
- **Do NOT touch containers** of other projects without user confirmation
- **Back up before editing configs:** `cp file file.bak`
- **Do NOT retry auth more than 2 times** -- risk of Fail2Ban lockout
