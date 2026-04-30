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


def clear_all_urls() -> None:
    """Clear all processed URLs from memory to allow re-scraping."""
    with _conn() as conn:
        conn.execute("DELETE FROM scraped_urls")
        conn.commit()


def get_processed_count() -> int:
    """Get the count of processed URLs in memory."""
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM scraped_urls").fetchone()
        return row[0] if row else 0


def get_all_processed_urls() -> list[str]:
    """Get all processed URLs from memory."""
    with _conn() as conn:
        rows = conn.execute("SELECT url FROM scraped_urls ORDER BY processed_at DESC").fetchall()
        return [row[0] for row in rows]


def clear_url(url: str) -> None:
    """Remove a specific URL from processed memory to allow re-scraping."""
    with _conn() as conn:
        conn.execute("DELETE FROM scraped_urls WHERE url = ?", (url,))
        conn.commit()
