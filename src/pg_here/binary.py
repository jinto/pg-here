"""PostgreSQL binary download and cache management."""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import Callable

import httpx

MAVEN_BASE = "https://repo1.maven.org/maven2/io/zonky/test/postgres"
DEFAULT_PG_VERSION = "17.4.0"
_VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")

PLATFORM_MAP: dict[tuple[str, str], str] = {
    ("Darwin", "arm64"): "darwin-arm64v8",
    ("Darwin", "x86_64"): "darwin-amd64",
    ("Linux", "x86_64"): "linux-amd64",
    ("Linux", "aarch64"): "linux-arm64v8",
}

_COMPLETE_MARKER = ".pg_here_complete"
_EXEC_BITS = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
_log = logging.getLogger(__name__)


def detect_platform() -> str:
    key = (platform.system(), platform.machine())
    artifact = PLATFORM_MAP.get(key)
    if artifact is None:
        raise RuntimeError(
            f"Unsupported platform: {key[0]} {key[1]}. "
            f"Supported: {', '.join(f'{s} {m}' for s, m in PLATFORM_MAP)}"
        )
    return artifact


def get_install_dir(project_dir: Path, version: str) -> Path:
    return project_dir / "pg_local" / "bin" / version


def is_installed(project_dir: Path, version: str) -> bool:
    return (get_install_dir(project_dir, version) / _COMPLETE_MARKER).is_file()


def download_url(plat: str, version: str) -> str:
    artifact = f"embedded-postgres-binaries-{plat}"
    return f"{MAVEN_BASE}/{artifact}/{version}/{artifact}-{version}.jar"


def _has_symlink_ancestor(path: Path, root: Path) -> bool:
    """Check if any directory between path and root is a symlink."""
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            return True
    return False


def _is_safe_member(member: tarfile.TarInfo, dest: Path) -> bool:
    """Return True if a tar member is safe to extract into dest."""
    if not (member.isfile() or member.isdir()):
        _log.debug("Skipping non-regular entry: %s (type=%s)", member.name, member.type)
        return False
    if member.name.startswith("/") or ".." in member.name.split("/"):
        _log.debug("Skipping entry with unsafe path: %s", member.name)
        return False
    raw_target = dest / member.name
    resolved = raw_target.resolve()
    if not resolved.is_relative_to(dest):
        _log.debug("Skipping entry outside dest: %s", member.name)
        return False
    if _has_symlink_ancestor(raw_target, dest):
        _log.debug("Skipping entry with symlink ancestor: %s", member.name)
        return False
    return True


def _safe_tar_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    skipped = 0
    for member in tar.getmembers():
        if _is_safe_member(member, dest):
            tar.extract(member, dest, set_attrs=False)
        else:
            skipped += 1
    if skipped:
        _log.debug("Skipped %d tar entries (non-regular/unsafe)", skipped)


def _find_pg_root(extracted: Path) -> Path:
    """Find the directory containing bin/postgres after extraction."""
    if (extracted / "bin" / "postgres").exists():
        return extracted
    for child in extracted.iterdir():
        if child.is_dir() and (child / "bin" / "postgres").exists():
            return child
    raise RuntimeError(
        f"Could not find bin/postgres in extracted directory: {extracted}"
    )


def _make_executable(bin_dir: Path) -> None:
    for entry in bin_dir.iterdir():
        if entry.is_file():
            entry.chmod(entry.stat().st_mode | _EXEC_BITS)


def _semver_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(s) for s in version.split("."))


def list_installed_versions(project_dir: Path) -> list[str]:
    bin_base = project_dir / "pg_local" / "bin"
    if not bin_base.is_dir():
        return []
    versions = [
        d.name
        for d in bin_base.iterdir()
        if d.is_dir() and (d / _COMPLETE_MARKER).is_file()
    ]
    versions.sort(key=_semver_tuple, reverse=True)
    return versions


def _validate_version(version: str) -> str:
    if not _VERSION_RE.match(version):
        raise ValueError(
            f"Invalid PostgreSQL version: {version!r}. "
            "Expected format: X.Y.Z (digits and dots only)."
        )
    return version


def resolve_version(project_dir: Path, requested: str | None = None) -> str:
    if requested:
        return _validate_version(requested)
    installed = list_installed_versions(project_dir)
    if installed:
        return installed[0]
    return DEFAULT_PG_VERSION


def _download_jar(
    url: str,
    jar_path: Path,
    version: str,
    plat: str,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> None:
    """Download the PostgreSQL jar from Maven, reporting progress."""
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as resp:
        if resp.status_code == 404:
            raise RuntimeError(
                f"PostgreSQL {version} not found for {plat}. "
                f"Check available versions at: {MAVEN_BASE}/embedded-postgres-binaries-{plat}/"
            )
        resp.raise_for_status()
        total = resp.headers.get("content-length")
        total_bytes = int(total) if total else None
        downloaded = 0
        with open(jar_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress:
                    on_progress(downloaded, total_bytes)


def _extract_txz_from_jar(jar_path: Path, txz_path: Path, url: str) -> None:
    """Extract the largest .txz file from a PostgreSQL jar."""
    with zipfile.ZipFile(jar_path) as zf:
        txz_entries = [
            n for n in zf.namelist()
            if n.endswith(".txz") and not n.startswith("META-INF/")
        ]
        if not txz_entries:
            raise RuntimeError(f"No .txz file found in jar: {url}")
        txz_entries.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
        with zf.open(txz_entries[0]) as src, open(txz_path, "wb") as dst:
            shutil.copyfileobj(src, dst)


def download_and_extract(
    project_dir: Path,
    version: str,
    plat: str | None = None,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    _validate_version(version)
    if plat is None:
        plat = detect_platform()

    install_dir = get_install_dir(project_dir, version)

    if is_installed(project_dir, version):
        return install_dir

    if install_dir.exists():
        shutil.rmtree(install_dir)

    install_dir.parent.mkdir(parents=True, exist_ok=True)

    staging = install_dir.parent / f".staging-{version}-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    try:
        url = download_url(plat, version)
        jar_path = staging / "pg.jar"
        txz_path = staging / "pg.txz"

        _download_jar(url, jar_path, version, plat, on_progress)
        _extract_txz_from_jar(jar_path, txz_path, url)
        jar_path.unlink()

        extract_dir = staging / "extracted"
        extract_dir.mkdir()
        with tarfile.open(txz_path, "r:xz") as tar:
            _safe_tar_extract(tar, extract_dir)
        txz_path.unlink()

        pg_root = _find_pg_root(extract_dir)
        bin_dir = pg_root / "bin"
        if bin_dir.is_dir():
            _make_executable(bin_dir)

        pg_root.rename(install_dir)
        (install_dir / _COMPLETE_MARKER).write_text("")

    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    return install_dir
