# Transaction Agent API

A focused FastAPI + Postgres project for one use case:

> Ask a natural-language question like "Give me the transactions failed in the last 2 days" and return matching transaction rows from Postgres.

## How It Works

```text
User question
  -> FastAPI endpoint
  -> planner agent parses filters
  -> data-helper agent queries Postgres
  -> tool calls and task output are stored
```

The project intentionally keeps only the transaction-query path.

## Stack

- FastAPI
- Postgres
- SQLAlchemy async engine
- asyncpg
- Plain SQL migrations
- Docker Compose

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d postgres
python scripts/migrate.py upgrade
python scripts/seed.py
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

## Main Endpoints

- `GET /` - simple transaction chat page
- `GET /health` - database health check
- `GET /transactions` - list seeded transactions
- `POST /agent-runs` - ask a natural-language transaction question
- `GET /tasks` - inspect previous questions and answers
- `GET /tool-calls` - inspect the parser/query tool trace
- `GET /tools` - list the transaction tools

## Example

```bash
curl -X POST http://127.0.0.1:8000/agent-runs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Failed transactions",
    "input": "Give me the transactions failed in the last 2 days"
  }'
```

The planner turns the question into:

```json
{"status": "error", "days": 2}
```

The data-helper then calls `search_transactions` and returns matching rows from Postgres.

## Schema Versioning

This project uses plain SQL files in `migrations/` for database versioning.
Applied versions are tracked in the database table `schema_migrations`.

When you add or change tables:

1. Edit the SQLAlchemy models in `app/models.py`.
2. Add a new SQL file in `migrations/` with the next version prefix:

   ```bash
   touch migrations/002_describe_schema_change.sql
   ```

3. Write the forward and rollback SQL:

   ```sql
   -- migrate:up

   ALTER TABLE transactions ADD COLUMN merchant_name text;

   -- migrate:down

   ALTER TABLE transactions DROP COLUMN merchant_name;
   ```

4. Apply it:

   ```bash
   python scripts/migrate.py upgrade
   ```

5. Update `scripts/seed.py` only if you need new sample data.

To inspect migration state:

```bash
python scripts/migrate.py status
```

If the tables already exist and match `migrations/001_initial_schema.sql`, mark
the current schema as versioned without running the SQL:

```bash
python scripts/migrate.py stamp
```

For a brand-new database, use `python scripts/migrate.py upgrade` instead.

To roll back the most recent migration:

```bash
python scripts/migrate.py rollback
```
