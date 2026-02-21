"""PostgreSQL instance lifecycle management (initdb, pg_ctl)."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import Callable

_log = logging.getLogger(__name__)
_CONF_MARKER = "# --- pg-here managed settings ---"
_CONF_END = "# --- end pg-here ---"


def get_data_dir(project_dir: Path) -> Path:
    return project_dir / "pg_local" / "data"


def check_version_compat(data_dir: Path, version: str) -> None:
    """Raise RuntimeError if existing data directory is incompatible with binary version."""
    pg_version_file = data_dir / "PG_VERSION"
    if not pg_version_file.is_file():
        return
    data_major = pg_version_file.read_text().strip()
    binary_major = version.split(".")[0]
    if data_major != binary_major:
        raise RuntimeError(
            f"pg_local/data/ was initialized with PostgreSQL {data_major}, "
            f"but binary is version {binary_major}. "
            f"Delete pg_local/data/ to reinitialize, "
            f"or use a version matching major version {data_major}."
        )


def _find_binary(install_dir: Path, name: str) -> Path:
    binary = install_dir / "bin" / name
    if not binary.is_file():
        raise FileNotFoundError(f"PostgreSQL binary not found: {binary}")
    return binary


def _make_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    return {**os.environ, **(extra or {})}


def _run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True, env=_make_env(env))
    if check and result.returncode != 0:
        raise RuntimeError(
            f"{Path(cmd[0]).name} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result


def init_cluster(
    install_dir: Path,
    data_dir: Path,
    username: str,
    env: dict[str, str] | None = None,
) -> bool:
    """Initialize a PostgreSQL data cluster. Returns False if already initialized."""
    if (data_dir / "PG_VERSION").is_file():
        _log.debug("Data directory already initialized: %s", data_dir)
        return False

    data_dir.mkdir(parents=True, exist_ok=True)
    initdb = _find_binary(install_dir, "initdb")

    _run(
        [
            str(initdb),
            f"--pgdata={data_dir}",
            f"--username={username}",
            "--auth=trust",
            "--encoding=UTF-8",
            "--locale=C",
            "--no-instructions",
        ],
        env=env,
    )
    _log.info("Initialized data cluster at %s", data_dir)
    return True


def write_pg_conf(data_dir: Path, settings: dict[str, str]) -> None:
    """Write pg-here managed settings to postgresql.conf (idempotent)."""
    conf_path = data_dir / "postgresql.conf"
    content = conf_path.read_text()

    setting_lines = [f"{key} = {value}" for key, value in settings.items()]
    new_block = "\n".join([_CONF_MARKER, *setting_lines, _CONF_END]) + "\n"

    if _CONF_MARKER in content:
        start = content.index(_CONF_MARKER)
        if _CONF_END in content:
            end = content.index(_CONF_END) + len(_CONF_END)
            if end < len(content) and content[end] == "\n":
                end += 1
        else:
            end = len(content)
        content = content[:start] + new_block + content[end:]
    else:
        content = content.rstrip("\n") + "\n\n" + new_block

    conf_path.write_text(content)
    _log.debug("Wrote pg-here settings to %s", conf_path)


def start(
    install_dir: Path,
    data_dir: Path,
    port: int,
    env: dict[str, str] | None = None,
) -> None:
    """Start PostgreSQL using pg_ctl. Waits until server is ready."""
    if is_running(install_dir, data_dir, env):
        _log.warning("PostgreSQL is already running (data_dir=%s)", data_dir)
        return

    pg_ctl = _find_binary(install_dir, "pg_ctl")
    _run(
        [
            str(pg_ctl),
            "start",
            "-D", str(data_dir),
            "-l", str(data_dir / "pg.log"),
            "-w",
            "-o", f"-p {port}",
        ],
        env=env,
    )
    _log.info("PostgreSQL started on port %d", port)


def stop(
    install_dir: Path,
    data_dir: Path,
    env: dict[str, str] | None = None,
) -> None:
    """Stop PostgreSQL gracefully. No-op if not running."""
    if not is_running(install_dir, data_dir, env):
        _log.debug("PostgreSQL is not running, nothing to stop")
        return

    pg_ctl = _find_binary(install_dir, "pg_ctl")
    result = _run(
        [str(pg_ctl), "stop", "-D", str(data_dir), "-m", "fast"],
        env=env,
        check=False,
    )
    if result.returncode != 0:
        _log.warning("pg_ctl stop returned %d: %s", result.returncode, result.stderr.strip())
    else:
        _log.info("PostgreSQL stopped")


def is_running(
    install_dir: Path,
    data_dir: Path,
    env: dict[str, str] | None = None,
) -> bool:
    """Check if PostgreSQL is running via pg_ctl status."""
    pg_ctl = _find_binary(install_dir, "pg_ctl")
    result = _run(
        [str(pg_ctl), "status", "-D", str(data_dir)],
        env=env,
        check=False,
    )
    return result.returncode == 0


def register_shutdown(stop_fn: Callable[[], None]) -> Callable[[], None]:
    """Register SIGINT/SIGTERM handlers that call stop_fn. Returns an unregister function."""
    stopping = False
    prev_sigint = signal.getsignal(signal.SIGINT)
    prev_sigterm = signal.getsignal(signal.SIGTERM)

    def handler(signum: int, frame: object) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        _log.info("Received signal %s, shutting down...", signal.Signals(signum).name)
        try:
            stop_fn()
        except Exception:
            _log.exception("Error during shutdown")

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    def unregister() -> None:
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)

    return unregister
