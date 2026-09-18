"""Database configuration, connection management, and schema migrations."""

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "dashboard.db"


def connection() -> Iterator[sqlite3.Connection]:
    """Yield a request-scoped SQLite connection with row access by column name."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
    except sqlite3.Error:
        db.rollback()
        raise
    else:
        db.commit()
    finally:
        db.close()


def _add_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    """Create the SQLite schema and apply additive migrations safely."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        db = sqlite3.connect(DB_PATH)
    except sqlite3.Error as exc:
        raise RuntimeError(f"Unable to open SQLite database at {DB_PATH}") from exc

    try:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY,
                store_name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                subscription_end DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'expired', 'blocked')),
                monthly_price REAL NOT NULL DEFAULT 0,
                license_key_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                total_daily_sales REAL NOT NULL DEFAULT 0,
                total_low_stock_count INTEGER NOT NULL DEFAULT 0,
                last_active_cashier_session TEXT,
                app_status TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                monthly_price REAL NOT NULL DEFAULT 0,
                annual_price REAL NOT NULL DEFAULT 0,
                features TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'مشرف',
                permissions TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                ip_address TEXT NOT NULL DEFAULT '-',
                logged_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'نجاح'
            );
            CREATE TABLE IF NOT EXISTS app_releases (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                version TEXT NOT NULL,
                download_url TEXT NOT NULL
            );
            INSERT OR IGNORE INTO app_releases(id, version, download_url)
            VALUES (1, '1.2.0',
                    'https://preeminent-truffle-0ea26e.netlify.app/static/updates/app-1.2.0.zip');
            """
        )
        _add_column(db, "stores", "owner_name", "TEXT NOT NULL DEFAULT ''")
        _add_column(db, "stores", "plan_id", "INTEGER")
        for name, monthly, annual, features in [
            ("Basic", 99, 999, ["إدارة المخزون", "نقطة بيع واحدة", "دعم البريد الإلكتروني"]),
            ("Pro", 199, 1999, ["كل مزايا Basic", "تقارير متقدمة", "حتى 5 نقاط بيع"]),
            ("Enterprise", 399, 3999, ["كل مزايا Pro", "دعم أولوية", "نقاط بيع غير محدودة"]),
        ]:
            db.execute(
                "INSERT OR IGNORE INTO plans(name, monthly_price, annual_price, features) VALUES (?, ?, ?, ?)",
                (name, monthly, annual, json.dumps(features, ensure_ascii=False)),
            )
        db.commit()
    except sqlite3.Error as exc:
        db.rollback()
        raise RuntimeError("SQLite schema migration failed") from exc
    finally:
        db.close()
