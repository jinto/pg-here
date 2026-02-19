"""Database creation and extension management."""

from __future__ import annotations

import logging
from urllib.parse import quote

import psycopg
from psycopg import sql

_log = logging.getLogger(__name__)


def connection_string(
    host: str, port: int, username: str, password: str, database: str
) -> str:
    """Build a PostgreSQL connection URI with properly escaped components."""
    return (
        f"postgresql://{quote(username, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{quote(database, safe='')}"
    )


def ensure_database(
    host: str, port: int, username: str, database: str
) -> bool:
    """Create database if it doesn't exist. Returns True if created."""
    if database == "postgres":
        return False

    with psycopg.connect(
        host=host, port=port, user=username, dbname="postgres", autocommit=True
    ) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database,)
        ).fetchone()
        if row is not None:
            _log.debug("Database %r already exists", database)
            return False

        try:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        except psycopg.errors.DuplicateDatabase:
            _log.debug("Database %r created concurrently", database)
            return False
        _log.info("Created database %r", database)
        return True


def ensure_extension(
    host: str, port: int, username: str, database: str, extension: str
) -> None:
    """Install a PostgreSQL extension in the given database."""
    with psycopg.connect(
        host=host, port=port, user=username, dbname=database, autocommit=True
    ) as conn:
        try:
            conn.execute(
                sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(
                    sql.Identifier(extension)
                )
            )
        except psycopg.Error as exc:
            raise RuntimeError(
                f"Failed to create extension {extension!r}: {exc}. "
                f"If this is a preload extension, ensure shared_preload_libraries "
                f"includes '{extension}' in postgresql.conf and restart PostgreSQL."
            ) from exc
        _log.info("Extension %r ensured in database %r", extension, database)


def ensure_pg_stat_statements(
    host: str, port: int, username: str, database: str
) -> None:
    """Install pg_stat_statements extension."""
    ensure_extension(host, port, username, database, "pg_stat_statements")
