"""
Enhanced active memory for processed sitemap recipe URLs with analytics
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

DB_PATH = Path("scraped_memory.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    # Enhanced schema with additional metadata
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scraped_urls (
            url TEXT PRIMARY KEY,
            domain TEXT,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            recipe_count INTEGER DEFAULT 0,
            last_scraped TEXT,
            status TEXT DEFAULT 'processed',
            error_count INTEGER DEFAULT 0
        )
        """
    )
    
    # Analytics table for tracking scraping performance
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scraping_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            scrape_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_urls INTEGER,
            new_urls INTEGER,
            skipped_urls INTEGER,
            errors INTEGER,
            duration_seconds REAL
        )
        """
    )
    
    conn.commit()
    return conn


def has_url(url: str) -> bool:
    """Check if URL has been processed"""
    with _conn() as conn:
        row = conn.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,)).fetchone()
        return bool(row)


def mark_url(url: str, recipe_count: int = 0, status: str = 'processed') -> None:
    """Mark URL as processed with additional metadata"""
    domain = urlparse(url).netloc
    
    with _conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO scraped_urls(url, domain, recipe_count, last_scraped, status)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (url, domain, recipe_count, status)
        )
        conn.commit()


def mark_url_error(url: str, error_msg: str = "") -> None:
    """Mark URL as having errors"""
    domain = urlparse(url).netloc
    
    with _conn() as conn:
        # Increment error count
        conn.execute(
            """
            INSERT INTO scraped_urls(url, domain, status, error_count)
            VALUES (?, ?, 'error', 1)
            ON CONFLICT(url) DO UPDATE SET
            error_count = error_count + 1,
            last_scraped = CURRENT_TIMESTAMP,
            status = 'error'
            """,
            (url, domain)
        )
        conn.commit()


def get_domain_stats(domain: str) -> Dict:
    """Get scraping statistics for a specific domain"""
    with _conn() as conn:
        stats = conn.execute(
            """
            SELECT 
                COUNT(*) as total_urls,
                COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_urls,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_urls,
                SUM(recipe_count) as total_recipes,
                MAX(processed_at) as last_processed
            FROM scraped_urls 
            WHERE domain = ?
            """,
            (domain,)
        ).fetchone()
        
        return {
            'domain': domain,
            'total_urls': stats[0] or 0,
            'processed_urls': stats[1] or 0,
            'error_urls': stats[2] or 0,
            'total_recipes': stats[3] or 0,
            'last_processed': stats[4],
            'success_rate': (stats[1] or 0) / max(1, stats[0] or 1)
        }


def log_scraping_session(domain: str, total_urls: int, new_urls: int, 
                        skipped_urls: int, errors: int, duration: float) -> None:
    """Log a scraping session for analytics"""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO scraping_analytics 
            (domain, total_urls, new_urls, skipped_urls, errors, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (domain, total_urls, new_urls, skipped_urls, errors, duration)
        )
        conn.commit()


def get_recent_analytics(limit: int = 50) -> List[Dict]:
    """Get recent scraping analytics"""
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT domain, scrape_date, total_urls, new_urls, skipped_urls, errors, duration_seconds
            FROM scraping_analytics 
            ORDER BY scrape_date DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [
            {
                'domain': row[0],
                'scrape_date': row[1],
                'total_urls': row[2],
                'new_urls': row[3],
                'skipped_urls': row[4],
                'errors': row[5],
                'duration_seconds': row[6],
                'success_rate': row[3] / max(1, row[2])
            }
            for row in rows
        ]


def cleanup_old_records(days: int = 30) -> int:
    """Clean up old records to manage database size"""
    with _conn() as conn:
        # Delete old analytics
        result = conn.execute(
            "DELETE FROM scraping_analytics WHERE scrape_date < datetime('now', '-{} days')".format(days)
        )
        
        # Keep URLs but update old error records
        conn.execute(
            "UPDATE scraped_urls SET status = 'archived' WHERE status = 'error' AND processed_at < datetime('now', '-{} days')".format(days)
        )
        
        conn.commit()
        return result.rowcount


# Legacy functions for backward compatibility
def get_urls_by_domain(domain: str) -> List[str]:
    """Get all processed URLs for a domain"""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT url FROM scraped_urls WHERE domain = ? AND status = 'processed'", 
            (domain,)
        ).fetchall()
        return [row[0] for row in rows]
