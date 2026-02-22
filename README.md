# pg-here

[![PyPI](https://img.shields.io/pypi/v/pg-here)](https://pypi.org/project/pg-here/)
[![Downloads](https://img.shields.io/pypi/dm/pg-here)](https://pypi.org/project/pg-here/)
[![CI](https://github.com/jinto/pg-here/actions/workflows/python-package.yml/badge.svg)](https://github.com/jinto/pg-here/actions/workflows/python-package.yml)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/pg-here)](https://pypi.org/project/pg-here/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Run a local PostgreSQL instance in your project folder with one command.

```bash
uvx pg-here
```

That's it. No Docker, no Homebrew, no system-wide installation. PostgreSQL runs from `./pg_local/` inside your project and shuts down cleanly with Ctrl+C.

> **Python port** of [pg-here](https://github.com/mayfer/pg-here) (Node.js) by [@mayfer](https://github.com/mayfer).
> Same concept, independent implementation — rewritten from scratch in Python for the `uv`/`uvx` ecosystem.

[한국어 README](README.ko.md)

## Why?

Setting up PostgreSQL for local development is annoying:

| Approach | Problem |
|----------|---------|
| **Docker** | Heavy, slow startup, daemon required, port mapping headaches |
| **Homebrew / apt** | System-wide install, version conflicts between projects |
| **Cloud databases** | Network latency, costs, can't work offline |
| **Manual binary** | Download, extract, initdb, pg_ctl, configure... every time |

pg-here does all of that in one command. Each project gets its own PostgreSQL binary and data directory. No conflicts. No configuration.

## Features

- **One command**: `uvx pg-here` — nothing else needed
- **Zero config**: Sensible defaults, works out of the box
- **Per-project isolation**: Data lives in `./pg_local/`, easily gitignored
- **Auto-download**: Fetches a pre-built PostgreSQL binary on first run (~30MB)
- **Instant restart**: Binary is cached — subsequent runs start in seconds
- **pg_stat_statements**: Pre-configured for query performance analysis
- **Python API**: Use as a library in tests and scripts
- **Cross-platform**: macOS (Apple Silicon & Intel) and Linux (x86_64 & ARM64)
- **Clean shutdown**: Ctrl+C stops PostgreSQL gracefully

## Install

```bash
# Run directly — no install needed
uvx pg-here

# Or install globally
uv tool install pg-here

# Or add to your project
uv add --dev pg-here
```

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

## Usage

### Quick start

```bash
uvx pg-here
```

Output:

```
PostgreSQL 17.4.0 running on port 55432

  psql postgresql://postgres:postgres@localhost:55432/postgres

Press Ctrl+C to stop.
```

Copy the connection string and use it with any PostgreSQL client.

### Custom database

```bash
uvx pg-here -d myapp
```

Creates the `myapp` database automatically if it doesn't exist.

### All options

```
Usage: pg-here [OPTIONS]

Options:
  -u, --username TEXT   PostgreSQL superuser name (default: postgres)
  --password TEXT       Password for connection string (default: postgres)
  --port INTEGER        Port number (default: 55432)
  -d, --database TEXT   Database name (default: postgres)
  --pg-version TEXT     PostgreSQL version, e.g. 17.4.0
  --help                Show this message and exit.
```

### Use in a project

Add to your `pyproject.toml`:

```toml
[dependency-groups]
dev = ["pg-here"]
```

Then:

```bash
uv run pg-here
```

### Connect from your app

```python
import psycopg

conn = psycopg.connect("postgresql://postgres:postgres@localhost:55432/myapp")
```

```bash
psql postgresql://postgres:postgres@localhost:55432/myapp
```

### Python API

Use pg-here programmatically in tests or scripts:

```python
from pg_here import start_pg_here

# Start a local PostgreSQL instance
handle = start_pg_here(port=55432, database="myapp")
print(handle.connection_string)
# postgresql://postgres:postgres@localhost:55432/myapp

# Create additional databases
handle.ensure_database("testdb")

# Get connection strings for other databases
uri = handle.connection_string_for("testdb")

# Stop when done
handle.stop()
```

#### pytest fixture example

```python
import pytest
from pg_here import start_pg_here

@pytest.fixture
def pg(tmp_path):
    handle = start_pg_here(project_dir=tmp_path, port=0)  # 0 = auto
    yield handle
    handle.stop()

def test_my_app(pg):
    conn = psycopg.connect(pg.connection_string)
    # ...
```

## How it works

```
uvx pg-here
    │
    ├─ 1. Download PostgreSQL binary from Maven Central (Zonky)
    ├─ 2. Extract to ./pg_local/bin/17.4.0/
    ├─ 3. initdb → initialize data cluster in ./pg_local/data/
    ├─ 4. pg_ctl start → run PostgreSQL on port 55432
    ├─ 5. Create database + install pg_stat_statements
    └─ 6. Wait for Ctrl+C → pg_ctl stop (graceful shutdown)
```

All files live under `./pg_local/`. Add it to your `.gitignore`:

```
# .gitignore
pg_local/
```

### Directory structure

```
your-project/
├── pg_local/              ← created by pg-here (gitignored)
│   ├── bin/17.4.0/        ← PostgreSQL binaries (cached)
│   │   ├── bin/
│   │   ├── lib/
│   │   └── share/
│   └── data/              ← database cluster
│       ├── PG_VERSION
│       ├── postgresql.conf
│       └── ...
└── ...
```

## Comparison

| | pg-here (Python) | pg-here (Node.js) | Docker Postgres | Homebrew |
|---|---|---|---|---|
| One command | `uvx pg-here` | `bunx pg-here` | `docker run ...` | `brew install` + config |
| Per-project isolation | Yes | Yes | Volume mounts | No |
| No daemon required | Yes | Yes | No (Docker daemon) | No (brew services) |
| Offline after first run | Yes | Yes | Needs image | Yes |
| Python API | Yes | No | No | No |
| Size | ~30MB binary | ~30MB binary | ~400MB image | ~100MB |

## Acknowledgments

- Inspired by [pg-here](https://github.com/mayfer/pg-here) (Node.js) by [@mayfer](https://github.com/mayfer). This is an independent Python implementation — no code was copied. We share the same vision: one-command local PostgreSQL for any project.
- Uses [Zonky embedded-postgres-binaries](https://github.com/zonkyio/embedded-postgres-binaries) (Apache 2.0) for pre-built PostgreSQL distributions via Maven Central.

## License

MIT
