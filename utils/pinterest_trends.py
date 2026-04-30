"""
Pinterest trend ingestion with Playwright-first scraping and RSS fallback.
"""

from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import quote_plus, urlparse

import feedparser


DEFAULT_COMPETITOR_RSS = [
    "https://www.pinterest.com/tasty/feed.rss",
    "https://www.pinterest.com/foodnetwork/feed.rss",
    "https://www.pinterest.com/allrecipes/feed.rss",
]


def _keywords_from_recipe_url(recipe_url: str) -> list[str]:
    path = urlparse(recipe_url).path.lower()
    words = [w for w in re.split(r"[^a-z0-9]+", path) if len(w) > 2]
    joined = " ".join(words[-6:]).strip()
    return [joined] if joined else ["easy dinner recipe"]


def _normalize_pin(title: str, description: str, image_url: str, pin_url: str, source: str) -> dict:
    return {
        "title": (title or "").strip(),
        "description": (description or "").strip(),
        "image_url": (image_url or "").strip(),
        "pin_url": (pin_url or "").strip(),
        "source": source,
    }


def scrape_pinterest_with_playwright(keywords: Iterable[str], max_pins: int = 10) -> list[dict]:
    from playwright.sync_api import sync_playwright  # lazy import

    pins: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)

        for keyword in keywords:
            search_url = f"https://www.pinterest.com/search/pins/?q={quote_plus(keyword)}"
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            cards = page.locator("a[href*='/pin/']")
            count = min(cards.count(), max_pins * 3)
            for i in range(count):
                if len(pins) >= max_pins:
                    break
                card = cards.nth(i)
                href = card.get_attribute("href") or ""
                full_url = f"https://www.pinterest.com{href}" if href.startswith("/") else href
                title = card.get_attribute("aria-label") or ""
                img = card.locator("img").first
                image_url = img.get_attribute("src") if img.count() else ""
                if not (title or image_url):
                    continue
                pins.append(_normalize_pin(title, "", image_url or "", full_url, "playwright"))
            if len(pins) >= max_pins:
                break

        browser.close()
    return pins[:max_pins]


def scrape_pinterest_from_rss(feed_urls: Iterable[str], max_pins: int = 10) -> list[dict]:
    pins: list[dict] = []
    for feed_url in feed_urls:
        parsed = feedparser.parse(feed_url)
        entries = parsed.entries or []
        for entry in entries:
            if len(pins) >= max_pins:
                break
            media_content = entry.get("media_content", [])
            image_url = ""
            if media_content and isinstance(media_content, list):
                image_url = media_content[0].get("url", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            pins.append(
                _normalize_pin(
                    entry.get("title", ""),
                    summary,
                    image_url,
                    entry.get("link", ""),
                    "rss",
                )
            )
    return pins[:max_pins]


def collect_trending_pins(
    recipe_url: str,
    max_pins: int = 10,
    competitor_rss_feeds: list[str] | None = None,
) -> tuple[list[dict], str]:
    keywords = _keywords_from_recipe_url(recipe_url)
    try:
        pins = scrape_pinterest_with_playwright(keywords, max_pins=max_pins)
        if pins:
            return pins, "playwright"
    except Exception:
        pass

    feeds = competitor_rss_feeds or DEFAULT_COMPETITOR_RSS
    pins = scrape_pinterest_from_rss(feeds, max_pins=max_pins)
    return pins, "rss_fallback"
