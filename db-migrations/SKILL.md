---
name: db-migrations
description: "Database migration skill for Python projects using SQLite or PostgreSQL. Use when adding columns, creating tables, renaming fields, changing schema, or managing migration history. Covers Alembic (SQLAlchemy), raw SQL migrations, rollback strategies, and zero-downtime patterns. Triggers on: database migration, add column, alter table, schema change, alembic, migrate db, rollback migration, change database schema, rename column, create table."
---

# Database Migrations

Safe schema changes for Python projects. SQLite and PostgreSQL.

---

## Before You Start

**Always back up before migrating:**

```bash
# SQLite
cp database.db database.db.backup.$(date +%Y%m%d_%H%M%S)

# PostgreSQL
docker exec <pg_container> pg_dump -U <user> <db> > backup_$(date +%Y%m%d_%H%M%S).sql
```

Read the current schema:

```bash
# SQLite — list all tables and columns
sqlite3 database.db ".schema"
sqlite3 database.db "SELECT name, sql FROM sqlite_master WHERE type='table';"

# PostgreSQL
docker exec <pg_container> psql -U <user> <db> -c "\d+"
```

Check the database size and row counts for key tables — this affects migration strategy:

```bash
# SQLite — file size and row counts
ls -lh database.db
sqlite3 database.db "SELECT name, (SELECT count(*) FROM pragma_table_info(name)) as cols FROM sqlite_master WHERE type='table';"

# PostgreSQL
docker exec <pg_container> psql -U <user> <db> -c "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
```

---

## Path A: Alembic (when using SQLAlchemy)

### Initialization (one time)

```bash
pip install alembic -q
alembic init migrations

# In migrations/env.py set target_metadata:
# from src.models import Base
# target_metadata = Base.metadata
```

### Creating and applying a migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "add user_preferences column"

# Review what was generated (always review before applying!)
cat migrations/versions/<hash>_add_user_preferences_column.py

# Apply
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# History
alembic history --verbose

# Current DB version
alembic current
```

### Migration template

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
    # Backfill default if needed
    op.execute("UPDATE users SET preferences = '{}' WHERE preferences IS NULL")

def downgrade():
    op.drop_column('users', 'preferences')
```

---

## Path B: Raw SQL Migrations (without ORM)

### File structure

```
migrations/
  001_initial_schema.sql
  002_add_user_preferences.sql
  003_add_heartbeat_index.sql
  migration_runner.py
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
    conn.commit()
    cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    return {row[0] for row in cursor.fetchall()}

def run_migrations(db_path: str, migrations_dir: str = "migrations"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")  # safer for concurrent access
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
            # Use execute() with manual transaction control, not executescript()
            # executescript() issues implicit COMMIT which breaks atomicity
            conn.execute("BEGIN")
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)
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
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "database.db"
    run_migrations(db)
```

### SQL migration template

```sql
-- 002_add_user_preferences.sql
-- Description: Add preferences JSON column to users table
-- Rollback: ALTER TABLE users DROP COLUMN preferences (SQLite < 3.35: rebuild table)

ALTER TABLE users ADD COLUMN preferences TEXT DEFAULT '{}';

-- Backfill existing rows
UPDATE users SET preferences = '{}' WHERE preferences IS NULL;
```

**Note:** Do NOT wrap raw SQL migration files in BEGIN/COMMIT — the runner handles transactions.

---

## SQLite Specifics

SQLite does not support `DROP COLUMN` (before 3.35), `RENAME COLUMN` (before 3.25), or `ADD CONSTRAINT` after creation. For these changes use the "rebuild" pattern:

```sql
-- Renaming / dropping / changing column type in SQLite
-- Note: the runner wraps this in a transaction

-- 1. Create new table with the desired schema
CREATE TABLE users_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    preferences TEXT DEFAULT '{}'
);

-- 2. Copy data
INSERT INTO users_new (id, name, preferences)
SELECT id, name, COALESCE(old_preferences, '{}')
FROM users;

-- 3. Replace
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

-- 4. Recreate indexes
CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
```

**SQLite WAL mode:** If the database is accessed concurrently (e.g., by a running bot), enable WAL mode to prevent locking conflicts:

```bash
sqlite3 database.db "PRAGMA journal_mode=WAL;"
```

---

## Data Migrations

When the migration involves transforming data (not just schema), follow these steps:

1. **Add new column/table** (schema migration)
2. **Backfill data** in the same migration or a separate one
3. **Verify data** — run a count/sample check
4. **Drop old column** only after confirming the backfill is correct

```python
# Example: splitting a full_name column into first_name + last_name
def upgrade():
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))

    # Backfill
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE users
        SET first_name = substr(full_name, 1, instr(full_name, ' ') - 1),
            last_name = substr(full_name, instr(full_name, ' ') + 1)
        WHERE full_name IS NOT NULL
    """))

    # Do NOT drop full_name here — do it in a follow-up migration after verification
```

---

## Zero-Downtime Patterns

For production services that cannot be stopped:

### Adding a column — safe

```sql
-- Nullable with default — does not lock the table
ALTER TABLE focus_items ADD COLUMN archived_at TIMESTAMP DEFAULT NULL;
```

### Renaming a column — expand/contract

```
Step 1 (deploy 1): Add NEW column, write to both (old + new)
Step 2 (deploy 2): Read from NEW, write to both
Step 3 (deploy 3): Remove OLD column
```

### Removing a column — code first, then schema

```
Step 1: Remove all references to the column in code -> deploy
Step 2: DROP COLUMN -> deploy
```

### Adding a NOT NULL constraint — backfill first

```
Step 1: Add column as nullable -> deploy
Step 2: Backfill all rows with valid values -> verify
Step 3: Add NOT NULL constraint -> deploy
```

---

## Indexes

```sql
-- Create index without locking (PostgreSQL)
CREATE INDEX CONCURRENTLY idx_actions_user_id ON actions(user_id);

-- SQLite — no CONCURRENTLY, but fast for small tables
CREATE INDEX IF NOT EXISTS idx_actions_user_id ON actions(user_id);

-- Verify index usage
EXPLAIN QUERY PLAN SELECT * FROM actions WHERE user_id = 'usr_abc123';
-- Should say "SEARCH ... USING INDEX", not "SCAN"

-- List existing indexes
sqlite3 database.db "SELECT name, tbl_name FROM sqlite_master WHERE type='index';"
-- PostgreSQL:
-- \di+ in psql
```

**When to add an index:**
- Column appears in WHERE, JOIN, or ORDER BY clauses frequently
- Table has > 1000 rows
- EXPLAIN QUERY PLAN shows "SCAN TABLE" (full table scan)

**When NOT to add an index:**
- Table has < 100 rows (scan is faster)
- Column has very low cardinality (e.g., boolean)
- Write-heavy table where index maintenance cost exceeds read benefit

---

## Rollback Plan

Before every migration, prepare a rollback:

```bash
# 1. Backup (already done above)

# 2. Record current version
alembic current > migration_checkpoint.txt  # if alembic
# or
sqlite3 database.db "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;"

# 3. Rollback if something goes wrong
alembic downgrade -1                      # alembic
sqlite3 database.db < rollback_002.sql    # raw SQL

# 4. Restore from backup as last resort
cp database.db.backup.20260327_143000 database.db
```

---

## Pre-Deploy Migration Checklist

```
[ ] Backup created and verified (can you restore from it?)
[ ] Migration tested on a copy of the database
[ ] Rollback SQL written and tested
[ ] Service can be restarted without downtime (or maintenance window scheduled)
[ ] Large tables: estimated lock time checked (ALTER on 1M+ rows can be slow)
[ ] Data migration verified: SELECT count(*) on key tables before and after
[ ] Smoke test passes after migration
[ ] Migration is idempotent (running it twice does not fail or corrupt data)
[ ] No secrets or PII in migration files
```
