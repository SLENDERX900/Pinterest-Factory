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
    
    prompt = f"""
Target recipe:
- Name: {recipe.get("name","")}
- Time: {recipe.get("time","")}
- Ingredient count: {recipe.get("ingredients","")}
- Benefit: {recipe.get("benefit","")}
- URL: {recipe.get("url","")}

Similar trending Pinterest pins:
{context_block}

Based on the recipe content and trending pins, create 5 hooks using these dynamic angles:
{dynamic_angles}

Return ONLY valid JSON as an array of 5 objects.
Each object must include:
- angle (use the exact angle names provided above, or create better ones based on content)
- hook (<= 8 words, humanized, specific, punchy)
- description (<= 150 chars, SEO-friendly)
- vibe_prompt (short visual direction for image generation)

The angles should feel native to THIS specific recipe, not generic.
"""
    try:
        raw = _generate(prompt, model=model)
        data = json.loads(raw)
        if isinstance(data, list) and len(data) >= 5:
            return data[:5]
    except Exception:
        pass

    # Fallback with dynamic angles
    name = recipe.get("name", "Recipe")
    return [
        {"angle": dynamic_angles[0], "hook": f"Fast {name} in minutes", "description": f"Quick {name} for busy nights.", "vibe_prompt": "bright, efficient weeknight dinner"},
        {"angle": dynamic_angles[1], "hook": f"Low-effort {name} tonight", "description": f"Minimal effort {name} with big flavor.", "vibe_prompt": "cozy one-pan comfort mood"},
        {"angle": dynamic_angles[2], "hook": f"Weeknight {name} hero", "description": f"Reliable {name} for your weeknight rotation.", "vibe_prompt": "family dinner table warmth"},
        {"angle": dynamic_angles[3], "hook": f"Simple {name} ingredient win", "description": f"Easy pantry-friendly {name} anyone can make.", "vibe_prompt": "minimal ingredients styled cleanly"},
        {"angle": dynamic_angles[4], "hook": f"Best method for {name}", "description": f"Foolproof method to make {name} perfectly.", "vibe_prompt": "close-up food texture detail"},
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
