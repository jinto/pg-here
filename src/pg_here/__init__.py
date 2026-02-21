"""pg-here: Run a local PostgreSQL instance in your project folder."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("pg-here")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"


@dataclass
class PgHereHandle:
    """Handle for a running pg-here PostgreSQL instance."""

    install_dir: Path
    data_dir: Path
    port: int
    username: str
    password: str = field(repr=False)
    database: str
    version: str
    connection_string: str = field(repr=False)

    def stop(self) -> None:
        """Stop the PostgreSQL instance."""
        from pg_here import instance

        instance.stop(self.install_dir, self.data_dir)

    def ensure_database(self, name: str) -> bool:
        """Create a database if it doesn't exist. Returns True if created."""
        from pg_here import database

        return database.ensure_database("localhost", self.port, self.username, name)

    def connection_string_for(self, db: str) -> str:
        """Build a connection string for the given database name."""
        from pg_here import database

        return database.connection_string(
            "localhost", self.port, self.username, self.password, db
        )


def start_pg_here(
    project_dir: Path | None = None,
    username: str = "postgres",
    password: str = "postgres",
    port: int = 55432,
    database: str = "postgres",
    pg_version: str | None = None,
) -> PgHereHandle:
    """Start a local PostgreSQL instance and return a handle.

    Does not register signal handlers — the caller is responsible
    for calling handle.stop() when done.

    The *password* parameter is used only in the connection string.
    The server uses trust authentication for local connections.
    """
    from pg_here import binary
    from pg_here import database as database_mod
    from pg_here import instance

    if project_dir is None:
        project_dir = Path.cwd()

    ver = binary.resolve_version(project_dir, pg_version)
    install_dir = binary.download_and_extract(project_dir, ver)
    data_dir = instance.get_data_dir(project_dir)

    instance.check_version_compat(data_dir, ver)

    if instance.is_running(install_dir, data_dir):
        raise RuntimeError(
            "PostgreSQL is already running on this data directory. "
            "Stop the existing instance first, or use a different project directory."
        )

    instance.init_cluster(install_dir, data_dir, username)
    instance.write_pg_conf(data_dir, {
        "listen_addresses": "'localhost'",
        "shared_preload_libraries": "'pg_stat_statements'",
    })
    instance.start(install_dir, data_dir, port)

    try:
        if database != "postgres":
            database_mod.ensure_database("localhost", port, username, database)
        database_mod.ensure_pg_stat_statements("localhost", port, username, database)
    except Exception:
        try:
            instance.stop(install_dir, data_dir)
        except Exception:
            pass
        raise

    conn_str = database_mod.connection_string("localhost", port, username, password, database)

    return PgHereHandle(
        install_dir=install_dir,
        data_dir=data_dir,
        port=port,
        username=username,
        password=password,
        database=database,
        version=ver,
        connection_string=conn_str,
    )


def stop_pg_here(handle: PgHereHandle) -> None:
    """Stop a pg-here PostgreSQL instance."""
    handle.stop()
