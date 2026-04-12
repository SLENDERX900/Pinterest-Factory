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
    Extract recipe information with schema validation and extraction memory.
    """
    # Initialize extraction memory for this URL
    extraction_memory = {
        'url': url,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'schema_found': False,
        'extraction_steps': [],
        'raw_data_found': {},
        'final_values': {},
        'errors': []
    }
    
    def log_step(step_name: str, details: dict):
        """Log an extraction step with details."""
        extraction_memory['extraction_steps'].append({
            'step': step_name,
            'timestamp': time.strftime('%H:%M:%S'),
            'details': details
        })
    
    try:
        log_step('http_request', {'status': 'started', 'url': url})
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        log_step('http_request', {'status': 'success', 'status_code': response.status_code, 'content_length': len(response.content)})
        
        soup = BeautifulSoup(response.content, 'html.parser')
        log_step('html_parse', {'status': 'success', 'parser_used': 'html.parser'})
        
        # Step 1: Check for Recipe schema validation
        schema_found = has_recipe_schema(soup)
        extraction_memory['schema_found'] = schema_found
        log_step('schema_validation', {'schema_found': schema_found})
        
        if not schema_found:
            log_step('extraction_aborted', {'reason': 'No recipe schema found'})
            print(f"No recipe schema found on {url}")
            return None
        
        # Step 2: Extract recipe name
        log_step('extract_name', {'status': 'started'})
        name = extract_recipe_name(soup, memory=extraction_memory)
        extraction_memory['final_values']['name'] = name
        log_step('extract_name', {
            'status': 'completed', 
            'value': name,
            'method_used': extraction_memory.get('name_method_used', 'unknown'),
            'tried_methods': len(extraction_memory.get('name_extraction_log', []))
        })
        
        if name == "Unknown Recipe":
            # Document what we tried
            title_tag = soup.find('title')
            h1_tag = soup.find('h1')
            h2_tags = soup.find_all('h2')[:3]
            extraction_memory['raw_data_found']['page_title'] = title_tag.get_text() if title_tag else None
            extraction_memory['raw_data_found']['h1_content'] = h1_tag.get_text() if h1_tag else None
            extraction_memory['raw_data_found']['h2_contents'] = [h.get_text() for h in h2_tags]
            log_step('extract_name_failed', {
                'extraction_log': extraction_memory.get('name_extraction_log', []),
                'all_methods_tried': [log.get('method') for log in extraction_memory.get('name_extraction_log', [])]
            })
        
        # Step 3: Extract times
        log_step('extract_times', {'status': 'started'})
        prep_time, cook_time, total_time = extract_recipe_times(soup)
        extraction_memory['final_values']['prep_time'] = prep_time
        extraction_memory['final_values']['cook_time'] = cook_time
        extraction_memory['final_values']['total_time'] = total_time
        log_step('extract_times', {
            'status': 'completed',
            'prep_time': prep_time,
            'cook_time': cook_time,
            'total_time': total_time
        })
        
        # Step 4: Extract ingredient count
        log_step('extract_ingredients', {'status': 'started'})
        ingredient_count = extract_ingredient_count(soup)
        extraction_memory['final_values']['ingredients'] = ingredient_count
        log_step('extract_ingredients', {'status': 'completed', 'value': ingredient_count})
        
        # Step 5: Determine benefit
        log_step('determine_benefit', {'status': 'started', 'recipe_name': name})
        benefit = determine_recipe_benefit(soup, name)
        extraction_memory['final_values']['benefit'] = benefit
        log_step('determine_benefit', {'status': 'completed', 'value': benefit})
        
        # Step 6: Extract nutrition facts
        log_step('extract_nutrition', {'status': 'started'})
        nutrition_facts = extract_nutrition_facts(soup)
        extraction_memory['final_values']['nutrition_facts'] = nutrition_facts
        log_step('extract_nutrition', {'status': 'completed', 'facts_found': list(nutrition_facts.keys()) if nutrition_facts else []})
        
        # Create final result with extraction memory attached
        result = {
            'name': name,
            'url': url,
            'prep_time': prep_time,
            'cook_time': cook_time,
            'total_time': total_time,
            'time': total_time if total_time else (cook_time if cook_time else prep_time),
            'ingredients': ingredient_count,
            'benefit': benefit,
            'nutrition_facts': nutrition_facts,
            '_extraction_memory': extraction_memory  # Internal tracking data
        }
        
        log_step('extraction_complete', {'success': True})
        
        # Print summary for debugging
        print(f"\n📄 Extraction Summary for: {url}")
        print(f"   Name: {name}")
        print(f"   Times: Prep={prep_time}, Cook={cook_time}, Total={total_time}")
        print(f"   Ingredients: {ingredient_count}")
        print(f"   Benefit: {benefit}")
        print(f"   Steps completed: {len(extraction_memory['extraction_steps'])}")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        extraction_memory['errors'].append({'error': error_msg, 'timestamp': time.strftime('%H:%M:%S')})
        log_step('extraction_error', {'error': error_msg})
        print(f"❌ Error extracting recipe info from {url}: {error_msg}")
        
        # Even on error, return what we managed to extract
        if extraction_memory['final_values']:
            return {
                'name': extraction_memory['final_values'].get('name', 'Unknown Recipe'),
                'url': url,
                'prep_time': extraction_memory['final_values'].get('prep_time', ''),
                'cook_time': extraction_memory['final_values'].get('cook_time', ''),
                'total_time': extraction_memory['final_values'].get('total_time', ''),
                'time': '',
                'ingredients': extraction_memory['final_values'].get('ingredients', ''),
                'benefit': extraction_memory['final_values'].get('benefit', 'Quick Weeknight'),
                'nutrition_facts': extraction_memory['final_values'].get('nutrition_facts', {}),
                '_extraction_memory': extraction_memory,
                '_extraction_error': error_msg
            }
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

def extract_recipe_name(soup: BeautifulSoup, memory: dict = None) -> str:
    """
    Extract recipe name with multiple fallback methods and logging.
    """
    extraction_log = []
    
    # Method 1: Try to extract from Recipe schema first
    schema_name = extract_name_from_schema(soup)
    extraction_log.append({'method': 'schema', 'found': schema_name, 'valid': is_valid_recipe_name(schema_name) if schema_name else False})
    if schema_name and is_valid_recipe_name(schema_name):
        if memory:
            memory['name_extraction_log'] = extraction_log
            memory['name_method_used'] = 'schema'
        return schema_name
    
    # Method 2: Try various HTML selectors
    selectors = [
        ('h1', 'main_heading'),
        ('.recipe-title', 'recipe_title_class'),
        ('.entry-title', 'entry_title_class'),
        ('.post-title', 'post_title_class'),
        ('[itemprop="name"]', 'schema_name_attr'),
        ('.recipe-name', 'recipe_name_class'),
        ('.title', 'generic_title'),
        ('h2', 'sub_heading'),
        ('.wp-block-post-title', 'wordpress_block'),
        ('.elementor-heading-title', 'elementor_heading')
    ]
    
    for selector, method_name in selectors:
        element = soup.select_one(selector)
        if element:
            raw_name = element.get_text().strip()
            cleaned_name = clean_recipe_name(raw_name)
            is_valid = is_valid_recipe_name(cleaned_name)
            extraction_log.append({
                'method': method_name,
                'selector': selector,
                'raw_value': raw_name[:100],  # Limit length
                'cleaned_value': cleaned_name,
                'valid': is_valid
            })
            if is_valid:
                if memory:
                    memory['name_extraction_log'] = extraction_log
                    memory['name_method_used'] = method_name
                return cleaned_name
    
    # Method 3: Try to extract from page title
    title_tag = soup.find('title')
    if title_tag:
        raw_title = title_tag.get_text().strip()
        # Remove common suffixes
        title = re.sub(r'\s*[-|]\s*.+$', '', raw_title)  # Remove "| Site Name" 
        title = re.sub(r'\s*Recipe$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\-.*$', '', title)  # Remove " - anything"
        cleaned_title = clean_recipe_name(title)
        is_valid = is_valid_recipe_name(cleaned_title)
        extraction_log.append({
            'method': 'page_title',
            'raw_value': raw_title[:100],
            'cleaned_value': cleaned_title,
            'valid': is_valid
        })
        if is_valid:
            if memory:
                memory['name_extraction_log'] = extraction_log
                memory['name_method_used'] = 'page_title'
            return cleaned_title
    
    # Method 4: Try to find recipe name in URL path
    url_element = soup.find('link', rel='canonical')
    if url_element:
        url = url_element.get('href', '')
        name_from_url = extract_name_from_url(url)
        is_valid = is_valid_recipe_name(name_from_url) if name_from_url else False
        extraction_log.append({
            'method': 'url_path',
            'url': url,
            'extracted': name_from_url,
            'valid': is_valid
        })
        if name_from_url and is_valid:
            if memory:
                memory['name_extraction_log'] = extraction_log
                memory['name_method_used'] = 'url_path'
            return name_from_url
    
    # Log failure
    if memory:
        memory['name_extraction_log'] = extraction_log
        memory['name_method_used'] = 'failed'
    
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

def extract_recipe_times(soup: BeautifulSoup) -> tuple[str, str, str]:
    """
    Extract prep time, cook time, and total time from recipe page.
    Returns tuple of (prep_time, cook_time, total_time)
    """
    prep_time = ""
    cook_time = ""
    total_time = ""
    
    # Method 1: Try structured HTML selectors
    selector_mapping = {
        'prepTime': ('[itemprop="prepTime"]', '.prep-time'),
        'cookTime': ('[itemprop="cookTime"]', '.cook-time'),
        'totalTime': ('[itemprop="totalTime"]', '.recipe-time', '.recipe-details-time', '.duration')
    }
    
    for time_type, selectors in selector_mapping.items():
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                time_text = element.get_text().strip()
                time = parse_iso_duration(time_text)
                if time and time != "1 mins":
                    if time_type == 'prepTime':
                        prep_time = time
                    elif time_type == 'cookTime':
                        cook_time = time
                    elif time_type == 'totalTime':
                        total_time = time
                    break
    
    # Method 2: Check meta tags
    meta_mapping = {
        'prepTime': 'meta[itemprop="prepTime"]',
        'cookTime': 'meta[itemprop="cookTime"]',
        'totalTime': 'meta[itemprop="totalTime"]'
    }
    
    for time_type, selector in meta_mapping.items():
        meta = soup.select_one(selector)
        if meta:
            content = meta.get('content', '')
            time = parse_iso_duration(content)
            if time and time != "1 mins":
                if time_type == 'prepTime' and not prep_time:
                    prep_time = time
                elif time_type == 'cookTime' and not cook_time:
                    cook_time = time
                elif time_type == 'totalTime' and not total_time:
                    total_time = time
    
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
                    # Extract all three times from schema
                    if not prep_time and schema.get('prepTime'):
                        prep_time = parse_iso_duration(schema.get('prepTime'))
                    if not cook_time and schema.get('cookTime'):
                        cook_time = parse_iso_duration(schema.get('cookTime'))
                    if not total_time and schema.get('totalTime'):
                        total_time = parse_iso_duration(schema.get('totalTime'))
        except:
            pass
    
    # Method 4: Search for time in page text with specific patterns
    page_text = soup.get_text()
    
    # Pattern for prep time
    prep_patterns = [
        r'prep\s*time[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'preparation\s*time[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'prep[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
    ]
    
    for pattern in prep_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match and not prep_time:
            number = int(match.group(1))
            if 1 <= number <= 180:  # Prep usually 1-180 mins
                match_text = match.group(0).lower()
                if 'hr' in match_text or 'hour' in match_text:
                    prep_time = f"{number} hr" if number == 1 else f"{number} hrs"
                else:
                    prep_time = f"{number} mins"
                break
    
    # Pattern for cook time
    cook_patterns = [
        r'cook\s*time[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'cooking\s*time[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'cook[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
    ]
    
    for pattern in cook_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match and not cook_time:
            number = int(match.group(1))
            if 1 <= number <= 600:  # Cook time can be longer
                match_text = match.group(0).lower()
                if 'hr' in match_text or 'hour' in match_text:
                    cook_time = f"{number} hr" if number == 1 else f"{number} hrs"
                else:
                    cook_time = f"{number} mins"
                break
    
    # Pattern for total time
    total_patterns = [
        r'total\s*time[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'ready\s*in[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
        r'takes[:\s]*(\d+)\s*(?:mins?|minutes?|hrs?|hours?)',
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match and not total_time:
            number = int(match.group(1))
            if 5 <= number <= 1440:  # Total time sanity check
                match_text = match.group(0).lower()
                if 'hr' in match_text or 'hour' in match_text:
                    total_time = f"{number} hr" if number == 1 else f"{number} hrs"
                else:
                    total_time = f"{number} mins"
                break
    
    return prep_time, cook_time, total_time

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
    Extract ingredient count from recipe page - counts actual bullet points and list items.
    """
    # Method 1: Count bullet points in ingredient lists (most accurate for visual count)
    bullet_selectors = [
        '.ingredients ul > li',
        '.ingredients ol > li',
        '.ingredient-list > li',
        '.recipe-ingredients ul > li',
        '.recipe-ingredients ol > li',
        '.ingredients-list > li',
        '.wp-block-ingredients-list > li',
        '.tasty-recipes-ingredients ul > li',
        '.tasty-recipes-ingredients ol > li',
        '.tasty-recipes-ingredients-body > li',
        '.wprm-recipe-ingredients-list > li',
        '.ingredient-group > li',
        '[itemprop="recipeIngredient"]'
    ]
    
    for selector in bullet_selectors:
        ingredients = soup.select(selector)
        if 0 < len(ingredients) < 50:  # Sanity check
            # Quick validation - just check it's not empty and has reasonable length
            valid_count = 0
            for ing in ingredients:
                text = ing.get_text().strip()
                # Just ensure it's not empty and has some content
                if len(text) > 2:
                    valid_count += 1
            
            if valid_count > 0:
                print(f"Found {valid_count} ingredients using bullet selector: {selector}")
                return str(valid_count)
    
    # Method 2: Count all list items within ingredient sections
    ingredient_section_selectors = [
        '.ingredients',
        '.ingredient-list',
        '.recipe-ingredients',
        '.tasty-recipes-ingredients',
        '.wprm-recipe-ingredients'
    ]
    
    for section_selector in ingredient_section_selectors:
        section = soup.select_one(section_selector)
        if section:
            # Count all list items within this section
            all_items = section.find_all('li')
            if 0 < len(all_items) < 50:
                # Validate they're ingredients (not sub-lists or notes)
                valid_count = 0
                for item in all_items:
                    text = item.get_text().strip()
                    # Check if it looks like an ingredient (has measurement or common ingredient)
                    has_measurement = any(unit in text.lower() for unit in ['cup', 'tbsp', 'tsp', 'oz', 'lb', 'g ', 'kg', 'ml', 'tablespoon', 'teaspoon', 'pound', 'ounce', 'gram', 'clove', 'piece', 'slice'])
                    has_ingredient = any(word in text.lower() for word in ['salt', 'pepper', 'oil', 'butter', 'garlic', 'onion', 'flour', 'sugar', 'egg', 'milk', 'water', 'chicken', 'beef', 'cheese', 'pasta', 'rice', 'vegetable', 'fruit', 'herb', 'spice'])
                    if (has_measurement or has_ingredient) and len(text) > 2:
                        valid_count += 1
                
                if valid_count > 0:
                    print(f"Found {valid_count} ingredients in section: {section_selector}")
                    return str(valid_count)
    
    # Method 3: Extract from JSON-LD schema (structured data)
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            schemas = data if isinstance(data, list) else [data]
            
            for schema in schemas:
                if schema.get('@type') == 'Recipe' or (isinstance(schema.get('@type'), list) and 'Recipe' in schema.get('@type', [])):
                    recipe_ingredients = schema.get('recipeIngredient', [])
                    if recipe_ingredients and 0 < len(recipe_ingredients) < 50:
                        print(f"Found {len(recipe_ingredients)} ingredients from JSON-LD schema")
                        return str(len(recipe_ingredients))
        except:
            pass
    
    # Method 4: Manual counting of bullet characters in ingredients section
    page_text = soup.get_text()
    
    # Find ingredients section and count bullet points
    ingredients_section_match = re.search(r'(?i)ingredients[\s:]*\n(.*?)(?:\n\n|\n[A-Z]|instructions|directions|method|$)', page_text, re.DOTALL)
    if ingredients_section_match:
        section = ingredients_section_match.group(1)
        # Count lines that start with bullet characters
        bullet_pattern = r'^[\s•\-\*\+\d]'
        lines = section.split('\n')
        bullet_count = 0
        for line in lines:
            if re.match(bullet_pattern, line.strip()) and len(line.strip()) > 3:
                bullet_count += 1
        
        if bullet_count > 0:
            print(f"Found {bullet_count} bullet points in ingredients section")
            return str(bullet_count)
    
    # Default - return empty to indicate extraction failed
    print("Could not accurately determine ingredient count")
    return ""

def determine_recipe_benefit(soup: BeautifulSoup, recipe_name: str) -> str:
    """
    Determine recipe benefit/category based on content and name with scoring system.
    """
    name_lower = recipe_name.lower()
    page_text = soup.get_text().lower()
    
    # Define benefit categories with keywords and weights
    benefits = {
        "Quick Weeknight": {
            "keywords": ["quick", "fast", "easy", "simple", "weeknight", "busy", "15 minute", "20 minute", "30 minute", "under 30", "15 min", "20 min", "30 min"],
            "weight": 3,
            "time_threshold": 30  # Minutes
        },
        "High Protein": {
            "keywords": ["high protein", "protein-rich", "protein packed"],
            "ingredients": ["chicken", "beef", "fish", "salmon", "tuna", "shrimp", "turkey", "pork", "lamb", "tofu", "tempeh", "eggs", "egg", "lentils", "beans", "quinoa"],
            "weight": 2
        },
        "Budget Friendly": {
            "keywords": ["budget", "cheap", "affordable", "economical", "inexpensive", "frugal", "money-saving"],
            "weight": 2
        },
        "Vegan": {
            "keywords": ["vegan", "plant-based", "plant based", "dairy-free", "dairy free", "no animal", "cruelty-free"],
            "weight": 3
        },
        "Vegetarian": {
            "keywords": ["vegetarian", "meatless", "meat-free", "meat free"],
            "weight": 2
        },
        "Healthy": {
            "keywords": ["healthy", "light", "low-fat", "low fat", "nutritious", "fresh", "clean eating", "wholesome", "good for you"],
            "weight": 2
        },
        "Comfort Food": {
            "keywords": ["comfort food", "comforting", "cozy", "hearty", "warm", "soul food", "rich", "indulgent"],
            "weight": 2
        },
        "One Pan": {
            "keywords": ["one pan", "one-pot", "one pot", "single pan", "sheet pan", "skillet", "one dish"],
            "weight": 3
        },
        "Meal Prep": {
            "keywords": ["meal prep", "make-ahead", "make ahead", "batch cook", "freezer friendly", "storage", "prep ahead"],
            "weight": 2
        },
        "Spicy": {
            "keywords": ["spicy", "hot", "chili", "chilli", "pepper", "jalapeño", "cayenne", "sriracha", "heat", "fiery"],
            "weight": 2
        },
        "Date Night": {
            "keywords": ["romantic", "date night", "date-night", "special occasion", "elegant", "fancy", "impressive"],
            "weight": 2
        },
        "No Oven": {
            "keywords": ["no oven", "stovetop", "stove top", "grill", "grilled", "raw", "no bake", "no-bake"],
            "weight": 2
        }
    }
    
    # Score each benefit
    scores = {}
    
    for benefit, data in benefits.items():
        score = 0
        
        # Check keywords in recipe name (higher weight)
        for keyword in data.get("keywords", []):
            if keyword in name_lower:
                score += data["weight"] * 2  # Double weight for name matches
        
        # Check keywords in page content
        for keyword in data.get("keywords", []):
            if keyword in page_text:
                score += data["weight"]
        
        # Check ingredients for specific benefits
        if "ingredients" in data:
            for ingredient in data["ingredients"]:
                if ingredient in name_lower or ingredient in page_text:
                    score += 1
        
        # Special check for Quick Weeknight based on time
        if benefit == "Quick Weeknight":
            # Look for time indicators in recipe name
            time_match = re.search(r'(\d+)\s*(?:min|minute)', name_lower)
            if time_match:
                minutes = int(time_match.group(1))
                if minutes <= data["time_threshold"]:
                    score += 3
        
        scores[benefit] = score
    
    # Find benefit with highest score
    if scores:
        max_score = max(scores.values())
        if max_score > 0:
            best_benefit = max(scores, key=scores.get)
            return best_benefit
    
    # Default fallback - try to infer from recipe name structure
    if any(word in name_lower for word in ['salad', 'soup', 'stew', 'curry']):
        return "Healthy"
    elif any(word in name_lower for word in ['pasta', 'noodles', 'rice']):
        return "Quick Weeknight"
    elif any(word in name_lower for word in ['cake', 'cookie', 'pie', 'dessert']):
        return "Comfort Food"
    
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
