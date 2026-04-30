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
    
    prompt = f"""Target recipe:
- Name: {recipe.get("name","")}
- Time: {recipe.get("time","")}
- Ingredient count: {recipe.get("ingredients","")}
- Benefit: {recipe.get("benefit","")}
- URL: {recipe.get("url","")}

Similar trending Pinterest pins:
{context_block}

Create 5 hooks for these angles:
{angles_list}

CRITICAL: Each hook must be CUSTOM-TAILORED to its specific angle. Do NOT use the same sentence pattern for all hooks.

EXAMPLES BY ANGLE TYPE:
- "Lightning-Fast" → "Dinner ready before the pasta water boils" or "20 minutes start to finish"
- "Health-Boost" → "High protein without the bland" or "Guilt-free comfort food"
- "Protein-Packed" → "40g protein per serving" or "Muscles love this bowl"
- "Texture-Perfect" → "Crispy edges, juicy center" or "The crunch you crave"
- "Minimal-Cleanup" → "One pan, zero regrets" or "The dishwasher stays closed"
- "Budget-Smart" → "Feeds 4 for under $10" or "Pantry staples, restaurant taste"
- "Family-Approved" → "Picky eaters ask for seconds" or "Kid-tested, parent-loved"
- "Big-Flavor" → "Garlicky, buttery, perfect" or "Bold flavors, simple steps"

RULES:
- Each hook MUST sound different from the others (vary sentence structure)
- Hook must REFLECT its angle's specific promise (not just mention the recipe name)
- <= 8 words per hook
- Human, punchy, scroll-stopping

Return ONLY valid JSON as an array of 5 objects:
[{{"angle": "...", "hook": "...", "description": "...", "vibe_prompt": "..."}}, ...]
"""
    try:
        raw = _generate(prompt, model=model)
        data = json.loads(raw)
        if isinstance(data, list) and len(data) >= 5:
            return data[:5]
    except Exception:
        pass

    # Fallback hooks - angle-specific and varied sentence structures
    name = recipe.get("name", "Recipe")
    time = recipe.get("time", "")
    benefit = recipe.get("benefit", "")
    
    # Create varied hooks that match typical angle meanings
    fallback_hooks = [
        {"hook": "Dinner ready before delivery arrives", "desc": f"Fast {name} for busy weeknights.", "vibe": "speedy modern kitchen action"},
        {"hook": "Set it and forget it", "desc": f"Hands-off {name} with maximum flavor.", "vibe": "relaxed cooking scene"},
        {"hook": "The recipe that converted skeptics", "desc": f"Family-favorite {name} everyone loves.", "vibe": "happy family dinner moment"},
        {"hook": "Pantry staples, restaurant results", "desc": f"Budget-friendly {name} that impresses.", "vibe": "elegant plating on simple table"},
        {"hook": "Crispy outside, juicy inside", "desc": f"Perfect texture every single time.", "vibe": "macro food texture shot"},
    ]
    
    return [
        {"angle": dynamic_angles[i], "hook": fb["hook"], "description": fb["desc"], "vibe_prompt": fb["vibe"]}
        for i, fb in enumerate(fallback_hooks[:5])
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
