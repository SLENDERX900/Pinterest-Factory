"""
utils/web_scraper.py
Web scraping utilities for extracting recipe information from food blog websites.
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import time
import xml.etree.ElementTree as ET

def scrape_recipes_from_website(base_url: str, max_recipes: int = 50) -> list[dict]:
    """
    Scrape recipe information from a food blog website using sitemap discovery.
    
    Args:
        base_url: The base URL of the food blog
        max_recipes: Maximum number of recipes to extract
        
    Returns:
        List of recipe dictionaries with name, url, time, ingredients, benefit
    """
    try:
        # Normalize base URL
        base_url = base_url.rstrip('/')
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Discovering sitemap for {domain}")
        
        # Step 1: Discover sitemap
        sitemap_urls = discover_sitemaps(domain, headers)
        if not sitemap_urls:
            print("No sitemap found, falling back to homepage scraping")
            return fallback_homepage_scraping(base_url, max_recipes, headers)
        
        print(f"Found {len(sitemap_urls)} sitemap(s)")
        
        # Step 2: Extract URLs from sitemaps
        all_urls = []
        for sitemap_url in sitemap_urls:
            urls = extract_urls_from_sitemap(sitemap_url, headers)
            all_urls.extend(urls)
        
        if not all_urls:
            print("No URLs found in sitemaps")
            return []
        
        print(f"Extracted {len(all_urls)} URLs from sitemaps")
        
        # Step 3: Take the most recent URLs (sitemaps are usually ordered by date)
        recent_urls = all_urls[:max_recipes * 2]  # Get more to account for non-recipes
        
        # Step 4: Iterative scraping with recipe validation
        recipes = []
        for url in recent_urls:
            if len(recipes) >= max_recipes:
                break
                
            try:
                recipe = extract_recipe_info_with_validation(url, headers)
                if recipe:
                    recipes.append(recipe)
                    print(f"✓ Found recipe: {recipe['name']}")
                time.sleep(1)  # Be respectful to the server
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
        
        print(f"Successfully extracted {len(recipes)} recipes")
        return recipes
        
    except Exception as e:
        print(f"Error scraping website {base_url}: {e}")
        return []

def discover_sitemaps(domain: str, headers: dict) -> list[str]:
    """
    Discover sitemap URLs for a domain.
    """
    sitemap_urls = []
    
    # Check robots.txt first
    robots_url = f"{domain}/robots.txt"
    try:
        response = requests.get(robots_url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text
            # Look for Sitemap directives
            for line in content.split('\n'):
                if line.startswith('Sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
    except Exception as e:
        print(f"Error checking robots.txt: {e}")
    
    # If no sitemaps found in robots.txt, try common locations
    if not sitemap_urls:
        common_sitemaps = [
            f"{domain}/sitemap.xml",
            f"{domain}/sitemap_index.xml",
            f"{domain}/sitemap_index.xml",
            f"{domain}/wp-sitemap.xml",
            f"{domain}/sitemap/sitemap-index.xml"
        ]
        
        for sitemap_url in common_sitemaps:
            try:
                response = requests.head(sitemap_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    sitemap_urls.append(sitemap_url)
                    break  # Found one, no need to check others
            except Exception:
                continue
    
    return sitemap_urls

def extract_urls_from_sitemap(sitemap_url: str, headers: dict) -> list[str]:
    """
    Extract URLs from a sitemap, handling nested sitemaps.
    """
    urls = []
    
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Check if this is a sitemap index or a regular sitemap
        if root.tag.endswith('sitemapindex'):
            # This is a sitemap index - find child sitemaps
            print(f"Parsing sitemap index: {sitemap_url}")
            child_sitemaps = []
            
            for child in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc = child.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    child_url = loc.text.strip()
                    # Prioritize sitemaps that likely contain recipes
                    if any(keyword in child_url.lower() for keyword in ['post', 'recipe', 'item', 'page']):
                        child_sitemaps.insert(0, child_url)  # High priority
                    else:
                        child_sitemaps.append(child_url)
            
            # Recursively extract from child sitemaps
            for child_sitemap in child_sitemaps[:10]:  # Limit to prevent infinite loops
                child_urls = extract_urls_from_sitemap(child_sitemap, headers)
                urls.extend(child_urls)
                
        elif root.tag.endswith('urlset'):
            # This is a regular sitemap with URLs
            print(f"Parsing URL sitemap: {sitemap_url}")
            for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    urls.append(loc.text.strip())
        
    except Exception as e:
        print(f"Error parsing sitemap {sitemap_url}: {e}")
    
    return urls

def extract_recipe_info_with_validation(url: str, headers: dict) -> dict:
    """
    Extract recipe information with schema validation.
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Step 1: Check for Recipe schema validation
        if not has_recipe_schema(soup):
            print(f"No recipe schema found on {url}")
            return None  # Not a recipe page
        
        # Step 2: Extract recipe information
        name = extract_recipe_name(soup)
        if name == "Unknown Recipe":
            print(f"Could not extract recipe name from {url}")
            # Debug: show available titles
            title_tag = soup.find('title')
            if title_tag:
                print(f"  Page title: {title_tag.get_text()}")
            h1_tag = soup.find('h1')
            if h1_tag:
                print(f"  H1 content: {h1_tag.get_text()}")
        
        time_info = extract_cooking_time(soup)
        ingredient_count = extract_ingredient_count(soup)
        benefit = determine_recipe_benefit(soup, name)
        
        return {
            'name': name,
            'url': url,
            'time': time_info,
            'ingredients': ingredient_count,
            'benefit': benefit
        }
        
    except Exception as e:
        print(f"Error extracting recipe info from {url}: {e}")
        return None

def has_recipe_schema(soup: BeautifulSoup) -> bool:
    """
    Check if the page contains Recipe schema data.
    """
    # Look for application/ld+json scripts
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            
            # Handle single schema or array of schemas
            if isinstance(data, list):
                schemas = data
            else:
                schemas = [data]
            
            for schema in schemas:
                if schema.get('@type') == 'Recipe':
                    return True
                
                # Check if Recipe is in a list of types
                schema_type = schema.get('@type')
                if isinstance(schema_type, list) and 'Recipe' in schema_type:
                    return True
                    
        except Exception:
            continue
    
    return False

def fallback_homepage_scraping(base_url: str, max_recipes: int, headers: dict) -> list[dict]:
    """
    Fallback method: scrape from homepage if no sitemap found.
    """
    try:
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        recipe_links = find_recipe_links(soup, base_url)
        
        recipes = []
        for link in recipe_links[:max_recipes]:
            try:
                recipe = extract_recipe_info_with_validation(link, headers)
                if recipe:
                    recipes.append(recipe)
                time.sleep(1)
            except Exception as e:
                continue
                
        return recipes
        
    except Exception as e:
        print(f"Error in fallback scraping: {e}")
        return []

def find_recipe_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """
    Find individual recipe links, filtering out categories and generic pages.
    """
    links = []
    
    # Generic category terms to exclude
    EXCLUDED_TERMS = [
        'all recipes', 'snacks recipes', 'mains recipes', 'desserts recipes',
        'soups recipes', 'breakfast recipes', 'sides recipes', 'appetizers',
        'main course', 'side dish', 'dessert', 'breakfast', 'lunch', 'dinner',
        'category', 'categories', 'collection', 'collections', 'index',
        'archive', 'archives', 'tag', 'tags', 'type', 'types'
    ]
    
    # More specific patterns for individual recipe URLs
    recipe_patterns = [
        r'/recipe[s]?/[\w-]+$',  # /recipes/dish-name
        r'/[\w-]+-recipe$',     # /dish-name-recipe
        r'/cook/[\w-]+$',       # /cook/dish-name
        r'/food/[\w-]+$',       # /food/dish-name
        r'/dishes/[\w-]+$',     # /dishes/dish-name
        r'/meals/[\w-]+$',       # /meals/dish-name
    ]
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        link_text = a_tag.get_text().strip().lower()
        full_url = urljoin(base_url, href)
        
        # Skip if link text contains excluded terms
        if any(excluded_term in link_text for excluded_term in EXCLUDED_TERMS):
            continue
        
        # Skip if link text is too short or too generic
        if len(link_text) < 3 or len(link_text.split()) > 8:
            continue
        
        # Check if it matches recipe URL patterns
        if any(re.search(pattern, href, re.IGNORECASE) for pattern in recipe_patterns):
            links.append(full_url)
        # Fallback: check if link text looks like a dish name
        elif looks_like_dish_name(link_text):
            links.append(full_url)
    
    # Remove duplicates
    return list(set(links))

def looks_like_dish_name(text: str) -> bool:
    """
    Determine if text looks like an actual dish name rather than a category.
    """
    # Common dish name indicators
    dish_indicators = [
        'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'tofu',
        'pasta', 'rice', 'noodles', 'soup', 'salad', 'sandwich', 'burger',
        'pizza', 'taco', 'curry', 'stir', 'roast', 'baked', 'grilled',
        'cake', 'pie', 'cookie', 'bread', 'muffin', 'pancake', 'waffle'
    ]
    
    # Category indicators to exclude
    category_indicators = [
        'recipes', 'recipe', 'dishes', 'dish', 'meals', 'meal', 'food',
        'ideas', 'collection', 'best', 'easy', 'quick', 'simple',
        'homemade', 'traditional', 'classic', 'favorite'
    ]
    
    # Must contain at least one dish indicator
    if not any(indicator in text for indicator in dish_indicators):
        return False
    
    # Must not contain category indicators
    if any(indicator in text for indicator in category_indicators):
        return False
    
    return True

def extract_recipe_info(url: str, headers: dict) -> dict:
    """
    Extract recipe information from a specific recipe page.
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract recipe name
        name = extract_recipe_name(soup)
        
        # Extract cooking time
        time_info = extract_cooking_time(soup)
        
        # Extract ingredient count
        ingredient_count = extract_ingredient_count(soup)
        
        # Determine benefit/category
        benefit = determine_recipe_benefit(soup, name)
        
        return {
            'name': name,
            'url': url,
            'time': time_info,
            'ingredients': ingredient_count,
            'benefit': benefit
        }
        
    except Exception as e:
        print(f"Error extracting recipe info from {url}: {e}")
        return None

def extract_recipe_name(soup: BeautifulSoup) -> str:
    """
    Extract recipe name with multiple fallback methods.
    """
    # Method 1: Try to extract from Recipe schema first
    schema_name = extract_name_from_schema(soup)
    if schema_name and is_valid_recipe_name(schema_name):
        return schema_name
    
    # Method 2: Try various HTML selectors
    selectors = [
        'h1',
        '.recipe-title',
        '.entry-title',
        '.post-title',
        '[itemprop="name"]',
        '.recipe-name',
        '.title',
        'h2',
        '.post-title entry-title',
        '.recipe-title h1',
        '.entry-content h1',
        '.recipe h1',
        '.wp-block-post-title',
        '.elementor-heading-title'
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            name = element.get_text().strip()
            # Clean up the name
            name = clean_recipe_name(name)
            if is_valid_recipe_name(name):
                return name
    
    # Method 3: Try to extract from page title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text().strip()
        # Remove common suffixes
        title = re.sub(r'\s*[-|]\s*.+$', '', title)  # Remove "| Site Name" 
        title = re.sub(r'\s*Recipe$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\-.*$', '', title)  # Remove " - anything"
        title = clean_recipe_name(title)
        if is_valid_recipe_name(title):
            return title
    
    # Method 4: Try to find recipe name in URL path
    url_element = soup.find('link', rel='canonical')
    if url_element:
        url = url_element.get('href', '')
        name_from_url = extract_name_from_url(url)
        if name_from_url:
            return name_from_url
    
    return "Unknown Recipe"

def extract_name_from_schema(soup: BeautifulSoup) -> str:
    """
    Extract recipe name from JSON-LD schema.
    """
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            
            # Handle single schema or array of schemas
            if isinstance(data, list):
                schemas = data
            else:
                schemas = [data]
            
            for schema in schemas:
                if schema.get('@type') == 'Recipe':
                    name = schema.get('name')
                    if name and isinstance(name, str):
                        return name.strip()
                
                # Check if Recipe is in a list of types
                schema_type = schema.get('@type')
                if isinstance(schema_type, list) and 'Recipe' in schema_type:
                    name = schema.get('name')
                    if name and isinstance(name, str):
                        return name.strip()
                        
        except Exception:
            continue
    
    return None

def clean_recipe_name(name: str) -> str:
    """
    Clean up recipe name by removing common artifacts.
    """
    if not name:
        return name
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^Recipe:\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*Recipe$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^How to Make\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Easy\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Simple\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Quick\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Homemade\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Best\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^Perfect\s*', '', name, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Remove common suffixes
    name = re.sub(r'\s*\|.*$', '', name)  # Remove "| anything"
    name = re.sub(r'\s*-.*$', '', name)   # Remove "- anything"
    
    return name

def extract_name_from_url(url: str) -> str:
    """
    Extract recipe name from URL path.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Split path and get the last segment
        segments = path.split('/')
        if segments:
            last_segment = segments[-1]
            # Convert hyphens to spaces and capitalize
            name = last_segment.replace('-', ' ').replace('_', ' ')
            name = ' '.join(word.capitalize() for word in name.split())
            return name
    except Exception:
        pass
    
    return None

def extract_nutrition_facts(soup: BeautifulSoup) -> dict:
    """
    Extract nutrition facts from recipe page.
    """
    nutrition_facts = {}
    
    # Look for structured nutrition data
    nutrition_selectors = [
        '[itemprop="nutrition"]',
        '.nutrition-facts',
        '.recipe-nutrition',
        '.nutrition-info',
        '[itemprop="calories"]',
        '[itemprop="protein"]',
        '[itemprop="carbohydrateContent"]',
        '[itemprop="fatContent"]'
    ]
    
    for selector in nutrition_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text().strip()
            # Parse nutrition values
            if 'calories' in selector:
                nutrition_facts['calories'] = extract_number(text)
            elif 'protein' in selector:
                nutrition_facts['protein'] = extract_number(text)
            elif 'carbohydrate' in selector:
                nutrition_facts['carbs'] = extract_number(text)
            elif 'fat' in selector:
                nutrition_facts['fat'] = extract_number(text)
    
    # Look for common nutrition patterns in text
    page_text = soup.get_text().lower()
    
    # Calorie patterns
    calorie_patterns = [
        r'(\d+)\s*calories?',
        r'(\d+)\s*kcal?',
        r'calories?\s*(\d+)',
        r'energy\s*(\d+)'
    ]
    
    for pattern in calorie_patterns:
        match = re.search(pattern, page_text)
        if match:
            nutrition_facts['calories'] = extract_number(match.group(1))
            break
    
    # Protein patterns
    protein_patterns = [
        r'(\d+)\s*g\s*protein?',
        r'protein\s*(\d+)\s*g',
        r'protein\s*(\d+)',
        r'high protein\s*(\d+)'
    ]
    
    for pattern in protein_patterns:
        match = re.search(pattern, page_text)
        if match:
            nutrition_facts['protein'] = extract_number(match.group(1))
            break
    
    # Carb patterns
    carb_patterns = [
        r'(\d+)\s*g\s*carbs?',
        r'carbohydrate\s*(\d+)',
        r'carbs?\s*(\d+)',
        r'net carbs\s*(\d+)',
        r'total carbs\s*(\d+)'
    ]
    
    for pattern in carb_patterns:
        match = re.search(pattern, page_text)
        if match:
            nutrition_facts['carbs'] = extract_number(match.group(1))
            break
    
    # Fat patterns
    fat_patterns = [
        r'(\d+)\s*g\s*fat?',
        r'fat\s*(\d+)\s*g',
        r'fat\s*(\d+)',
        r'total fat\s*(\d+)'
    ]
    
    for pattern in fat_patterns:
        match = re.search(pattern, page_text)
        if match:
            nutrition_facts['fat'] = extract_number(match.group(1))
            break
    
    # Time-based estimates (when no explicit nutrition found)
    if not nutrition_facts.get('calories') and 'minute' in page_text:
        # Estimate calories based on cooking time (rough estimate)
        time_match = re.search(r'(\d+)\s*minutes?', page_text)
        if time_match:
            estimated_calories = int(time_match.group(1)) * 8  # Rough estimate: 8 cal/min
            nutrition_facts['calories'] = str(estimated_calories)
    
    return nutrition_facts

def extract_number(text: str) -> str:
    """
    Extract numeric value from text.
    """
    match = re.search(r'(\d+)', text)
    if match:
        return match.group(1)
    return None

def is_valid_recipe_name(name: str) -> bool:
    """
    Validate that the extracted name is actually a recipe name.
    """
    name = name.strip()
    
    # Exclude generic terms
    excluded_terms = [
        'all recipes', 'recipes', 'recipe collection', 'recipe index',
        'category', 'categories', 'archives', 'recent', 'popular',
        'breakfast recipes', 'dinner ideas', 'lunch recipes',
        'dessert recipes', 'snack recipes', 'main dishes'
    ]
    
    name_lower = name.lower()
    if any(excluded in name_lower for excluded in excluded_terms):
        return False
    
    # Must be reasonable length
    if len(name) < 3 or len(name) > 100:
        return False
    
    # Should contain at least one food-related word
    food_words = [
        'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'tofu',
        'pasta', 'rice', 'noodles', 'soup', 'salad', 'sandwich', 'burger',
        'pizza', 'taco', 'curry', 'stew', 'roast', 'baked', 'grilled',
        'cake', 'pie', 'cookie', 'bread', 'muffin', 'pancake', 'waffle',
        'chocolate', 'vanilla', 'strawberry', 'apple', 'banana',
        'potato', 'tomato', 'onion', 'garlic', 'cheese', 'egg'
    ]
    
    return any(food_word in name_lower for food_word in food_words)

def extract_cooking_time(soup: BeautifulSoup) -> str:
    """
    Extract cooking time - more accurate version that avoids false positives.
    """
    # Method 1: Try structured data (most reliable)
    time_selectors = [
        ('[itemprop="totalTime"]', 'total'),
        ('[itemprop="cookTime"]', 'cook'),
        ('[itemprop="prepTime"]', 'prep'),
        ('.recipe-time', 'total'),
        ('.cook-time', 'cook'),
        ('.prep-time', 'prep'),
        ('.recipe-details-time', 'total'),
        ('.duration', 'total')
    ]
    
    for selector, time_type in time_selectors:
        element = soup.select_one(selector)
        if element:
            time_text = element.get_text().strip()
            time = parse_iso_duration(time_text)
            if time and time != "1 mins":  # Avoid suspicious 1-minute times
                print(f"Found {time_type} time: {time} using selector: {selector}")
                return time
    
    # Method 2: Look for time in meta tags
    meta_selectors = [
        'meta[itemprop="cookTime"]',
        'meta[itemprop="totalTime"]',
        'meta[itemprop="prepTime"]'
    ]
    
    for meta in soup.select(','.join(meta_selectors)):
        content = meta.get('content', '')
        time = parse_iso_duration(content)
        if time and time != "1 mins":
            return time
    
    # Method 3: Extract from JSON-LD schema (most reliable)
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, list):
                schemas = data
            else:
                schemas = [data]
            
            for schema in schemas:
                if schema.get('@type') == 'Recipe' or (isinstance(schema.get('@type'), list) and 'Recipe' in schema.get('@type', [])):
                    # Try totalTime first, then cookTime, then prepTime
                    for time_field in ['totalTime', 'cookTime', 'prepTime']:
                        time_value = schema.get(time_field)
                        if time_value:
                            time = parse_iso_duration(time_value)
                            if time and time != "1 mins":
                                print(f"Found {time_field}: {time} from JSON-LD schema")
                                return time
        except:
            pass
    
    # Method 4: Search for time in page text with stricter patterns
    page_text = soup.get_text()
    
    # Look for recipe time patterns (avoiding false positives like "1" being extracted from other contexts)
    strict_patterns = [
        # Look for "X minutes" or "X hours" near recipe-related words
        r'(?:prep|cook|total|ready in)\s*(?:time)?[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'(?:prep|cook|total)\s*(?:time)?[:\s]*(?:about|around)?\s*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'(?:time required|time needed)[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'(?:takes|needs)\s*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)\s*(?:to\s*cook|to\s*prep|total)',
    ]
    
    for pattern in strict_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            number = int(match.group(1))
            # Sanity check - recipes shouldn't take less than 5 minutes or more than 24 hours
            if 5 <= number <= 1440:
                # Determine unit
                match_text = match.group(0).lower()
                if 'hr' in match_text or 'hour' in match_text:
                    if number == 1:
                        return "1 hr"
                    else:
                        return f"{number} hrs"
                else:
                    if number == 1:
                        return "1 min"
                    else:
                        return f"{number} mins"
    
    # Return empty string if we can't determine accurately
    print("Could not accurately determine cooking time")
    return ""

def parse_iso_duration(duration_text: str) -> str:
    """
    Parse ISO 8601 duration format (e.g., PT30M, PT1H30M) to human-readable format.
    Also handles plain text like "30 minutes", "1 hour", etc.
    """
    if not duration_text:
        return None
    
    duration_text = duration_text.strip().upper()
    
    # Check for ISO 8601 format (PT30M, PT1H30M, etc.)
    iso_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:\d+S)?', duration_text)
    if iso_match:
        hours = int(iso_match.group(1)) if iso_match.group(1) else 0
        minutes = int(iso_match.group(2)) if iso_match.group(2) else 0
        
        if hours > 0 and minutes > 0:
            return f"{hours} hr {minutes} mins"
        elif hours > 0:
            if hours == 1:
                return "1 hr"
            else:
                return f"{hours} hrs"
        elif minutes > 0:
            if minutes == 1:
                return "1 min"
            else:
                return f"{minutes} mins"
    
    # Parse plain text format
    # Look for patterns like "30 minutes", "1 hour", "2 hours 30 minutes"
    hour_match = re.search(r'(\d+)\s*(?:hr|hrs|hour|hours)', duration_text, re.IGNORECASE)
    minute_match = re.search(r'(\d+)\s*(?:min|mins|minute|minutes)', duration_text, re.IGNORECASE)
    
    hours = int(hour_match.group(1)) if hour_match else 0
    minutes = int(minute_match.group(1)) if minute_match else 0
    
    if hours > 0 and minutes > 0:
        return f"{hours} hr {minutes} mins"
    elif hours > 0:
        if hours == 1:
            return "1 hr"
        else:
            return f"{hours} hrs"
    elif minutes > 0:
        if minutes == 1:
            return "1 min"
        else:
            return f"{minutes} mins"
    
    return None

def parse_time_from_text(time_text: str) -> str:
    """
    Parse time from various text formats.
    """
    # Handle different time formats
    time_patterns = [
        r'(\d+)\s*hr',
        r'(\d+)\s*hrs?',
        r'(\d+)\s*hour',
        r'(\d+)\s*mins?',
        r'(\d+)\s*minutes?',
        r'(\d+)\s*min'
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, time_text)
        if match:
            return match.group(0)
    
    return None

def extract_ingredient_count(soup: BeautifulSoup) -> str:
    """
    Extract ingredient count from recipe page - more accurate version.
    """
    # Method 1: Look for structured ingredient lists - most reliable
    ingredient_selectors = [
        '.ingredients li',
        '.ingredient-list li',
        '[itemprop="recipeIngredient"]',
        '.recipe-ingredients li',
        '.ingredients-list li',
        '.recipe-ingredients ul li',
        '.wp-block-ingredients-list li',
        '.tasty-recipes-ingredients li',
        '.recipe-ingredients ol li',
        '.ingredient-group li',
        '.wprm-recipe-ingredient',
        '.tasty-recipes-ingredients-body li'
    ]
    
    for selector in ingredient_selectors:
        ingredients = soup.select(selector)
        if len(ingredients) > 0 and len(ingredients) < 50:  # Sanity check - recipes shouldn't have 50+ ingredients
            # Verify these are actually ingredients by checking content
            valid_ingredients = []
            for ing in ingredients:
                text = ing.get_text().strip()
                # Ingredient should have some substance and likely contain a measurement or ingredient word
                if len(text) > 3 and len(text) < 200:
                    # Check for measurement indicators
                    has_measurement = any(unit in text.lower() for unit in ['cup', 'tbsp', 'tsp', 'oz', 'lb', 'g', 'kg', 'ml', 'tablespoon', 'teaspoon', 'pound', 'ounce', 'gram'])
                    # Or check for common ingredient words
                    has_ingredient = any(word in text.lower() for word in ['salt', 'pepper', 'oil', 'butter', 'garlic', 'onion', 'flour', 'sugar', 'egg', 'milk', 'water', 'chicken', 'beef', 'cheese', 'pasta', 'rice', 'vegetable'])
                    if has_measurement or has_ingredient:
                        valid_ingredients.append(text)
            
            if len(valid_ingredients) > 0:
                print(f"Found {len(valid_ingredients)} valid ingredients using selector: {selector}")
                return str(len(valid_ingredients))
    
    # Method 2: Look for ingredient section and count items
    page_text = soup.get_text()
    
    # Find the ingredients section
    ingredient_section_patterns = [
        r'(?i)ingredients[\s:]*\n((?:\s*[-•\d\.]\s*[^\n]+\n?)+)',
        r'(?i)what you[\'\']?ll need[\s:]*\n((?:\s*[-•\d\.]\s*[^\n]+\n?)+)',
        r'(?i)you will need[\s:]*\n((?:\s*[-•\d\.]\s*[^\n]+\n?)+)'
    ]
    
    for pattern in ingredient_section_patterns:
        match = re.search(pattern, page_text)
        if match:
            section = match.group(1)
            # Count lines that look like ingredients (start with bullet, number, or have measurements)
            lines = [line.strip() for line in section.split('\n') if line.strip()]
            ingredient_lines = []
            for line in lines:
                # Check if line looks like an ingredient
                if re.match(r'^[\s•\-\*\d\.]+', line) or any(unit in line.lower() for unit in ['cup', 'tbsp', 'tsp', 'oz', 'lb', 'g ', 'ml', 'tablespoon', 'teaspoon', 'pound']):
                    if len(line) > 3 and len(line) < 200:
                        ingredient_lines.append(line)
            
            if len(ingredient_lines) > 0:
                print(f"Found {len(ingredient_lines)} ingredients from section pattern")
                return str(len(ingredient_lines))
    
    # Method 3: Extract from JSON-LD schema
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, list):
                schemas = data
            else:
                schemas = [data]
            
            for schema in schemas:
                if schema.get('@type') == 'Recipe' or (isinstance(schema.get('@type'), list) and 'Recipe' in schema.get('@type', [])):
                    recipe_ingredients = schema.get('recipeIngredient', [])
                    if recipe_ingredients and len(recipe_ingredients) > 0:
                        print(f"Found {len(recipe_ingredients)} ingredients from JSON-LD schema")
                        return str(len(recipe_ingredients))
        except:
            pass
    
    # Default - return empty to indicate extraction failed rather than guessing
    print("Could not accurately determine ingredient count")
    return ""

def determine_recipe_benefit(soup: BeautifulSoup, recipe_name: str) -> str:
    """
    Determine recipe benefit/category based on content and name.
    """
    name_lower = recipe_name.lower()
    page_text = soup.get_text().lower()
    
    # Define benefit categories with keywords
    benefits = {
        "Quick Weeknight": ["quick", "fast", "easy", "simple", "weeknight", "busy"],
        "High Protein": ["protein", "chicken", "beef", "fish", "meat", "tofu"],
        "Budget Friendly": ["budget", "cheap", "affordable", "economical"],
        "Vegan": ["vegan", "plant-based", "dairy-free"],
        "Vegetarian": ["vegetarian", "meatless", "meat-free"],
        "Healthy": ["healthy", "light", "low-fat", "nutritious"],
        "Comfort Food": ["comfort", "cozy", "hearty", "warm"],
        "One Pan": ["one pan", "one-pot", "single pan"],
        "Meal Prep": ["meal prep", "make-ahead", "batch"],
        "Spicy": ["spicy", "hot", "chili", "pepper"],
        "Date Night": ["romantic", "date", "special", "elegant"]
    }
    
    # Check name first
    for benefit, keywords in benefits.items():
        if any(keyword in name_lower for keyword in keywords):
            return benefit
    
    # Then check page content
    for benefit, keywords in benefits.items():
        if any(keyword in page_text for keyword in keywords):
            return benefit
    
    # Default fallback
    return "Quick Weeknight"

def validate_url(url: str) -> bool:
    """
    Validate if the URL is properly formatted.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
