# pg-here

Run a local PostgreSQL instance in your project folder with one command.

```bash
uvx pg-here
```

That's it. No Docker, no Homebrew, no system-wide installation. PostgreSQL runs from `./pg_local/` inside your project and shuts down cleanly with Ctrl+C.

## Why?

Setting up PostgreSQL for local development is annoying:

- **Docker**: Heavy, slow startup, needs daemon running, port mapping headaches
- **Homebrew/apt**: System-wide install, version conflicts between projects
- **Cloud databases**: Network latency, costs, can't work offline

pg-here downloads a self-contained PostgreSQL binary and runs it locally, per-project. Each project gets its own database and its own data directory. No conflicts. No configuration. Just `uvx pg-here`.

## Features

- **Zero config**: Works out of the box with sensible defaults
- **Per-project isolation**: Data lives in `./pg_local/`, gitignored
- **Auto-download**: Downloads PostgreSQL binary on first run (~30MB)
- **Cached**: Subsequent runs start instantly — no re-download
- **pg_stat_statements**: Pre-configured for query performance analysis
- **Cross-platform**: macOS (Apple Silicon & Intel) and Linux (x86_64 & ARM64)
- **Clean shutdown**: Ctrl+C stops PostgreSQL gracefully

## Install

```bash
# Run directly (no install needed)
uvx pg-here

# Or install globally
uv tool install pg-here

# Or install in your project
uv add --dev pg-here
```

Requires Python 3.10+.

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

### Options

```
--username, -u    PostgreSQL superuser name (default: postgres)
--password        Password for connection string (default: postgres)
--port            Port number (default: 55432)
--database, -d    Database name (default: postgres)
--pg-version      PostgreSQL version, e.g. 17.4.0 (default: latest cached or 17.4.0)
```

### Custom database

```bash
uvx pg-here -d myapp
```

Creates `myapp` database automatically if it doesn't exist.

### Use in a project

Add to your `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pg-here"]
```

Then:

```bash
uv run pg-here
```

### Connect from your app

The connection string is printed on startup. Use it with any PostgreSQL client:

```python
import psycopg

conn = psycopg.connect("postgresql://postgres:postgres@localhost:55432/myapp")
```

```bash
# Or from the command line
psql postgresql://postgres:postgres@localhost:55432/myapp
```

### Python API

Use pg-here as a library in tests or scripts:

```python
from pg_here import start_pg_here

handle = start_pg_here(port=55432, database="myapp")
print(handle.connection_string)
# ... use PostgreSQL ...
handle.stop()
```

## How it works

1. Downloads pre-built PostgreSQL binaries from [Zonky embedded-postgres-binaries](https://github.com/zonkyio/embedded-postgres-binaries) (Maven Central)
2. Extracts to `./pg_local/bin/{version}/`
3. Initializes a data cluster in `./pg_local/data/`
4. Starts PostgreSQL on the specified port
5. Creates your database and installs pg_stat_statements
6. Waits for Ctrl+C, then shuts down gracefully

All files live under `./pg_local/` — add `pg_local/` to your `.gitignore`.

## Directory structure

```
your-project/
├── pg_local/              ← created by pg-here
│   ├── bin/17.4.0/        ← PostgreSQL binaries (cached)
│   └── data/              ← database cluster
├── .gitignore             ← should include pg_local/
└── ...
```

## Acknowledgments

Inspired by [pg-here](https://github.com/mayfer/pg-here) (Node.js) by [@mayfer](https://github.com/mayfer). This is an independent Python implementation sharing the same vision: one-command local PostgreSQL for any project.

Uses [Zonky embedded-postgres-binaries](https://github.com/zonkyio/embedded-postgres-binaries) (Apache 2.0) for pre-built PostgreSQL distributions.

## License

MIT
