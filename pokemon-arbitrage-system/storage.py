"""SQLite storage for Pokemon arbitrage backend."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent / "pokemon_arbitrage.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                role TEXT NOT NULL,
                source_type TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                card_name TEXT NOT NULL,
                set_name TEXT,
                condition_note TEXT,
                image_url TEXT,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                asking_price_hkd REAL,
                target_resale_hkd REAL,
                estimated_profit_hkd REAL,
                estimated_margin_pct REAL,
                confidence INTEGER NOT NULL DEFAULT 50,
                risk_note TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER NOT NULL,
                buyer_name TEXT NOT NULL,
                buyer_contact TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                message TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        ensure_column(conn, "opportunities", "image_url", "TEXT")


def ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
