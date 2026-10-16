"""Postgres connection helper; the URL comes from DATABASE_URL in the .env file."""
import os
from importlib import import_module
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def get_connection() -> Any:
    load_dotenv(Path(__file__).parent / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Missing DATABASE_URL in .env")

    try:
        psycopg = import_module("psycopg")
    except ImportError as exc:
        raise RuntimeError("Install the PostgreSQL driver with 'pip install psycopg[binary]'.") from exc

    try:
        # Percent-encoded characters in the URL (e.g. %40, %23) are decoded by libpq
        return psycopg.connect(url, connect_timeout=10)
    except psycopg.OperationalError as exc:
        raise ConnectionError(f"Could not connect to Postgres: {exc}") from exc


if __name__ == "__main__":
    with get_connection() as conn:
        print("Connected:", conn.execute("SELECT version()").fetchone()[0])
