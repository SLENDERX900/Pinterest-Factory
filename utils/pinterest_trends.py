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
    """Extract search keywords from URL or query string, excluding website names."""
    if query.startswith('http'):
        # Extract keywords from URL path
        keywords = re.sub(r'[^\w\s-]', ' ', query).split()
        
        # Filter out common non-recipe terms and website names
        exclude_terms = [
            'http', 'https', 'www', 'com', 'recipe', 'recipes',
            'nobscooking', 'tasty', 'buzzfeedtasty', 'food', 'blog',
            'cooking', 'kitchen', 'chef', 'dinner', 'lunch', 'breakfast'
        ]
        
        # Keep only recipe-relevant keywords
        recipe_keywords = []
        for k in keywords:
            k_lower = k.lower()
            if (len(k) > 2 and 
                k_lower not in exclude_terms and 
                not k_lower.endswith('.com') and
                not k_lower.endswith('.net') and
                not k_lower.endswith('.org')):
                recipe_keywords.append(k)
        
        return ' '.join(recipe_keywords[:5])
    return query


# Global flag to track installation status
_playwright_installing = False
_playwright_ready = False
_playwright_install_output = []  # Store installation output

def _install_playwright_if_needed():
    """Force install Playwright synchronously to ensure it works."""
    global _playwright_installing, _playwright_ready
    
    import subprocess
    import sys
    from pathlib import Path
    
    print("PLAYWRIGHT DEBUG: Starting synchronous installation...", flush=True)
    
    # Install playwright package
    print("PLAYWRIGHT DEBUG: Installing playwright package...", flush=True)
    result = subprocess.run(
        ["pip", "install", "playwright"],
        capture_output=True,
        text=True,
        timeout=120
    )
    print(f"PLAYWRIGHT DEBUG: Package install result: {result.returncode}", flush=True)
    if result.stderr:
        print(f"PLAYWRIGHT DEBUG: Package stderr: {result.stderr}", flush=True)
    
    # Install browsers synchronously 
    print("PLAYWRIGHT DEBUG: Installing browsers synchronously...", flush=True)
    result = subprocess.run(
        ["python", "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes
    )
    print(f"PLAYWRIGHT DEBUG: Browser install result: {result.returncode}", flush=True)
    if result.stdout:
        print(f"PLAYWRIGHT DEBUG: Browser stdout: {result.stdout}", flush=True)
    if result.stderr:
        print(f"PLAYWRIGHT DEBUG: Browser stderr: {result.stderr}", flush=True)
    
    # Check if installation succeeded
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    if cache_dir.exists() and list(cache_dir.glob("chromium*")):
        _playwright_ready = True
        print("PLAYWRIGHT DEBUG: Installation successful!", flush=True)
        return True
    else:
        print("PLAYWRIGHT DEBUG: Installation failed!", flush=True)
        return False


def _scrape_with_playwright(search_term: str, max_pins: int = 10) -> Optional[list[dict]]:
    """
    Use Playwright to scrape Pinterest search results.
    Returns None if Playwright fails or is not available.
    """
    import sys
    
    print(f"PLAYWRIGHT DEBUG: _scrape_with_playwright called for '{search_term}'", flush=True)
    print(f"PLAYWRIGHT DEBUG: _playwright_ready = {_playwright_ready}", flush=True)
    print(f"PLAYwright_installing = {_playwright_installing}", flush=True)
    
    # Check if browsers are actually installed
    from pathlib import Path
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    print(f"PLAYWRIGHT DEBUG: Browser cache exists: {cache_dir.exists()}", flush=True)
    if cache_dir.exists():
        chromium_dirs = list(cache_dir.glob("chromium*"))
        print(f"PLAYWRIGHT DEBUG: Found {len(chromium_dirs)} chromium directories", flush=True)
        for d in chromium_dirs:
            print(f"PLAYWRIGHT DEBUG: Chromium dir: {d}", flush=True)
    
    # Try to import playwright to see if it's actually available
    try:
        import playwright
        print("PLAYWRIGHT DEBUG: Playwright import successful", flush=True)
    except ImportError as e:
        print(f"PLAYWRIGHT DEBUG: Playwright import failed: {e}", flush=True)
    
    # Check if Playwright is ready
    if not _playwright_ready:
        print("PLAYWRIGHT DEBUG: Not ready, triggering installation...", flush=True)
        # Force re-check installation status
        _install_playwright_if_needed()
        
        # Wait a bit for installation to complete
        import time
        for i in range(10):  # Wait up to 5 seconds
            time.sleep(0.5)
            if _playwright_ready:
                print(f"PLAYWRIGHT DEBUG: Installation completed after {i*0.5}s!", flush=True)
                break
        
        if not _playwright_ready:
            print("PLAYWRIGHT DEBUG: Installation still not ready, returning None", flush=True)
            return None
    
    print("PLAYWRIGHT DEBUG: Ready to scrape, importing playwright...", flush=True)
    
    try:
        from playwright.sync_api import sync_playwright
        print("PLAYWRIGHT DEBUG: Successfully imported sync_playwright", flush=True)
        
        pins = []
        search_url = f"https://www.pinterest.com/search/pins/?q={requests.utils.quote(search_term)}"
        
        print("PLAYWRIGHT DEBUG: Launching Chromium browser...", flush=True)
        
        with sync_playwright() as p:
            # Launch browser with stealth options
            print("PLAYWRIGHT DEBUG: Creating browser instance...", flush=True)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors-spki-list'
                ]
            )
            print("PLAYWRIGHT DEBUG: Browser launched successfully", flush=True)
            print("PLAYWRIGHT DEBUG: Creating stealth context...", flush=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            # Add stealth scripts to avoid detection
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                window.chrome = {
                    runtime: {},
                };
            """)
            print("PLAYWRIGHT DEBUG: Stealth context created", flush=True)
            print("PLAYWRIGHT DEBUG: Context created, creating page...", flush=True)
            page = context.new_page()
            print("PLAYWRIGHT DEBUG: Page created, navigating to Pinterest...", flush=True)
            
            # Navigate to Pinterest home page first, then search
            print("PLAYWRIGHT DEBUG: Navigating to Pinterest home page first...", flush=True)
            page.goto("https://www.pinterest.com", wait_until='domcontentloaded', timeout=60000)
            print("PLAYWRIGHT DEBUG: Home page loaded, navigating to search...", flush=True)
            
            # Wait a bit to look more human
            import time
            time.sleep(2)
            
            # Now navigate to search
            print(f"PLAYWRIGHT DEBUG: Navigating to: {search_url}", flush=True)
            page.goto(search_url, wait_until='domcontentloaded', timeout=120000)  # 2 minutes
            print("PLAYWRIGHT DEBUG: Search page loaded", flush=True)
            
            # Wait for pins to load with multiple selectors
            print("PLAYWRIGHT DEBUG: Waiting for pins to load...", flush=True)
            try:
                page.wait_for_selector('[data-test-id="pin"]', timeout=30000)
            except:
                try:
                    page.wait_for_selector('.Pin', timeout=30000)
                except:
                    try:
                        page.wait_for_selector('[data-testid="pin-wrapper"]', timeout=30000)
                    except:
                        print("PLAYWRIGHT DEBUG: No pin selectors found, trying alternative approach", flush=True)
                        # Wait for any content to load
                        time.sleep(5)
            
            # Scroll to load more pins
            for _ in range(3):
                page.evaluate('window.scrollBy(0, 800)')
                time.sleep(random.uniform(0.5, 1.5))
            
            print("PLAYWRIGHT DEBUG: Extracting pin data...", flush=True)
            pin_elements = page.query_selector_all('[data-test-id="pin"] || .Pin || [data-testid="pin-wrapper"]')
            print(f"PLAYWRIGHT DEBUG: Found {len(pin_elements)} pin elements", flush=True)
            
            print(f"PLAYWRIGHT DEBUG: Processing {min(len(pin_elements), max_pins)} pins...", flush=True)
            
            for i, element in enumerate(pin_elements[:max_pins]):
                try:
                    print(f"PLAYWRIGHT DEBUG: Processing pin {i+1}/{min(len(pin_elements), max_pins)}", flush=True)
                    
                    # Extract title
                    title_elem = element.query_selector('img')
                    title = title_elem.get_attribute('alt') if title_elem else search_term
                    print(f"PLAYWRIGHT DEBUG: Extracted title: {title[:50]}...", flush=True)
                    
                    # Extract image URL
                    img_elem = element.query_selector('img')
                    image_url = img_elem.get_attribute('src') if img_elem else ''
                    print(f"PLAYWRIGHT DEBUG: Extracted image URL: {image_url[:50]}...", flush=True)
                    
                    # Extract description (from title or alt text)
                    desc_elem = element.query_selector('[data-test-id="pin-title"]')
                    description = desc_elem.text_content() if desc_elem else title
                    print(f"PLAYWRIGHT DEBUG: Extracted description: {description[:50]}...", flush=True)
                    
                    pins.append({
                        'title': title,
                        'description': description,
                        'image_url': image_url,
                        'source': 'pinterest'
                    })
                    print(f"PLAYWRIGHT DEBUG: Pin {i+1} added successfully", flush=True)
                except Exception as e:
                    print(f"PLAYWRIGHT DEBUG: Error processing pin {i+1}: {e}", flush=True)
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
        print(f"PINTEREST DEBUG: Sending {len(pins)} pins to Groq", flush=True)
        print(f"PINTEREST DEBUG: Sample pin data: {pins[0] if pins else 'None'}", flush=True)
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
