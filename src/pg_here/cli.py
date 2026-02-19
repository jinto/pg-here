import click


@click.command()
@click.option("--username", "-u", default="postgres", help="PostgreSQL username.")
@click.option("--password", default="postgres", envvar="PGPASSWORD", help="PostgreSQL password (or set PGPASSWORD).")
@click.option("--port", default=55432, type=int, help="PostgreSQL port.")
@click.option("--database", "-d", default="postgres", help="Database name.")
@click.option("--pg-version", default=None, help="PostgreSQL version (e.g. 17.4.0).")
def main(username: str, password: str, port: int, database: str, pg_version: str | None) -> None:
    """Run a local PostgreSQL instance in your project folder."""
    click.echo("pg-here is not yet implemented.")
