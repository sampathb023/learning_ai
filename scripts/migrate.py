import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from app.core.config import get_settings


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
UP_MARKER = "-- migrate:up"
DOWN_MARKER = "-- migrate:down"


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    up_sql: str
    down_sql: str


def database_dsn() -> str:
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def split_sql_sections(sql: str) -> tuple[str, str]:
    if UP_MARKER not in sql:
        return sql.strip(), ""

    _, after_up = sql.split(UP_MARKER, 1)
    if DOWN_MARKER in after_up:
        up_sql, down_sql = after_up.split(DOWN_MARKER, 1)
    else:
        up_sql, down_sql = after_up, ""
    return up_sql.strip(), down_sql.strip()


def load_migrations() -> list[Migration]:
    migrations = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        up_sql, down_sql = split_sql_sections(path.read_text(encoding="utf-8"))
        migrations.append(
            Migration(
                version=path.stem,
                path=path,
                up_sql=up_sql,
                down_sql=down_sql,
            )
        )
    return migrations


async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(database_dsn())


async def ensure_schema_migrations(connection: asyncpg.Connection) -> None:
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version text PRIMARY KEY,
            applied_at timestamptz NOT NULL
        )
        """
    )


async def applied_versions(connection: asyncpg.Connection) -> set[str]:
    rows = await connection.fetch("SELECT version FROM schema_migrations ORDER BY version")
    return {row["version"] for row in rows}


async def upgrade() -> None:
    migrations = load_migrations()
    connection = await connect()
    try:
        await ensure_schema_migrations(connection)
        applied = await applied_versions(connection)
        pending = [migration for migration in migrations if migration.version not in applied]

        if not pending:
            print("No pending migrations.")
            return

        for migration in pending:
            async with connection.transaction():
                print(f"Applying {migration.version} from {migration.path.name}")
                if migration.up_sql:
                    await connection.execute(migration.up_sql)
                await connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES ($1, $2)",
                    migration.version,
                    datetime.now(UTC),
                )
        print(f"Applied {len(pending)} migration(s).")
    finally:
        await connection.close()


async def rollback() -> None:
    migrations = {migration.version: migration for migration in load_migrations()}
    connection = await connect()
    try:
        await ensure_schema_migrations(connection)
        row = await connection.fetchrow(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        )
        if not row:
            print("No migrations have been applied.")
            return

        migration = migrations[row["version"]]
        if not migration.down_sql:
            raise RuntimeError(f"Migration {migration.version} does not have a down section.")

        async with connection.transaction():
            print(f"Rolling back {migration.version} from {migration.path.name}")
            await connection.execute(migration.down_sql)
            await connection.execute(
                "DELETE FROM schema_migrations WHERE version = $1",
                migration.version,
            )
        print("Rolled back 1 migration.")
    finally:
        await connection.close()


async def stamp() -> None:
    migrations = load_migrations()
    connection = await connect()
    try:
        await ensure_schema_migrations(connection)
        applied = await applied_versions(connection)
        missing = [migration for migration in migrations if migration.version not in applied]

        if not missing:
            print("All migrations are already stamped.")
            return

        async with connection.transaction():
            for migration in missing:
                await connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES ($1, $2)",
                    migration.version,
                    datetime.now(UTC),
                )
        print(f"Stamped {len(missing)} migration(s) without running SQL.")
    finally:
        await connection.close()


async def status() -> None:
    migrations = load_migrations()
    connection = await connect()
    try:
        await ensure_schema_migrations(connection)
        applied = await applied_versions(connection)
        for migration in migrations:
            state = "applied" if migration.version in applied else "pending"
            print(f"{state:8} {migration.version}")
    finally:
        await connection.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Apply plain SQL database migrations.")
    parser.add_argument("command", choices=["upgrade", "rollback", "stamp", "status"])
    args = parser.parse_args()

    if args.command == "upgrade":
        await upgrade()
    elif args.command == "rollback":
        await rollback()
    elif args.command == "stamp":
        await stamp()
    elif args.command == "status":
        await status()


if __name__ == "__main__":
    asyncio.run(main())
