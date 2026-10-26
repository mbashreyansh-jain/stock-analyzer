"""Database connection and a minimal migration runner for db/migrations/*.sql."""

from pathlib import Path

import psycopg

from stockai.config import get_settings


def connect() -> psycopg.Connection:
    return psycopg.connect(get_settings().database_url)


def migrate(conn: psycopg.Connection, migrations_dir: Path | None = None) -> list[str]:
    """Apply every migration file not yet recorded in schema_migrations. Returns the versions applied."""
    migrations_dir = migrations_dir or get_settings().migrations_dir
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    applied = []
    for path in sorted(migrations_dir.glob("*.sql")):
        version = path.stem
        if version in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        applied.append(version)
    conn.commit()
    return applied
