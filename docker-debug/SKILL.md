---
name: docker-debug
description: Docker and docker-compose debugging skill. Use when containers crash, fail to start, consume too much memory, have networking issues, volume problems, or when logs show errors. Covers container inspection, log analysis, network debugging, volume issues, resource limits, and common failure patterns. Triggers on: "контейнер упал", "container crash", "docker не запускается", "не могу подключиться", "container keeps restarting", "OOM killed", "docker network issue", "volume не монтируется", "порт занят", "docker compose up fails", "отладка docker", "docker debug".
---

# Docker Debug

Диагностика и исправление проблем с Docker-контейнерами и docker-compose стеком.

---

## Quick Triage (начни здесь)

```bash
# Общая картина — что запущено, что упало
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Последние события Docker daemon
docker events --since 30m --until now 2>/dev/null | tail -20

# Ресурсы прямо сейчас
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Проблемные контейнеры (не running)
docker ps -a --filter "status=exited" --filter "status=restarting"
```

---

## Step 1: Logs Analysis

```bash
# Последние 100 строк
docker logs <container> --tail 100

# С временными метками
docker logs <container> --timestamps --tail 50

# Следить в реальном времени
docker logs -f <container>

# Только stderr (ошибки)
docker logs <container> 2>&1 | grep -i "error\|fatal\|exception\|traceback" | tail -30

# Логи за последние N минут
docker logs <container> --since 10m

# Если контейнер уже удалён — логи в journald
journalctl -u docker.service --since "30 min ago" | grep <container_name>
```

### Паттерны ошибок

```bash
# Python traceback
docker logs <container> 2>&1 | grep -A 10 "Traceback"

# OOM Kill (убит ядром из-за памяти)
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
# Полная конфигурация контейнера
docker inspect <container>

# Конкретные поля
docker inspect <container> --format '{{.State.Status}}'
docker inspect <container> --format '{{.State.ExitCode}}'
docker inspect <container> --format '{{.State.Error}}'
docker inspect <container> --format '{{.HostConfig.RestartPolicy}}'

# Переменные окружения (без секретов в логах!)
docker inspect <container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -v "PASSWORD\|TOKEN\|SECRET\|KEY"

# Смонтированные тома
docker inspect <container> --format '{{range .Mounts}}{{.Source}} → {{.Destination}} ({{.Mode}}){{println}}{{end}}'

# Сетевые настройки
docker inspect <container> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}: {{$v.IPAddress}}{{println}}{{end}}'
```

---

## Step 3: Shell в контейнер

```bash
# Запущенный контейнер
docker exec -it <container> bash
docker exec -it <container> sh  # если нет bash

# Упавший контейнер — запустить с override entrypoint
docker run -it --entrypoint sh <image>

# Запустить с теми же переменными что в compose
docker compose run --rm <service> bash

# Запустить с root правами
docker exec -it -u root <container> bash
```

### Внутри контейнера — что проверять

```bash
# Процессы
ps aux

# Открытые порты
ss -tlnp  # или netstat -tlnp

# Дисковое место
df -h

# Файлы в рабочей директории
ls -la /app  # или где лежит код

# Права на файлы
stat /app/vault.db
ls -la /app/data/

# Переменные окружения
env | grep -v "PASSWORD\|TOKEN\|SECRET"

# Можно ли достучаться до других сервисов
curl -s http://nginx:80/health || wget -q -O- http://nginx:80/health
ping -c 2 <service_name>
```

---

## Step 4: Networking Issues

```bash
# Список сетей
docker network ls

# Инспекция сети — кто в ней
docker network inspect <network_name>

# Проверить что контейнеры в одной сети
docker inspect <container1> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'
docker inspect <container2> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'

# DNS resolution внутри контейнера
docker exec <container> nslookup <service_name>
docker exec <container> cat /etc/hosts
docker exec <container> cat /etc/resolv.conf

# Порты на хосте
ss -tlnp | grep <port>
sudo lsof -i :<port>

# Занят ли порт другим контейнером
docker ps --format '{{.Names}}\t{{.Ports}}' | grep <port>
```

### Типичные сетевые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| `Connection refused` | Сервис не слушает или не запустился | Проверь логи, убедись что сервис стартовал |
| `Name or service not known` | Контейнер не в той же сети | Добавить в одну network в compose |
| `Address already in use` | Порт занят на хосте | `ss -tlnp \| grep <port>`, убить процесс |
| `Connection timeout` | Firewall / UFW блокирует | `ufw status`, проверь правила |

---

## Step 5: Volume Issues

```bash
# Список томов
docker volume ls

# Инспекция тома
docker volume inspect <volume_name>

# Где физически лежат данные volume
docker volume inspect <volume_name> --format '{{.Mountpoint}}'

# Проверить что в volume
docker run --rm -v <volume_name>:/data alpine ls -la /data

# Права на bind mount
ls -la /home/anton/docker/<service>/data/

# Частая проблема: файл создан как директория (или наоборот)
# Если volume mount создаёт директорию вместо файла:
file /home/anton/docker/vectoros/vault.db

# Починить: удалить директорию, создать файл
rm -rf /home/anton/docker/vectoros/vault.db
touch /home/anton/docker/vectoros/vault.db
```

---

## Step 6: Resource Problems

```bash
# OOM — контейнер убит из-за памяти
docker inspect <container> --format '{{.State.OOMKilled}}'

# Лимиты памяти
docker inspect <container> --format '{{.HostConfig.Memory}}'  # 0 = без лимита

# Установить лимит в compose:
# deploy:
#   resources:
#     limits:
#       memory: 512M

# Disk space проблемы
df -h /var/lib/docker
docker system df  # сколько места занимают images/containers/volumes

# Очистить неиспользуемое (осторожно!)
docker system prune -f          # containers + networks + dangling images
docker volume prune -f          # ТОЛЬКО неиспользуемые volumes
docker image prune -a -f        # все неиспользуемые images
```

---

## Step 7: Docker Compose Specific

```bash
# Посмотреть итоговый compose config (с учётом .env)
docker compose config

# Validate compose file
docker compose config --quiet && echo "OK"

# Пересоздать только один сервис
docker compose up -d --force-recreate <service>

# Rebuild image и рестарт
docker compose up -d --build <service>

# Посмотреть зависимости сервисов
docker compose config --services

# Запустить с verbose output
docker compose --verbose up

# Проверить .env загрузился правильно
docker compose run --rm <service> env | grep MY_VAR
```

### Типичные проблемы compose

```bash
# "Service X depends on Y which has failed"
docker compose logs <failing_service>  # смотреть логи зависимости

# Изменился .env но контейнер не подхватил
docker compose down && docker compose up -d

# "network not found" после docker system prune
docker compose down && docker compose up -d  # пересоздаст сети

# Порядок запуска (depends_on не гарантирует готовность сервиса)
# Добавить healthcheck в compose:
# healthcheck:
#   test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
#   interval: 10s
#   retries: 3
```

---

## Step 8: Rebuilding from Scratch

Когда ничего не помогает:

```bash
# 1. Сохранить данные
docker exec <container> cp /app/vault.db /tmp/vault.db.backup
docker cp <container>:/tmp/vault.db.backup ./vault.db.backup

# 2. Полная остановка
cd ~/docker && docker compose down -v  # -v удаляет volumes! только если уверен
# или без удаления volumes:
docker compose down

# 3. Очистить образы сервиса
docker compose build --no-cache <service>

# 4. Поднять заново
docker compose up -d

# 5. Проверить логи сразу
docker compose logs -f --tail 50
```

---

## Cheatsheet: Exit Codes

| Exit Code | Значение | Что делать |
|-----------|----------|------------|
| 0 | Штатное завершение | Норма для одноразовых контейнеров |
| 1 | Ошибка приложения | Смотреть логи, Python traceback |
| 137 | OOM Kill (128+9) | Увеличить memory limit или оптимизировать |
| 139 | Segfault (128+11) | Баг в native библиотеке |
| 143 | SIGTERM (128+15) | Штатная остановка (docker stop) |
| 125 | Docker daemon error | Проверить docker inspect, права |
| 126 | Entrypoint не исполняемый | chmod +x или исправить entrypoint |
| 127 | Entrypoint не найден | Проверить путь в CMD/ENTRYPOINT |
