"""
Active memory for processed sitemap recipe URLs.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("scraped_memory.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scraped_urls (
            url TEXT PRIMARY KEY,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def has_url(url: str) -> bool:
    with _conn() as conn:
        row = conn.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,)).fetchone()
        return bool(row)


def mark_url(url: str) -> None:
    with _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO scraped_urls(url) VALUES (?)", (url,))
        conn.commit()
