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
    Find recipe links on the main page.
    """
    links = []
    
    # Common patterns for recipe links
    recipe_patterns = [
        r'/recipe[s]?/',
        r'/cook/',
        r'/food/',
        r'/dishes/',
        r'/meals/'
    ]
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)
        
        # Check if it looks like a recipe link
        if any(re.search(pattern, href, re.IGNORECASE) for pattern in recipe_patterns):
            links.append(full_url)
        elif 'recipe' in a_tag.get_text().lower():
            links.append(full_url)
    
    # Remove duplicates
    return list(set(links))

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
    Extract recipe name from various HTML elements.
    """
    # Try different selectors for recipe titles
    selectors = [
        'h1',
        '.recipe-title',
        '.entry-title',
        '.post-title',
        'h2',
        '[itemprop="name"]'
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            name = element.get_text().strip()
            if len(name) > 3:  # Ensure it's not empty or too short
                return name
    
    return "Unknown Recipe"

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
