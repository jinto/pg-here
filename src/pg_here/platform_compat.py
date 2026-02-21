"""Platform-specific compatibility (Linux libxml2, etc.)."""

from __future__ import annotations

import platform
import re

_MISSING_LIB_RE = re.compile(
    r"(lib\S+\.so\S*)\s.*(?:not found|cannot open shared object file)"
)

_INSTALL_HINTS: dict[str, dict[str, str]] = {
    "libxml2": {
        "Ubuntu/Debian": "sudo apt-get install libxml2",
        "Fedora/RHEL": "sudo dnf install libxml2",
        "Alpine": "sudo apk add libxml2",
    },
}


def detect_missing_libs(error_message: str) -> list[str]:
    """Extract missing shared library names from an error message."""
    return _MISSING_LIB_RE.findall(error_message)


def format_linux_help(missing: list[str]) -> str:
    """Format installation guidance for missing Linux libraries."""
    if not missing:
        return ""

    lines = [f"Missing libraries: {', '.join(missing)}", ""]
    for lib in missing:
        base = lib.split(".so")[0]  # e.g. "libxml2"
        hints = _INSTALL_HINTS.get(base)
        if hints:
            lines.append(f"Install {base}:")
            for distro, cmd in hints.items():
                lines.append(f"  {distro}: {cmd}")
        else:
            lines.append(f"Install the package providing {lib} for your distribution.")
    return "\n".join(lines)


def is_linux() -> bool:
    """Return True if the current platform is Linux."""
    return platform.system() == "Linux"
