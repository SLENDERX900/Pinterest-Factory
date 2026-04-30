"""
utils/pinterest_scraper.py - Pinterest Scraping Engine with RSS Fallback
Implements Playwright-based Pinterest scraping with RSS fallback mechanism
"""

import asyncio
import feedparser
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import time
import json

class PinterestScraper:
    """
    Pinterest scraping engine with Playwright primary and RSS fallback
    """
    
    def __init__(self):
        self.rss_feeds = [
            "https://www.pinterest.com/feed.rss",  # General Pinterest feed
            # Add competitor feeds here
            "https://www.pinterest.com/foodnetwork/feed.rss",
            "https://www.pinterest.com/bonappetitmag/feed.rss",
            "https://www.pinterest.com/seriouseats/feed.rss",
        ]
        
    async def scrape_pinterest_pins(self, recipe_url: str, max_pins: int = 10) -> List[Dict]:
        """
        Main scraping method - tries Playwright first, falls back to RSS
        """
        print(f"🔍 Starting Pinterest scraping for: {recipe_url}")
        
        # Extract keywords from recipe URL
        keywords = self._extract_keywords_from_url(recipe_url)
        print(f"📝 Extracted keywords: {keywords}")
        
        # Try Playwright first
        try:
            print("🎭 Attempting Playwright scraping...")
            pins = await self._scrape_with_playwright(keywords, max_pins)
            if pins:
                print(f"✅ Playwright successful: {len(pins)} pins scraped")
                return pins
        except Exception as e:
            print(f"❌ Playwright failed: {e}")
        
        # Fallback to RSS
        print("📡 Falling back to RSS scraping...")
        pins = self._scrape_with_rss(max_pins)
        print(f"✅ RSS fallback: {len(pins)} pins scraped")
        
        return pins
    
    def _extract_keywords_from_url(self, url: str) -> List[str]:
        """Extract relevant keywords from recipe URL for Pinterest search"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Common recipe keywords
        recipe_keywords = [
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'tofu',
            'pasta', 'rice', 'noodles', 'soup', 'salad', 'sandwich', 'burger',
            'pizza', 'taco', 'curry', 'stew', 'roast', 'baked', 'grilled',
            'cake', 'pie', 'cookie', 'bread', 'muffin', 'pancake', 'waffle',
            'chocolate', 'vanilla', 'strawberry', 'apple', 'banana',
            'potato', 'tomato', 'onion', 'garlic', 'cheese', 'egg',
            'dinner', 'lunch', 'breakfast', 'dessert', 'snack', 'appetizer'
        ]
        
        keywords = []
        for keyword in recipe_keywords:
            if keyword in path:
                keywords.append(keyword)
        
        # If no keywords found, use generic terms
        if not keywords:
            keywords = ['recipe', 'food', 'cooking']
        
        return keywords[:3]  # Limit to top 3 keywords
    
    async def _scrape_with_playwright(self, keywords: List[str], max_pins: int) -> List[Dict]:
        """Scrape Pinterest using Playwright (headless browser)"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Search Pinterest with keywords
                search_query = " ".join(keywords)
                search_url = f"https://www.pinterest.com/search/pins/?q={search_query}"
                
                print(f"🌐 Navigating to: {search_url}")
                await page.goto(search_url, wait_until='networkidle')
                await page.wait_for_timeout(3000)  # Wait for content to load
                
                # Extract pin data
                pins = []
                pin_selectors = await page.query_selector_all('[data-test-id="pin-wrapper"]')
                
                for i, pin_element in enumerate(pin_selectors[:max_pins]):
                    try:
                        pin_data = await self._extract_pin_data(page, pin_element)
                        if pin_data:
                            pins.append(pin_data)
                            print(f"📌 Extracted pin {i+1}: {pin_data.get('title', 'No title')[:30]}...")
                    except Exception as e:
                        print(f"⚠️ Error extracting pin {i+1}: {e}")
                        continue
                
                await browser.close()
                return pins
                
        except ImportError:
            print("❌ Playwright not installed. Install with: pip install playwright")
            return []
        except Exception as e:
            print(f"❌ Playwright scraping error: {e}")
            return []
    
    async def _extract_pin_data(self, page, pin_element) -> Optional[Dict]:
        """Extract individual pin data from Pinterest page element"""
        try:
            # Extract title
            title_element = await pin_element.query_selector('[data-test-id="pin-title"]')
            title = await title_element.inner_text() if title_element else ""
            
            # Extract description
            desc_element = await pin_element.query_selector('[data-test-id="pin-description"]')
            description = await desc_element.inner_text() if desc_element else ""
            
            # Extract image URL
            img_element = await pin_element.query_selector('img')
            image_url = await img_element.get_attribute('src') if img_element else ""
            
            # Extract pin URL
            link_element = await pin_element.query_selector('a')
            pin_url = await link_element.get_attribute('href') if link_element else ""
            if pin_url and not pin_url.startswith('http'):
                pin_url = urljoin("https://www.pinterest.com", pin_url)
            
            # Extract save count (engagement metric)
            save_element = await pin_element.query_selector('[data-test-id="pin-save-count"]')
            saves = await save_element.inner_text() if save_element else "0"
            
            return {
                'title': title.strip(),
                'description': description.strip(),
                'image_url': image_url,
                'pin_url': pin_url,
                'saves': saves,
                'source': 'playwright',
                'scraped_at': time.time()
            }
            
        except Exception as e:
            print(f"❌ Error extracting pin data: {e}")
            return None
    
    def _scrape_with_rss(self, max_pins: int) -> List[Dict]:
        """Scrape Pinterest using RSS feeds as fallback"""
        all_pins = []
        
        for feed_url in self.rss_feeds:
            try:
                print(f"📡 Parsing RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:max_pins]:
                    pin_data = self._extract_rss_entry(entry)
                    if pin_data:
                        all_pins.append(pin_data)
                
                if all_pins:
                    break  # Got pins from first successful feed
                    
            except Exception as e:
                print(f"❌ RSS feed error for {feed_url}: {e}")
                continue
        
        return all_pins[:max_pins]
    
    def _extract_rss_entry(self, entry) -> Optional[Dict]:
        """Extract pin data from RSS entry"""
        try:
            # Extract title and description
            title = getattr(entry, 'title', '')
            description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
            
            # Extract image URL from description
            image_url = ""
            if description:
                # Look for image URLs in description
                img_match = re.search(r'<img[^>]+src="([^"]+)"', description)
                if img_match:
                    image_url = img_match.group(1)
            
            # Extract link
            pin_url = getattr(entry, 'link', '')
            
            # Clean description (remove HTML tags)
            clean_desc = re.sub(r'<[^>]+>', '', description)
            clean_desc = clean_desc.strip()
            
            return {
                'title': title.strip(),
                'description': clean_desc[:200],  # Limit length
                'image_url': image_url,
                'pin_url': pin_url,
                'saves': 'RSS',  # RSS doesn't provide save counts
                'source': 'rss',
                'scraped_at': time.time()
            }
            
        except Exception as e:
            print(f"❌ Error extracting RSS entry: {e}")
            return None

# Convenience function for async usage
async def scrape_pinterest_trends(recipe_url: str, max_pins: int = 10) -> List[Dict]:
    """
    Convenience function to scrape Pinterest trends
    """
    scraper = PinterestScraper()
    return await scraper.scrape_pinterest_pins(recipe_url, max_pins)

# Synchronous wrapper for easier integration
def scrape_pinterest_trends_sync(recipe_url: str, max_pins: int = 10) -> List[Dict]:
    """
    Synchronous wrapper for Pinterest scraping
    """
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(scrape_pinterest_trends(recipe_url, max_pins))
    except Exception as e:
        print(f"❌ Pinterest scraping failed: {e}")
        return []
