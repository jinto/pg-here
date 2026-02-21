"""Integration tests — starts a real PostgreSQL instance."""

from __future__ import annotations

import shutil
import socket
from pathlib import Path

import psycopg
import pytest

from pg_here import PgHereHandle, start_pg_here


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _safe_cleanup(project_dir: Path) -> None:
    """Stop any running instance, then delete data_dir for a clean slate."""
    data_dir = project_dir / "pg_local" / "data"
    if not data_dir.exists():
        return

    from pg_here import instance

    bin_dir = project_dir / "pg_local" / "bin"
    if bin_dir.is_dir():
        for version_dir in bin_dir.iterdir():
            if not version_dir.is_dir() or version_dir.name.startswith("."):
                continue
            try:
                if instance.is_running(version_dir, data_dir):
                    instance.stop(version_dir, data_dir)
            except Exception:
                pass

    shutil.rmtree(data_dir, ignore_errors=True)


def _is_port_conflict(exc: RuntimeError) -> bool:
    msg = str(exc).lower()
    return "address already in use" in msg or "could not bind" in msg


def _start_with_retry(project_dir: Path, max_attempts: int = 3) -> PgHereHandle:
    """Start pg-here with narrow port-conflict retry."""
    last_error: RuntimeError | None = None
    for _ in range(max_attempts):
        port = _find_free_port()
        try:
            return start_pg_here(project_dir=project_dir, port=port)
        except RuntimeError as exc:
            if not _is_port_conflict(exc):
                raise
            last_error = exc
            _safe_cleanup(project_dir)
    assert last_error is not None  # max_attempts >= 1 guarantees assignment
    raise last_error


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_dir(tmp_path_factory):
    """Per-session unique project dir. Binary downloaded once per session."""
    return tmp_path_factory.mktemp("pg_here")


@pytest.fixture
def pg(project_dir):
    """Function-scoped: fresh data_dir + dynamic port for each test."""
    _safe_cleanup(project_dir)
    handle = _start_with_retry(project_dir)
    yield handle
    handle.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_start_and_stop(pg):
    """Start PostgreSQL, verify handle attributes and live connection."""
    assert pg.port > 0
    assert pg.username == "postgres"
    assert pg.data_dir.is_dir()
    assert pg.install_dir.is_dir()
    assert "postgresql://" in pg.connection_string

    with psycopg.connect(pg.connection_string) as conn:
        row = conn.execute("SELECT 1 AS n").fetchone()
        assert row is not None
        assert row[0] == 1


def test_ensure_database(pg):
    """ensure_database() creates a new database and it's connectable."""
    created = pg.ensure_database("testdb")
    assert created is True

    conn_str = pg.connection_string_for("testdb")
    with psycopg.connect(conn_str) as conn:
        row = conn.execute("SELECT current_database()").fetchone()
        assert row is not None
        assert row[0] == "testdb"


def test_connection_string_for(pg):
    """connection_string_for() returns a valid URI."""
    uri = pg.connection_string_for("other")
    assert uri.startswith("postgresql://")
    assert "other" in uri
    assert str(pg.port) in uri


def test_already_running(pg, project_dir):
    """A second start on the same project_dir raises RuntimeError."""
    with pytest.raises(RuntimeError, match="already running"):
        start_pg_here(project_dir=project_dir, port=_find_free_port())


def test_pg_stat_statements(pg):
    """pg_stat_statements extension is loaded."""
    with psycopg.connect(pg.connection_string) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'"
        ).fetchone()
        assert row is not None
