"""
utils/groq_client.py
Thin wrapper around the Groq API for LLM calls.
Replaces Ollama for cloud deployment.
"""

import os
import json
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

ANGLES = ["Time-saver", "Lazy Dinner", "Weeknight Hero", "Ingredient-Count", "Core Method"]


def check_connection() -> tuple[bool, str]:
    """
    Returns (True, model_name) if Groq API key is valid.
    Returns (False, error_message) otherwise.
    """
    if not GROQ_API_KEY:
        return False, "GROQ_API_KEY not set. Add it to your .env file or Streamlit secrets."

    try:
        client = Groq(api_key=GROQ_API_KEY)
        # Quick test - list models
        models = client.models.list()
        model_names = [m.id for m in models.data]
        if GROQ_MODEL in model_names:
            return True, GROQ_MODEL
        return True, model_names[0] if model_names else "groq-model"
    except Exception as e:
        return False, f"Groq API error: {e}"


def _generate(prompt: str, model: str = None) -> str:
    """Raw generate call. Returns response text or raises on failure."""
    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a Pinterest copywriter for recipe content. Be concise, direct, and catchy."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.65,
        max_tokens=512,
        top_p=0.9,
    )

    return response.choices[0].message.content.strip()


def generate_hooks(recipe: dict, model: str = None) -> dict[str, str]:
    """
    Generate 5 Pinterest hooks for a single recipe.
    Returns {angle_name: hook_text} dict.
    Falls back to template hooks if Groq fails.
    """
    name = recipe.get("name", "Recipe")
    time = recipe.get("time", "")
    ingredients = recipe.get("ingredients", "")
    benefit = recipe.get("benefit", "")

    prompt = f"""You are writing Pinterest pin text for a recipe website. Recipes are direct, technical, zero fluff.

Recipe: {name}
Cook time: {time}
Ingredient count: {ingredients}
Key benefit/tag: {benefit}

Generate EXACTLY 5 Pinterest hooks. Each hook must be under 8 words. No punctuation at end. No quotes.
One per line, in this exact order:

1. Time-saver angle (lead with the time)
2. Lazy Dinner angle (effortless/minimal effort framing)
3. Weeknight Hero angle (weeknight/busy framing)
4. Ingredient-Count angle (lead with ingredient count)
5. Core Method angle (the key technique or result)

Output ONLY the 5 hooks, one per line, numbered 1-5. Nothing else."""

    try:
        raw = _generate(prompt, model)

        # Remove conversational filler from raw output
        filler_phrases = [
            'Here are the 5 Pinterest hooks:',
            'Here are 5 Pinterest hooks:',
            'Here are the hooks:',
            'Here are hooks:',
            'Pinterest hooks:',
            'hooks:',
            'Here are',
            'Pinterest',
        ]
        for phrase in filler_phrases:
            raw = raw.replace(phrase, '')
            raw = raw.replace(phrase.capitalize(), '')
            raw = raw.replace(phrase.upper(), '')

        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        # Extract just the hook text, strip numbering
        hooks = []
        for line in lines:
            # Remove leading number and dot/dash
            clean = line.lstrip("12345.-) ").strip().strip('"').strip("'")
            # Filter out lines that still contain filler
            line_lower = clean.lower()
            if not any(phrase in line_lower for phrase in ['here are', 'pinterest hooks', 'hooks:']):
                if clean and len(clean) > 3:
                    hooks.append(clean)

        # Match to angles
        result = {}
        for i, angle in enumerate(ANGLES):
            result[angle] = hooks[i] if i < len(hooks) else _fallback_hook(recipe, angle)

        return result

    except Exception as e:
        # Return fallback hooks so pipeline continues
        return {angle: _fallback_hook(recipe, angle) for angle in ANGLES}


def _fallback_hook(recipe: dict, angle: str) -> str:
    name = recipe.get("name", "Recipe")
    time = recipe.get("time", "")
    ing = recipe.get("ingredients", "")
    fallbacks = {
        "Time-saver": f"{time} {name}" if time else f"Quick {name} Recipe",
        "Lazy Dinner": f"Easy {name} No Fuss",
        "Weeknight Hero": f"Weeknight {name} Done Fast",
        "Ingredient-Count": f"Only {ing} Ingredients {name}" if ing else f"Simple {name}",
        "Core Method": f"The Only {name} You Need",
    }
    return fallbacks.get(angle, f"{name} Recipe")


def generate_description(recipe: dict, model: str = None) -> str:
    """
    Generate 1 SEO Pinterest description per recipe.
    Formula: [Keyword] + [benefit] + [use case]
    """
    name = recipe.get("name", "Recipe")
    time = recipe.get("time", "")
    benefit = recipe.get("benefit", "")
    url = recipe.get("url", "")

    prompt = f"""Write a single Pinterest SEO description for this recipe.

Recipe: {name}
Cook time: {time}
Benefit: {benefit}
URL: {url}

Formula to follow: [Main keyword phrase] + [key benefit] + [use case/occasion]
Requirements:
- 1-2 sentences only
- Under 150 characters total
- Include the recipe name naturally
- End with the URL if provided
- No hashtags in the description body
- No quotes, no preamble, just the description

Output ONLY the description. Nothing else."""

    try:
        raw = _generate(prompt, model)
        # Clean up any stray quotes or newlines
        desc = raw.replace('"', '').replace('\n', ' ').strip()
        return desc[:500]  # hard cap
    except Exception:
        base = f"{name} recipe ready in {time}." if time else f"{name} recipe."
        use = f" Perfect {benefit.lower()} meal." if benefit else " Great for weeknights."
        link = f" {url}" if url else ""
        return base + use + link
