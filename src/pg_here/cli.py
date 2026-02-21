"""Click CLI — orchestrates binary, instance, and database modules."""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

import click

from pg_here import binary, database, instance, platform_compat

_log = logging.getLogger(__name__)


def _progress_callback(downloaded: int, total: int | None) -> None:
    mb = downloaded / 1_048_576
    if total:
        pct = downloaded * 100 // total
        total_mb = total / 1_048_576
        click.echo(f"\rDownloading PostgreSQL... {mb:.1f}/{total_mb:.1f} MB ({pct}%)", nl=False)
    else:
        click.echo(f"\rDownloading PostgreSQL... {mb:.1f} MB", nl=False)


def _check_version_compat(data_dir: Path, version: str) -> None:
    """Check that data directory is compatible with the binary version."""
    pg_version_file = data_dir / "PG_VERSION"
    if not pg_version_file.is_file():
        return
    data_major = pg_version_file.read_text().strip()
    binary_major = version.split(".")[0]
    if data_major != binary_major:
        click.echo(
            f"Error: pg_local/data/ was initialized with PostgreSQL {data_major}, "
            f"but binary is version {binary_major}.\n"
            f"Delete pg_local/data/ to reinitialize, "
            f"or use --pg-version matching major version {data_major}.",
            err=True,
        )
        sys.exit(1)


@click.command()
@click.option("--username", "-u", default="postgres", help="PostgreSQL superuser name.")
@click.option(
    "--password",
    default="postgres",
    envvar="PGPASSWORD",
    help="Password for connection string (server uses trust auth).",
)
@click.option("--port", default=55432, type=int, help="PostgreSQL port.")
@click.option("--database", "-d", "dbname", default="postgres", help="Database name.")
@click.option("--pg-version", default=None, help="PostgreSQL version (e.g. 17.4.0).")
def main(
    username: str,
    password: str,
    port: int,
    dbname: str,
    pg_version: str | None,
) -> None:
    """Run a local PostgreSQL instance in your project folder."""
    project_dir = Path.cwd()
    install_dir: Path | None = None

    try:
        # 1. Resolve version
        version = binary.resolve_version(project_dir, pg_version)

        # 2. Download binary
        needs_download = not binary.is_installed(project_dir, version)
        if needs_download:
            click.echo(f"Downloading PostgreSQL {version}...")
        install_dir = binary.download_and_extract(
            project_dir, version, on_progress=_progress_callback
        )
        if not binary.is_installed(project_dir, version):
            raise RuntimeError("Binary extraction failed")
        if needs_download:
            click.echo("\r" + " " * 60 + "\r", nl=False)

        # 3. Version compatibility check
        data_dir = instance.get_data_dir(project_dir)
        _check_version_compat(data_dir, version)

        # 4. Initialize cluster
        is_new = instance.init_cluster(install_dir, data_dir, username)

        # 5. Write postgresql.conf
        instance.write_pg_conf(data_dir, {
            "listen_addresses": "'localhost'",
            "shared_preload_libraries": "'pg_stat_statements'",
        })

        # 6. Start PostgreSQL
        if instance.is_running(install_dir, data_dir):
            click.echo(
                "Error: PostgreSQL is already running on this data directory.\n"
                "Stop the existing instance first, or use a different project directory.",
                err=True,
            )
            sys.exit(1)
        instance.start(install_dir, data_dir, port)

        # 7. Create database
        if dbname != "postgres":
            database.ensure_database("localhost", port, username, dbname)

        # 8. Install pg_stat_statements
        database.ensure_pg_stat_statements("localhost", port, username, dbname)

        # 9. Print startup info
        conn_str = database.connection_string("localhost", port, username, password, dbname)
        if is_new:
            click.echo(f"Launching PostgreSQL {version} into new pg_local/")
        else:
            click.echo("Reusing existing pg_local/data/")

        click.echo(f"\nPostgreSQL {version} running on port {port}\n")
        click.echo(f"  psql {conn_str}\n")
        click.echo("Press Ctrl+C to stop.")

        # 10. Register shutdown and wait
        stopping = threading.Event()

        def on_stop() -> None:
            instance.stop(install_dir, data_dir)
            stopping.set()

        unregister = instance.register_shutdown(on_stop)
        try:
            stopping.wait()
        finally:
            unregister()

    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        if install_dir is not None:
            try:
                data_dir = instance.get_data_dir(project_dir)
                instance.stop(install_dir, data_dir)
            except Exception:
                pass
    except Exception as exc:
        error_msg = str(exc)
        click.echo(f"\nError: {error_msg}", err=True)

        # Linux-specific diagnostics
        if platform_compat.is_linux():
            missing = platform_compat.detect_missing_libs(error_msg)
            if missing:
                click.echo(f"\n{platform_compat.format_linux_help(missing)}", err=True)

        # Suggest checking logs
        data_dir = instance.get_data_dir(project_dir)
        log_file = data_dir / "pg.log"
        if log_file.is_file():
            click.echo(f"\nCheck logs: {log_file}", err=True)

        sys.exit(1)
