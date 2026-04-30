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
    
    # Build rich context from real Pinterest data
    context_lines = []
    for c in trend_context[:5]:
        title = c.get('title', '').strip()
        desc = c.get('description', '').strip()
        if title or desc:
            context_lines.append(f"• {title[:100]} | {desc[:150]}")
    context_block = "\n".join(context_lines) if context_lines else "No specific Pinterest trends found - use general best practices"
    
    angles_list = "\n".join([f"  {i+1}. {angle}" for i, angle in enumerate(dynamic_angles)])
    
    # Extract blog content for voice/style learning
    blog_sample = recipe.get("blog_content_sample", "")
    meta_keywords = recipe.get("meta_keywords", "")
    ingredient_names = recipe.get("ingredient_names", "")
    
    # Extract real Pinterest trend patterns
    real_trend_data = []
    for c in trend_context[:8]:  # More trends for better analysis
        title = c.get('title', '').strip()
        desc = c.get('description', '').strip()
        if title:
            real_trend_data.append(f"TITLE: {title}")
        if desc:
            real_trend_data.append(f"DESC: {desc}")
    
    trend_analysis = "\n".join(real_trend_data) if real_trend_data else "No real trend data available"
    
    prompt = f"""You are a Pinterest marketing expert. Create hooks by ANALYZING REAL PINTEREST DATA and blending it with the recipe content.

=== RECIPE TO PROMOTE ===
Recipe: {recipe.get("name","")}
Time: {recipe.get("time","")} | Benefit: {recipe.get("benefit","")}
Blog voice: {blog_sample[:300] if blog_sample else "Casual food blog style"}
Keywords: {meta_keywords[:200] if meta_keywords else "General recipe keywords"}
Ingredients: {ingredient_names[:200] if ingredient_names else "Standard ingredients"}

=== REAL PINTEREST TREND ANALYSIS ===
Study these ACTUAL trending pins for similar recipes:
{trend_analysis}

=== YOUR TASK ===
Create 5 hooks for these angles based on REAL TREND PATTERNS:
{angles_list}

CRITICAL INSTRUCTIONS:
1. STUDY the real Pinterest titles above - notice what words get clicks
2. MIRROR successful patterns from the trend data
3. BLEND with recipe specifics - make it authentic to this recipe
4. HOOKS must be 6-8 words MAX - punchy and scroll-stopping
5. DESCRIPTIONS must be 15-25 words - compelling copy for Pinterest

TREND-BASED HOOK FORMULAS (use what you see in the data):
- If trends say "better than takeout" → Use "Beats [takeout/restaurant]"
- If trends say "30 minute" → Use "30-minute [recipe type]"
- If trends say "family favorite" → Use "Family [emotion] [recipe]"
- If trends say "crispy golden" → Use "[Texture] [result]"

HOOK REQUIREMENTS:
- 6-8 words maximum
- Start with action/benefit words
- Include recipe-specific details
- Mirror high-performing trend patterns

DESCRIPTION REQUIREMENTS:
- 15-25 words (much longer than before)
- Include key SEO keywords
- Compelling benefit statement
- Call-to-action or urgency

Return ONLY valid JSON:
[{{"angle": "...", "hook": "6-8 word punchy hook", "description": "15-25 word compelling description", "vibe_prompt": "..."}}, ...]
"""
    try:
        print(f"GROQ DEBUG: Sending prompt to Groq...", flush=True)
        raw = _generate(prompt, model=model)
        print(f"GROQ DEBUG: Raw response: {raw[:200]}...", flush=True)
        
        # Extract JSON from response - Groq often adds explanatory text before JSON
        json_start = raw.find('[')
        json_end = raw.rfind(']') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = raw[json_start:json_end]
            print(f"GROQ DEBUG: Extracted JSON: {json_str[:100]}...", flush=True)
            
            data = json.loads(json_str)
            print(f"GROQ DEBUG: Parsed JSON type: {type(data)}", flush=True)
            print(f"GROQ DEBUG: Parsed JSON length: {len(data) if isinstance(data, list) else 'not a list'}", flush=True)
            
            if isinstance(data, list) and len(data) >= 5:
                print(f"GROQ DEBUG: Successfully parsed {len(data)} hooks from Groq", flush=True)
                return data[:5]
            else:
                print(f"GROQ DEBUG: Invalid JSON structure, using fallback", flush=True)
        else:
            print(f"GROQ DEBUG: No JSON found in response, using fallback", flush=True)
            
    except Exception as e:
        print(f"GROQ DEBUG: Error parsing Groq response: {e}", flush=True)
        print(f"GROQ DEBUG: Raw response that failed: {raw}", flush=True)
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
