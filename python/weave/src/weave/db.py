from pathlib import Path

import asyncpg

from weave.config import settings

_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )


async def _migration_applied(conn: asyncpg.Connection, version: str) -> bool:
    return bool(
        await conn.fetchval(
            "SELECT 1 FROM schema_migrations WHERE version = $1",
            version,
        )
    )


async def _bootstrap_existing_schema(conn: asyncpg.Connection, version: str) -> bool:
    """Mark migration applied when DB was created before schema_migrations existed."""
    if version != "001_init.sql":
        return False
    has_campaigns = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'campaigns'
        )
        """
    )
    if not has_campaigns:
        return False
    await conn.execute(
        "INSERT INTO schema_migrations (version) VALUES ($1) ON CONFLICT DO NOTHING",
        version,
    )
    return True


async def migrate(pool: asyncpg.Pool) -> None:
    migrations_dir = settings.migrations_dir
    if not migrations_dir.is_dir():
        raise FileNotFoundError(f"migrations not found: {migrations_dir}")

    async with pool.acquire() as conn:
        await conn.execute(_SCHEMA_MIGRATIONS)
        for path in sorted(migrations_dir.glob("*.sql")):
            version = path.name
            if await _migration_applied(conn, version):
                continue
            if await _bootstrap_existing_schema(conn, version):
                continue
            sql = path.read_text()
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    version,
                )
