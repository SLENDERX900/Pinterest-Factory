"""
utils/ollama_client.py
Thin wrapper around the Ollama HTTP API.
All LLM calls route through here so connection errors are caught once.
"""

import os
import json
import requests

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

ANGLES = ["Time-saver", "Lazy Dinner", "Weeknight Hero", "Ingredient-Count", "Core Method"]


# ── Health check ──────────────────────────────────────────────────────────────

def check_connection() -> tuple[bool, str]:
    """
    Returns (True, model_name) if Ollama is reachable and model is loaded.
    Returns (False, error_message) otherwise.
    """
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        if not models:
            return False, "Ollama is running but no models are loaded. Run: ollama pull llama3:8b-instruct-q4_K_M"

        # Check for exact model or any llama3 variant
        if any(OLLAMA_MODEL in m for m in models):
            return True, OLLAMA_MODEL
        llama3 = next((m for m in models if "llama3" in m.lower() or "llama-3" in m.lower()), None)
        if llama3:
            return True, llama3
        return False, f"Model '{OLLAMA_MODEL}' not found. Available: {', '.join(models[:3])}"

    except requests.ConnectionError:
        return False, f"Cannot connect to Ollama at {OLLAMA_HOST}. Is it running? Run: ollama serve"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def _generate(prompt: str, model: str = None) -> str:
    """Raw generate call. Returns response text or raises on failure."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.65,
            "num_predict": 512,
            "top_p": 0.9,
        },
    }
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json=payload,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


# ── Hook generation ───────────────────────────────────────────────────────────

def generate_hooks(recipe: dict, model: str = None) -> dict[str, str]:
    """
    Generate 5 Pinterest hooks for a single recipe.
    Returns {angle_name: hook_text} dict.
    Falls back to template hooks if Ollama fails.
    """
    name = recipe.get("name", "Recipe")
    time = recipe.get("time", "")
    ingredients = recipe.get("ingredients", "")
    benefit = recipe.get("benefit", "")

    prompt = f"""You are writing Pinterest pin text for nobscooking.com — a no-BS recipe site. Recipes are direct, technical, zero fluff.

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


# ── Description generation ────────────────────────────────────────────────────

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
