"""
Groq client with RAG-aware hook generation.
"""

from __future__ import annotations

import json
import os
from typing import Any

from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

ANGLES = ["Time-saver", "Lazy Dinner", "Weeknight Hero", "Ingredient-Count", "Core Method"]


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


def generate_hook_packages(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> list[dict[str, Any]]:
    trend_context = trend_context or []
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

Return ONLY valid JSON as an array of 5 objects.
Each object must include:
- angle (one of {ANGLES})
- hook (<= 8 words, humanized, specific)
- description (<= 150 chars, SEO-friendly)
- vibe_prompt (short visual direction for image generation)
"""
    try:
        raw = _generate(prompt, model=model)
        data = json.loads(raw)
        if isinstance(data, list) and len(data) >= 5:
            return data[:5]
    except Exception:
        pass

    name = recipe.get("name", "Recipe")
    return [
        {"angle": "Time-saver", "hook": f"Fast {name} in minutes", "description": f"Quick {name} for busy nights.", "vibe_prompt": "bright, efficient weeknight dinner"},
        {"angle": "Lazy Dinner", "hook": f"Low-effort {name} tonight", "description": f"Minimal effort {name} with big flavor.", "vibe_prompt": "cozy one-pan comfort mood"},
        {"angle": "Weeknight Hero", "hook": f"Weeknight {name} hero", "description": f"Reliable {name} for your weeknight rotation.", "vibe_prompt": "family dinner table warmth"},
        {"angle": "Ingredient-Count", "hook": f"Simple {name} ingredient win", "description": f"Easy pantry-friendly {name} anyone can make.", "vibe_prompt": "minimal ingredients styled cleanly"},
        {"angle": "Core Method", "hook": f"Best method for {name}", "description": f"Foolproof method to make {name} perfectly.", "vibe_prompt": "close-up food texture detail"},
    ]


def generate_hooks(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> dict[str, str]:
    packages = generate_hook_packages(recipe, trend_context=trend_context, model=model)
    hooks = {p.get("angle", ""): p.get("hook", "") for p in packages}
    result = {}
    for angle in ANGLES:
        result[angle] = hooks.get(angle, f"{recipe.get('name', 'Recipe')} idea")
    return result


def generate_description(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> str:
    packages = generate_hook_packages(recipe, trend_context=trend_context, model=model)
    return (packages[0].get("description", "") if packages else "").strip()
