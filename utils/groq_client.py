"""
STEP 3: Groq Cloud API Hook Generation with Dynamic Angles
Generates hooks based on recipe content + web scraping data.
Angles are self-generated (not fixed templates) based on what will perform best.
"""

from __future__ import annotations

import json
import os
from typing import Any

from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Fallback angles if generation fails
FALLBACK_ANGLES = ["Time-saver", "Lazy Dinner", "Weeknight Hero", "Ingredient-Count", "Core Method"]

# Dynamic angle categories for self-generation
ANGLE_CATEGORIES = [
    "Time/Effort (quick, fast, easy, under X minutes)",
    "Effort Level (lazy, simple, hands-off, dump-and-go)",
    "Meal Role (weeknight hero, family favorite, date night)",
    "Ingredients (pantry staples, minimal ingredients, budget-friendly)",
    "Technique/Method (one-pan, sheet-pan, slow cooker, air fryer)",
    "Dietary (healthy, low-carb, high-protein, comfort food)",
    "Occasion (meal prep, entertaining, kids love it)",
    "Result/Outcome (crispy, juicy, fall-apart tender, restaurant-quality)"
]


def check_connection() -> tuple[bool, str]:
    if not GROQ_API_KEY:
        return False, "GROQ_API_KEY not set."
    try:
        client = Groq(api_key=GROQ_API_KEY)
        _ = client.models.list()
        return True, GROQ_MODEL
    except Exception as exc:
        return False, f"Groq API error: {exc}"


def _generate(prompt: str, model: str | None = None, max_tokens: int = 900) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You write high-performing Pinterest copy for recipe content."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.75,
        max_tokens=max_tokens,
        top_p=0.95,
    )
    return (response.choices[0].message.content or "").strip()


def _extract_dynamic_angles(recipe: dict, trend_context: list[dict]) -> list[str]:
    """
    Analyze recipe + trends to determine which angles will perform best.
    Returns 5 specific angle names tailored to this content.
    """
    angles = []
    name = recipe.get("name", "").lower()
    benefit = recipe.get("benefit", "").lower()
    time_str = recipe.get("time", "").lower()
    
    # Determine based on recipe characteristics
    if any(x in time_str for x in ["15", "20", "30", "min", "quick", "fast"]):
        angles.append("Lightning-Fast")
    if any(x in name or x in benefit for x in ["easy", "simple", "beginner", "foolproof"]):
        angles.append("Effortless")
    if any(x in name or x in benefit for x in ["healthy", "protein", "low-carb", "keto", "paleo"]):
        angles.append("Health-Boost")
    if any(x in name for x in ["chicken", "beef", "pork", "salmon", "shrimp", "tofu"]):
        angles.append("Protein-Packed")
    if any(x in name or x in benefit for x in ["crispy", "crunchy", "golden", "baked"]):
        angles.append("Texture-Perfect")
    if any(x in name or x in benefit for x in ["sheet-pan", "one-pan", "one-pot", "skillet"]):
        angles.append("Minimal-Cleanup")
    if any(x in name for x in ["pasta", "noodle", "rice", "potato", "bread"]):
        angles.append("Carb-Comfort")
    if any(x in benefit for x in ["family", "kid", "children", "picky", "crowd"]):
        angles.append("Family-Approved")
    if any(x in time_str for x in ["hour", "slow", "crock", "braised", "roasted"]):
        angles.append("Slow-Cooked")
    if any(x in name or x in benefit for x in ["spicy", "bold", "flavor", "garlic", "herb"]):
        angles.append("Big-Flavor")
    if any(x in name for x in ["salad", "bowl", "fresh", "light"]):
        angles.append("Fresh-Bright")
    if any(x in benefit for x in ["budget", "cheap", "affordable", "pantry", "staple"]):
        angles.append("Budget-Smart")
    
    # Fill remaining slots with trend-informed angles
    if len(angles) < 5:
        # Look at trending context for popular angles
        trend_text = " ".join([c.get("title", "") + " " + c.get("description", "") for c in trend_context[:3]]).lower()
        if "easy" in trend_text and "Effortless" not in angles:
            angles.append("Effortless")
        if "quick" in trend_text and "Lightning-Fast" not in angles:
            angles.append("Lightning-Fast")
        if "healthy" in trend_text and "Health-Boost" not in angles:
            angles.append("Health-Boost")
    
    # Fill with defaults if still short
    defaults = ["Time-Saver", "Lazy-Dinner", "Weeknight-Hero", "Ingredient-Count", "Core-Method"]
    while len(angles) < 5:
        for d in defaults:
            if d not in angles:
                angles.append(d)
                break
    
    return angles[:5]


def generate_hook_packages(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> list[dict[str, Any]]:
    """
    STEP 3: Generate dynamic hook packages based on recipe + web scraping.
    Angles are self-determined by AI based on content, not fixed templates.
    """
    trend_context = trend_context or []
    
    # Determine dynamic angles for this recipe
    dynamic_angles = _extract_dynamic_angles(recipe, trend_context)
    
    context_lines = [
        f"- {c.get('title','')} | {c.get('description','')}"[:280]
        for c in trend_context[:5]
    ]
    context_block = "\n".join(context_lines) if context_lines else "- (no trend context found)"
    
    angles_list = "\n".join([f"  {i+1}. {angle}" for i, angle in enumerate(dynamic_angles)])
    
    # Extract blog content for voice/style learning
    blog_sample = recipe.get("blog_content_sample", "")
    meta_keywords = recipe.get("meta_keywords", "")
    ingredient_names = recipe.get("ingredient_names", "")
    
    # Extract Pinterest trend language patterns
    trend_titles = [c.get("title", "") for c in trend_context[:5]]
    trend_descs = [c.get("description", "") for c in trend_context[:5]]
    trend_language = " ".join(trend_titles + trend_descs)
    
    prompt = f"""You are a Pinterest marketing expert. Create hooks by COMBINING the food blog's voice with winning Pinterest language.

=== SOURCE 1: FOOD BLOG CONTENT ===
Recipe name: {recipe.get("name","")}
Blog description: {blog_sample[:400] if blog_sample else "Not extracted"}
Key ingredients: {ingredient_names if ingredient_names else "Not extracted"}
Meta keywords: {meta_keywords if meta_keywords else "None"}
Time: {recipe.get("time","")} | Benefit: {recipe.get("benefit","")}

=== SOURCE 2: TOP PINTEREST TRENDS FOR THIS RECIPE TYPE ===
Trending pin titles:
{trend_titles if trend_titles else "- (no trend data)"}

Trending pin descriptions:
{trend_descs if trend_descs else "- (no trend data)"}

=== YOUR TASK ===
Create 5 hooks for these angles:
{angles_list}

INSTRUCTIONS:
1. ANALYZE the blog's writing style from "Blog description" - notice their tone, vocabulary, what they emphasize
2. EXTRACT winning language patterns from "Top Pinterest Trends" - what words/phrases perform well for similar recipes?
3. BLEND both sources: Use the blog's voice + Pinterest-proven language structures

EXAMPLES OF GOOD BLENDING:
- Blog says "crispy golden chicken" + Pinterest trend "better than takeout" → "Crispy chicken that beats delivery"
- Blog emphasizes "30 minutes" + Pinterest trend "weeknight hero" → "Your new 30-minute weeknight hero"
- Blog mentions "kids love it" + Pinterest trend "picky eater approved" → "Finally, picky eaters clean their plates"

ANGLE → CONTENT RULES:
- "Lightning-Fast" = speed focus → use blog's time claims + Pinterest urgency words
- "Health-Boost" = nutrition angle → blend blog's health claims with Pinterest wellness language  
- "Protein-Packed" = fitness angle → blog's protein info + Pinterest gym/recovery terms
- "Texture-Perfect" = sensory focus → blog's texture words + Pinterest mouthfeel hooks
- "Family-Approved" = crowd-pleaser → blog's family notes + Pinterest kid/parent language

Return ONLY valid JSON:
[{{"angle": "...", "hook": "...", "description": "...", "vibe_prompt": "..."}}, ...]
"""
    try:
        raw = _generate(prompt, model=model)
        data = json.loads(raw)
        if isinstance(data, list) and len(data) >= 5:
            return data[:5]
    except Exception:
        pass

    # Smart fallback: Use blog content + trend keywords when AI fails
    name = recipe.get("name", "Recipe")
    blog_sample = recipe.get("blog_content_sample", "")
    ingredient_names = recipe.get("ingredient_names", "")
    
    # Extract keywords from blog content for smarter fallbacks
    blog_lower = blog_sample.lower()
    
    # Check for specific blog claims we can use
    has_crispy = "crispy" in blog_lower or "crunchy" in blog_lower
    has_juicy = "juicy" in blog_lower or "tender" in blog_lower
    has_quick = "quick" in blog_lower or "fast" in blog_lower or "easy" in blog_lower
    has_family = "family" in blog_lower or "kid" in blog_lower or "children" in blog_lower
    has_protein = "protein" in blog_lower or "chicken" in blog_lower or "beef" in name.lower()
    
    def smart_hook_for_angle(angle: str) -> dict:
        angle_lower = angle.lower()
        
        # Build hooks using actual blog content when possible
        if "lightning" in angle_lower or "fast" in angle_lower or "quick" in angle_lower or "time" in angle_lower:
            if has_quick:
                return {"hook": "Quick enough for tonight", "desc": f"Fast {name} when you need it now.", "vibe": "speedy weeknight cooking"}
            return {"hook": "Dinner ready before delivery arrives", "desc": f"Lightning-fast {name} for busy nights.", "vibe": "speedy energetic cooking"}
            
        elif "health" in angle_lower:
            return {"hook": "Guilt-free comfort in every bite", "desc": f"Healthy {name} that actually satisfies.", "vibe": "fresh vibrant healthy food"}
            
        elif "protein" in angle_lower:
            if has_protein:
                return {"hook": "Protein that tastes like indulgence", "desc": f"High-protein {name} you'll crave.", "vibe": "satisfying protein-rich meal"}
            return {"hook": "40g protein per serving", "desc": f"High-protein {name} for fuel.", "vibe": "athletic nutrition focused"}
            
        elif "texture" in angle_lower or "crispy" in angle_lower:
            if has_crispy and has_juicy:
                return {"hook": "Crispy meets juicy perfection", "desc": f"The texture combination you crave.", "vibe": "sensational texture contrast"}
            elif has_crispy:
                return {"hook": "The crunch you've been craving", "desc": f"Crispy {name} done right.", "vibe": "crunchy texture close-up"}
            return {"hook": "Crispy outside, juicy inside", "desc": f"Perfect texture every single time.", "vibe": "macro food texture detail"}
            
        elif "family" in angle_lower or "kid" in angle_lower or "crowd" in angle_lower:
            if has_family:
                return {"hook": "Finally, everyone agrees on dinner", "desc": f"The {name} that unites picky eaters.", "vibe": "happy family dinner table"}
            return {"hook": "Picky eaters ask for seconds", "desc": f"Family-favorite {name} everyone loves.", "vibe": "happy family dinner moment"}
            
        elif "flavor" in angle_lower or "bold" in angle_lower:
            return {"hook": "Flavor that stops the scroll", "desc": f"Bold taste in every bite.", "vibe": "rich flavorful food close-up"}
            
        elif "effortless" in angle_lower or "lazy" in angle_lower or "easy" in angle_lower:
            return {"hook": "Set it and forget it", "desc": f"Hands-off {name} with maximum flavor.", "vibe": "relaxed effortless cooking"}
            
        elif "weeknight" in angle_lower or "hero" in angle_lower:
            return {"hook": "Your new Tuesday night staple", "desc": f"Reliable {name} for weeknight rotation.", "vibe": "cozy weeknight dinner table"}
            
        elif "budget" in angle_lower or "pantry" in angle_lower:
            return {"hook": "Pantry staples, restaurant results", "desc": f"Budget-friendly {name} that impresses.", "vibe": "simple home cooking elegance"}
            
        else:
            # Use first ingredient if available for personalization
            if ingredient_names:
                first_ing = ingredient_names.split(",")[0].strip()
                return {"hook": f"{first_ing.title()} done perfectly", "desc": f"Best {name} with premium ingredients.", "vibe": "quality ingredient spotlight"}
            return {"hook": f"The {name} that changes everything", "desc": f"Best {name} you'll ever make.", "vibe": "appetizing food hero shot"}
    
    return [
        {"angle": angle, **smart_hook_for_angle(angle)}
        for angle in dynamic_angles[:5]
    ]


def generate_hooks(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> dict[str, str]:
    """
    Generate hooks as a dictionary with dynamic angles as keys.
    """
    packages = generate_hook_packages(recipe, trend_context=trend_context, model=model)
    hooks = {p.get("angle", f"Angle-{i}"): p.get("hook", "") for i, p in enumerate(packages)}
    return hooks


def generate_description(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> str:
    """Generate SEO description from first package."""
    packages = generate_hook_packages(recipe, trend_context=trend_context, model=model)
    return (packages[0].get("description", "") if packages else "").strip()


# Backward compatibility - ANGLES export for components that reference it
ANGLES = FALLBACK_ANGLES
