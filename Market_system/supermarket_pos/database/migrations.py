"""Small, transactional SQLite schema migration runner.

Migrations are append-only and never drop or truncate customer data. SQLite's
user_version is updated only after the corresponding migration succeeds.
"""
from typing import Callable, Dict

import sqlite3


REQUIRED_SCHEMA_VERSION = 2


def _column_exists(connection: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in connection.execute(f"PRAGMA table_info({table})"))


def _migration_1(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS App_Metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def _migration_2(connection: sqlite3.Connection) -> None:
    invoices_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Invoices'"
    ).fetchone()
    if not invoices_exists:
        return
    if not _column_exists(connection, "Invoices", "synced"):
        connection.execute(
            "ALTER TABLE Invoices ADD COLUMN synced INTEGER NOT NULL DEFAULT 0"
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_synced
        ON Invoices(synced, id)
        """
    )


MIGRATIONS: Dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _migration_1,
    2: _migration_2,
}


def get_schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def migrate_database(db_path: str) -> int:
    """Migrate *db_path* atomically and return the resulting schema version."""
    connection = sqlite3.connect(db_path)
    try:
        current = get_schema_version(connection)
        if current > REQUIRED_SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema {current} is newer than app schema "
                f"{REQUIRED_SCHEMA_VERSION}"
            )
        for version in range(current + 1, REQUIRED_SCHEMA_VERSION + 1):
            migration = MIGRATIONS.get(version)
            if migration is None:
                raise RuntimeError(f"Missing migration for schema version {version}")
            connection.execute("BEGIN")
            try:
                migration(connection)
                connection.execute(f"PRAGMA user_version = {version}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return get_schema_version(connection)
    finally:
        connection.close()
