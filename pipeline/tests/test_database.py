import pytest
import sqlite3
import os
from unittest.mock import patch
from pipeline.db.database import get_connection, init_db, upsert_candidate


class TestDatabase:
    def test_init_db_creates_tables(self, tmp_db):
        with patch("pipeline.config.DB_PATH", tmp_db):
            init_db()
            conn = sqlite3.connect(tmp_db)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            conn.close()
            assert "candidates" in tables
            assert "scanner_runs" in tables
            assert "stocks" in tables
            assert "watchlist" in tables
            assert "alerts" in tables

    def test_get_connection_row_factory(self, tmp_db):
        with patch("pipeline.config.DB_PATH", tmp_db):
            conn = get_connection()
            assert conn.row_factory == sqlite3.Row
            conn.close()

    def test_get_connection_wal_mode(self, tmp_db):
        with patch("pipeline.config.DB_PATH", tmp_db):
            conn = get_connection()
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"
            conn.close()

    def test_upsert_candidate_insert(self, tmp_db):
        with patch("pipeline.config.DB_PATH", tmp_db):
            init_db()
            conn = get_connection()
            data = {
                "ticker": "GME",
                "run_date": "2026-04-03",
                "score_total": 75.0,
                "is_current": 1,
            }
            upsert_candidate(conn, data)
            conn.commit()
            row = conn.execute(
                "SELECT * FROM candidates WHERE ticker='GME'"
            ).fetchone()
            assert row is not None
            assert row["score_total"] == 75.0
            conn.close()

    def test_upsert_candidate_update(self, tmp_db):
        with patch("pipeline.config.DB_PATH", tmp_db):
            init_db()
            conn = get_connection()
            data = {
                "ticker": "GME",
                "run_date": "2026-04-03",
                "score_total": 75.0,
                "is_current": 1,
            }
            upsert_candidate(conn, data)
            conn.commit()
            # Update score
            data["score_total"] = 80.0
            upsert_candidate(conn, data)
            conn.commit()
            row = conn.execute(
                "SELECT * FROM candidates WHERE ticker='GME'"
            ).fetchone()
            assert row["score_total"] == 80.0
            # Should still be one row
            count = conn.execute(
                "SELECT COUNT(*) FROM candidates WHERE ticker='GME'"
            ).fetchone()[0]
            assert count == 1
            conn.close()

    def test_upsert_excludes_id_ticker_run_date(self, tmp_db):
        """Verify the UPDATE SET clause excludes id, ticker, run_date."""
        with patch("pipeline.config.DB_PATH", tmp_db):
            init_db()
            conn = get_connection()
            data = {
                "ticker": "GME",
                "run_date": "2026-04-03",
                "score_total": 75.0,
            }
            upsert_candidate(conn, data)
            conn.commit()
            # Get the auto-generated id
            row = conn.execute(
                "SELECT id FROM candidates WHERE ticker='GME'"
            ).fetchone()
            original_id = row["id"]
            # Upsert again
            data["score_total"] = 80.0
            upsert_candidate(conn, data)
            conn.commit()
            row = conn.execute(
                "SELECT id, ticker, run_date FROM candidates WHERE ticker='GME'"
            ).fetchone()
            assert row["id"] == original_id
            assert row["ticker"] == "GME"
            assert row["run_date"] == "2026-04-03"
            conn.close()
