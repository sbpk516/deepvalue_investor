from __future__ import annotations

import sqlite3
import os
from pipeline import config
from pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def get_connection() -> sqlite3.Connection:
    # FIX: timeout=10 prevents OperationalError if two pipeline runs
    # overlap (e.g. manual run + scheduled run). WAL mode + timeout
    # together handle most concurrent access scenarios safely.
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db() -> None:
    """Create all tables if they don't exist."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with get_connection() as conn:
        conn.executescript(schema_sql)
    logger.info("Database initialised")

def upsert_candidate(conn: sqlite3.Connection, data: dict) -> None:
    """Insert or update a scored candidate.

    FIX: original code included 'id', 'ticker', 'run_date' in the
    UPDATE SET clause which breaks the UNIQUE constraint logic.
    These must be excluded — they are the conflict keys, not update targets.
    """
    _EXCLUDE_FROM_UPDATE = frozenset({"id", "ticker", "run_date"})
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    updates = ", ".join([f"{k}=excluded.{k}" for k in data.keys()
                         if k not in _EXCLUDE_FROM_UPDATE])
    sql = f"""
        INSERT INTO candidates ({columns}) VALUES ({placeholders})
        ON CONFLICT(ticker, run_date) DO UPDATE SET {updates}
    """
    conn.execute(sql, list(data.values()))

def get_watchlist(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM watchlist").fetchall()
    return [dict(row) for row in rows]

def save_alert(conn: sqlite3.Connection, ticker: str,
               alert_type: str, message: str) -> None:
    from datetime import date
    conn.execute(
        """INSERT INTO alerts (ticker, alert_type, alert_message, trigger_date)
           VALUES (?, ?, ?, ?)""",
        (ticker, alert_type, message, date.today().isoformat())
    )
