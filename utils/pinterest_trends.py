"""
utils/pinterest_trends.py
STEP 1: Pinterest Scraping Engine with Playwright + RSS Fallback
Scrapes Pinterest for trending pins related to a recipe or topic.
"""

import re
import os
import time
import random
from pathlib import Path
from typing import Optional
import logging

import requests
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger(__name__)

# Predefined competitor RSS feeds for fallback
COMPETITOR_RSS_FEEDS = [
    "https://www.pinterest.com/nobscooking/feed.rss",
    "https://www.pinterest.com/tasty/feed.rss",
    "https://www.pinterest.com/buzzfeedtasty/feed.rss",
]


def _extract_keywords(query: str) -> str:
    """Extract search keywords from URL or query string."""
    if query.startswith('http'):
        # Extract keywords from URL path
        keywords = re.sub(r'[^\w\s-]', ' ', query).split()
        keywords = [k for k in keywords if len(k) > 2 and not k.lower() in ['http', 'https', 'www', 'com', 'recipe', 'recipes']][:5]
        return ' '.join(keywords)
    return query


def _install_playwright_if_needed():
    """Lazy install Playwright browsers only when scraping is needed."""
    import subprocess
    import os
    from pathlib import Path
    
    # Check if browsers are already installed
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    if cache_dir.exists() and any(cache_dir.glob("chromium*")):
        return True
    
    try:
        print("Installing Playwright browsers for Pinterest scraping...")
        result = subprocess.run(
            ["python", "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            print("Playwright Chromium installed successfully")
            return True
        else:
            print(f"Playwright install failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Playwright installation error: {e}")
        return False


def _scrape_with_playwright(search_term: str, max_pins: int = 10) -> Optional[list[dict]]:
    """
    Use Playwright to scrape Pinterest search results.
    Returns None if Playwright fails or is not available.
    """
    # Try to install browsers if not available
    if not _install_playwright_if_needed():
        return None
    
    try:
        from playwright.sync_api import sync_playwright
        
        pins = []
        search_url = f"https://www.pinterest.com/search/pins/?q={requests.utils.quote(search_term)}"
        
        with sync_playwright() as p:
            # Launch browser with stealth options
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # Navigate to Pinterest search
            page.goto(search_url, wait_until='networkidle', timeout=30000)
            
            # Wait for pins to load
            page.wait_for_selector('[data-test-id="pin"] || .Pin || [data-testid="pin-wrapper"]', timeout=10000)
            
            # Scroll to load more pins
            for _ in range(3):
                page.evaluate('window.scrollBy(0, 800)')
                time.sleep(random.uniform(0.5, 1.5))
            
            # Extract pin data
            pin_elements = page.query_selector_all('[data-test-id="pin"] || .Pin || [data-testid="pin-wrapper"]')
            
            for element in pin_elements[:max_pins]:
                try:
                    # Extract title
                    title_elem = element.query_selector('img')
                    title = title_elem.get_attribute('alt') if title_elem else search_term
                    
                    # Extract image URL
                    img_elem = element.query_selector('img')
                    image_url = img_elem.get_attribute('src') if img_elem else ''
                    # Get high-res version
                    if image_url and '236x' in image_url:
                        image_url = image_url.replace('236x', '736x')
                    
                    # Extract pin URL
                    link_elem = element.query_selector('a')
                    pin_url = link_elem.get_attribute('href') if link_elem else ''
                    if pin_url and not pin_url.startswith('http'):
                        pin_url = f"https://www.pinterest.com{pin_url}"
                    
                    pins.append({
                        "title": title or f"{search_term} recipe idea",
                        "description": f"Trending {search_term} pin from Pinterest",
                        "image_url": image_url,
                        "pin_url": pin_url,
                        "source": "Pinterest (Playwright)"
                    })
                except Exception as e:
                    logger.debug(f"Error extracting pin element: {e}")
                    continue
            
            browser.close()
        
        return pins if pins else None
        
    except ImportError:
        logger.info("Playwright not installed, skipping Playwright scraping")
        return None
    except Exception as e:
        logger.warning(f"Playwright scraping failed: {e}")
        return None


def _scrape_with_rss_fallback(search_term: str, max_pins: int = 10) -> Optional[list[dict]]:
    """
    CRITICAL FALLBACK: Parse competitor RSS feeds to gather recent pins.
    Used when Playwright fails or is blocked.
    """
    try:
        pins = []
        
        for rss_url in COMPETITOR_RSS_FEEDS:
            try:
                logger.info(f"Trying RSS fallback: {rss_url}")
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:max_pins]:
                    # Extract data from RSS entry
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    link = entry.get('link', '')
                    
                    # Try to find image in content
                    image_url = ''
                    if 'media_content' in entry:
                        image_url = entry.media_content[0].get('url', '')
                    elif 'content' in entry:
                        soup = BeautifulSoup(entry.content[0].value, 'html.parser')
                        img = soup.find('img')
                        if img:
                            image_url = img.get('src', '')
                    
                    # Filter by search term relevance
                    if search_term.lower() in (title + summary).lower():
                        pins.append({
                            "title": title,
                            "description": summary[:200] if summary else f"Trending {search_term} recipe",
                            "image_url": image_url,
                            "pin_url": link,
                            "source": f"Pinterest RSS ({rss_url.split('/')[3]})"
                        })
                        
                        if len(pins) >= max_pins:
                            break
                            
                if len(pins) >= max_pins:
                    break
                    
            except Exception as e:
                logger.warning(f"RSS feed {rss_url} failed: {e}")
                continue
        
        return pins if pins else None
        
    except Exception as e:
        logger.error(f"RSS fallback failed: {e}")
        return None


def _generate_mock_data(search_term: str, max_pins: int = 10) -> list[dict]:
    """Generate mock data as final fallback."""
    logger.warning(f"Using mock data for: {search_term}")
    return [
        {
            "title": f"Trending {search_term} recipe",
            "description": f"Popular {search_term} pin with high engagement",
            "image_url": "https://via.placeholder.com/300x400",
            "pin_url": f"https://pinterest.com/pin/mock/{hash(search_term + str(i))}",
            "source": "Pinterest (mock data - fallback)"
        }
        for i in range(min(max_pins, 5))
    ]


def collect_trending_pins(query: str, max_pins: int = 10) -> tuple[list[dict], str]:
    """
    STEP 1: Collect trending Pinterest pins related to a query.
    
    Strategy:
    1. Try Playwright headless scraping first
    2. If Playwright fails/blocked, use RSS feedparser fallback
    3. If RSS fails, return mock data
    
    Args:
        query: Search query (recipe URL or name)
        max_pins: Maximum number of pins to collect
        
    Returns:
        Tuple of (list of pin dicts, source description)
    """
    search_term = _extract_keywords(query)
    
    if not search_term:
        return [], "No search term provided"
    
    logger.info(f"Collecting Pinterest trends for: {search_term}")
    
    # Try Playwright first
    pins = _scrape_with_playwright(search_term, max_pins)
    if pins:
        logger.info(f"Successfully scraped {len(pins)} pins with Playwright")
        return pins, f"Pinterest (Playwright): {search_term}"
    
    # Fallback to RSS
    logger.info("Playwright failed, trying RSS fallback")
    pins = _scrape_with_rss_fallback(search_term, max_pins)
    if pins:
        logger.info(f"Successfully scraped {len(pins)} pins from RSS feeds")
        return pins, f"Pinterest (RSS): {search_term}"
    
    # Final fallback: mock data
    pins = _generate_mock_data(search_term, max_pins)
    return pins, f"Pinterest (mock): {search_term}"
