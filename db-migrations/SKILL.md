---
name: db-migrations
description: Database migration skill for Python projects using SQLite or PostgreSQL. Use when adding columns, creating tables, renaming fields, changing schema, or managing migration history. Covers Alembic (SQLAlchemy), raw SQL migrations, rollback strategies, and zero-downtime patterns. Triggers on: "миграция базы данных", "database migration", "добавить колонку", "изменить схему", "alter table", "alembic", "schema change", "migrate db", "накатить миграцию", "откатить миграцию", "rollback migration".
---

# Database Migrations

Безопасные изменения схемы БД для Python-проектов. SQLite и PostgreSQL.

---

## Before You Start

**Всегда делай backup перед миграцией:**

```bash
# SQLite
cp vault.db vault.db.backup.$(date +%Y%m%d_%H%M%S)

# PostgreSQL
docker exec <pg_container> pg_dump -U <user> <db> > backup_$(date +%Y%m%d_%H%M%S).sql
```

Прочитай текущую схему:

```bash
# SQLite — посмотреть все таблицы и колонки
sqlite3 vault.db ".schema"
sqlite3 vault.db "SELECT name, sql FROM sqlite_master WHERE type='table';"

# PostgreSQL
docker exec <pg_container> psql -U <user> <db> -c "\d+"
```

---

## Path A: Alembic (если используется SQLAlchemy)

### Инициализация (один раз)

```bash
pip install alembic -q
alembic init migrations

# В migrations/env.py указать target_metadata:
# from src.models import Base
# target_metadata = Base.metadata
```

### Создание и применение миграции

```bash
# Автогенерация из изменений в моделях
alembic revision --autogenerate -m "add user_preferences column"

# Посмотреть что сгенерировалось
cat migrations/versions/<hash>_add_user_preferences_column.py

# Применить
alembic upgrade head

# Откатить последнюю
alembic downgrade -1

# История
alembic history --verbose

# Текущая версия БД
alembic current
```

### Шаблон миграции

```python
"""add user_preferences column

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users',
        sa.Column('preferences', sa.JSON(), nullable=True)
    )
    # Заполнить дефолтом если нужно
    op.execute("UPDATE users SET preferences = '{}' WHERE preferences IS NULL")

def downgrade():
    op.drop_column('users', 'preferences')
```

---

## Path B: Raw SQL миграции (без ORM)

### Структура файлов

```
migrations/
├── 001_initial_schema.sql
├── 002_add_user_preferences.sql
├── 003_add_heartbeat_index.sql
└── migration_runner.py
```

### migration_runner.py

```python
import sqlite3
import os
import glob

def get_applied_migrations(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    return {row[0] for row in cursor.fetchall()}

def run_migrations(db_path: str, migrations_dir: str = "migrations"):
    conn = sqlite3.connect(db_path)
    applied = get_applied_migrations(conn)

    migration_files = sorted(glob.glob(f"{migrations_dir}/*.sql"))

    for filepath in migration_files:
        version = os.path.basename(filepath)
        if version in applied:
            print(f"  skip: {version}")
            continue

        print(f"  apply: {version}")
        with open(filepath) as f:
            sql = f.read()

        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,)
            )
            conn.commit()
            print(f"  done: {version}")
        except Exception as e:
            conn.rollback()
            print(f"  FAILED: {version}: {e}")
            raise

    conn.close()
    print("All migrations applied.")

if __name__ == "__main__":
    run_migrations("vault.db")
```

### Шаблон SQL миграции

```sql
-- 002_add_user_preferences.sql
-- Description: Add preferences JSON column to users table
-- Rollback: ALTER TABLE users DROP COLUMN preferences (SQLite: rebuild table)

BEGIN;

ALTER TABLE users ADD COLUMN preferences TEXT DEFAULT '{}';

-- Backfill existing rows
UPDATE users SET preferences = '{}' WHERE preferences IS NULL;

COMMIT;
```

---

## SQLite Особенности

SQLite не поддерживает `DROP COLUMN`, `RENAME COLUMN` (до 3.35), `ADD CONSTRAINT` после создания. Для таких изменений — паттерн "rebuild":

```sql
-- Переименование колонки / удаление / изменение типа в SQLite
BEGIN;

-- 1. Создать новую таблицу с нужной схемой
CREATE TABLE users_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    -- новые поля / без старых
    preferences TEXT DEFAULT '{}'
);

-- 2. Скопировать данные
INSERT INTO users_new (id, name, preferences)
SELECT id, name, COALESCE(old_preferences, '{}')
FROM users;

-- 3. Заменить
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

-- 4. Восстановить индексы
CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);

COMMIT;
```

---

## Zero-Downtime Patterns

Для production сервисов, которые нельзя останавливать:

### Добавление колонки — безопасно

```sql
-- Nullable с дефолтом — не блокирует таблицу
ALTER TABLE focus_items ADD COLUMN archived_at TIMESTAMP DEFAULT NULL;
```

### Переименование колонки — expand/contract

```
Шаг 1 (deploy 1): Добавить NEW колонку, писать в обе (old + new)
Шаг 2 (deploy 2): Читать из NEW, писать в обе
Шаг 3 (deploy 3): Убрать OLD колонку
```

### Удаление колонки — сначала убрать из кода

```
Шаг 1: Убрать все обращения к колонке в коде → deploy
Шаг 2: DROP COLUMN → deploy
```

---

## Индексы

```sql
-- Создать индекс без блокировки (PostgreSQL)
CREATE INDEX CONCURRENTLY idx_actions_user_id ON actions(user_id);

-- SQLite — без CONCURRENTLY, но быстро на малых объёмах
CREATE INDEX IF NOT EXISTS idx_actions_user_id ON actions(user_id);

-- Проверить использование индексов
EXPLAIN QUERY PLAN SELECT * FROM actions WHERE user_id = 'usr_abc123';
-- Должно быть "SEARCH actions USING INDEX", не "SCAN"

-- Найти медленные запросы без индексов
sqlite3 vault.db "
  SELECT name FROM sqlite_master WHERE type='index';
"
```

---

## Rollback Plan

Перед каждой миграцией готовь откат:

```bash
# 1. Backup (уже сделан выше)

# 2. Записать текущую версию
alembic current > migration_checkpoint.txt  # если alembic
# или
sqlite3 vault.db "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;"

# 3. Rollback если что-то пошло не так
alembic downgrade -1                    # alembic
sqlite3 vault.db < rollback_002.sql     # raw SQL

# 4. Восстановить из backup в крайнем случае
cp vault.db.backup.20260327_143000 vault.db
```

---

## Checklist перед деплоем миграции

```
□ Backup сделан
□ Миграция протестирована на копии БД
□ Rollback SQL написан и проверен
□ Сервис можно перезапустить без downtime (или запланировано окно)
□ После миграции: проверить SELECT count(*) на ключевых таблицах
□ После миграции: прогнать smoke test
```
