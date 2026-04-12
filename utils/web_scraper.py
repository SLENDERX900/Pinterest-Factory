"""
utils/web_scraper.py
Web scraping utilities for extracting recipe information from food blog websites.
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import time

def scrape_recipes_from_website(base_url: str, max_recipes: int = 50) -> list[dict]:
    """
    Scrape recipe information from a food blog website.
    
    Args:
        base_url: The base URL of the food blog
        max_recipes: Maximum number of recipes to extract
        
    Returns:
        List of recipe dictionaries with name, url, time, ingredients, benefit
    """
    try:
        # Get the main page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find recipe links
        recipe_links = find_recipe_links(soup, base_url)
        
        recipes = []
        for link in recipe_links[:max_recipes]:
            try:
                recipe = extract_recipe_info(link, headers)
                if recipe:
                    recipes.append(recipe)
                    time.sleep(1)  # Be respectful to the server
            except Exception as e:
                print(f"Error scraping {link}: {e}")
                continue
                
        return recipes
        
    except Exception as e:
        print(f"Error scraping website {base_url}: {e}")
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
    Extract recipe name, filtering out generic titles.
    """
    # Try different selectors for recipe titles
    selectors = [
        'h1',
        '.recipe-title',
        '.entry-title',
        '.post-title',
        '[itemprop="name"]',
        '.recipe-name',
        '.title'
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            name = element.get_text().strip()
            # Filter out generic names
            if is_valid_recipe_name(name):
                return name
    
    # Fallback: try to extract from page title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text().strip()
        # Remove common suffixes
        title = re.sub(r'\s*[-|]\s*.+$', '', title)  # Remove "| Site Name" 
        title = re.sub(r'\s*Recipe$', '', title, flags=re.IGNORECASE)
        if is_valid_recipe_name(title):
            return title
    
    return "Unknown Recipe"

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
    Extract cooking time information.
    """
    # Look for time-related information
    time_patterns = [
        r'(\d+)\s*mins?',
        r'(\d+)\s*minutes?',
        r'(\d+)\s*hrs?',
        r'(\d+)\s*hours?',
        r'(\d+)\s*hr'
    ]
    
    # Check common time selectors
    time_selectors = [
        '[itemprop="cookTime"]',
        '[itemprop="totalTime"]',
        '.cook-time',
        '.prep-time',
        '.recipe-time',
        '.time'
    ]
    
    for selector in time_selectors:
        element = soup.select_one(selector)
        if element:
            time_text = element.get_text().lower()
            for pattern in time_patterns:
                match = re.search(pattern, time_text)
                if match:
                    number = match.group(1)
                    if 'hr' in time_text:
                        return f"{number} hr"
                    else:
                        return f"{number} mins"
    
    # If no structured time found, return default
    return "30 mins"

def extract_ingredient_count(soup: BeautifulSoup) -> str:
    """
    Extract or estimate ingredient count.
    """
    # Look for ingredient lists
    ingredient_selectors = [
        '.ingredients li',
        '.ingredient-list li',
        '[itemprop="recipeIngredient"]',
        '.recipe-ingredients li'
    ]
    
    for selector in ingredient_selectors:
        ingredients = soup.select(selector)
        if len(ingredients) > 0:
            return str(len(ingredients))
    
    # If no structured ingredients found, estimate based on content
    # This is a fallback - could be improved
    return "8"

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
