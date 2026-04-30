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
    """
    Enhanced hook generation with Pinterest semantic context analysis
    """
    trend_context = trend_context or []
    
    # DEBUG: Enhanced context analysis
    print(f"\n🔍 ENHANCED GROQ CONTEXT ANALYSIS:")
    print(f"   Recipe: {recipe.get('name', 'Unknown')}")
    print(f"   Trend context items: {len(trend_context)}")
    
    if trend_context:
        print(f"   Using Pinterest semantic context: YES")
        print(f"   Pinterest pins being analyzed:")
        
        # Analyze Pinterest-specific metrics
        total_saves = 0
        high_engagement_pins = 0
        
        for i, pin in enumerate(trend_context[:3]):  # Show first 3
            title = pin.get('title', 'No title')[:40]
            desc = pin.get('description', 'No description')[:40]
            saves = pin.get('saves', '0')
            engagement = pin.get('engagement_score', 0)
            
            if saves != 'RSS':
                total_saves += 1
            if engagement > 0.5:
                high_engagement_pins += 1
                
            print(f"     {i+1}. {title} | {desc} | 💾{saves} | ⭐{engagement:.2f}")
        
        print(f"   📊 Pinterest metrics: {total_saves} pins with saves, {high_engagement_pins} high engagement")
    else:
        print(f"   Using Pinterest semantic context: NO - will fallback to generic patterns")
    
    # Enhanced context block with Pinterest-specific formatting
    context_lines = []
    for i, pin in enumerate(trend_context[:5]):
        title = pin.get('title', '')
        desc = pin.get('description', '')
        saves = pin.get('saves', '')
        engagement = pin.get('engagement_score', 0)
        
        # Create rich context line with Pinterest metrics
        context_line = f"- Pin {i+1}: {title}"
        if desc:
            context_line += f" | {desc}"
        if saves and saves != 'RSS':
            context_line += f" | 💾{saves} saves"
        if engagement > 0.5:
            context_line += " | ⭐HIGH ENGAGEMENT"
        
        context_lines.append(context_line[:280])
    
    context_block = "\n".join(context_lines) if context_lines else "- (no Pinterest context found)"
    prompt = f"""
Target recipe:
- Name: {recipe.get("name","")}
- Time: {recipe.get("time","")}
- Ingredient count: {recipe.get("ingredients","")}
- Benefit: {recipe.get("benefit","")}
- URL: {recipe.get("url","")}

Similar trending Pinterest pins with engagement metrics:
{context_block}

ANALYZE the Pinterest pins above. Pay special attention to:
- Pins with HIGH ENGAGEMENT (⭐) - these are proven winners
- Save counts (💾) - higher saves indicate proven appeal
- Title patterns that drive engagement
- Description psychology that converts
- Hashtag strategies that work

LEARN from successful Pinterest psychology:
- What emotional triggers work best?
- What benefit-focused language converts?
- What hashtag combinations drive discovery?
- What call-to-action patterns get saves?

Return ONLY valid JSON as an array of 5 objects.
Each object must include:
- angle (one of {ANGLES})
- hook (<= 8 words, humanized, specific, emotional)
- description (<= 150 chars, Pinterest-optimized with proven psychology)
- vibe_prompt (short visual direction for image generation)

For descriptions: Apply PROVEN Pinterest psychology:
- Use emotional triggers from high-engagement pins
- Include 2-3 trending hashtags from successful pins
- Add benefit-focused language that drives saves
- Use call-to-action patterns that convert
- Mirror the psychology of pins with 💾 high save counts
- Focus on the emotional benefits, not just features
"""
    try:
        print(f"📤 Sending prompt to Groq with {len(trend_context)} trend items...")
        raw = _generate(prompt, model=model)
        print(f"📥 Raw Groq response received (length: {len(raw)})")
        
        data = json.loads(raw)
        if isinstance(data, list) and len(data) >= 5:
            print(f"✅ Groq SUCCESS: Generated {len(data)} valid packages")
            # Log first package to verify context usage
            first_pkg = data[0]
            desc = first_pkg.get('description', '')
            has_hashtags = '#' in desc
            has_trend_words = any(word in desc.lower() for word in ['recipe', 'easy', 'quick', 'best'])
            print(f"   First description: {desc[:60]}...")
            print(f"   Contains hashtags: {has_hashtags}")
            print(f"   Contains trend keywords: {has_trend_words}")
            return data[:5]
        else:
            print(f"❌ Groq INVALID: Returned {len(data) if data else 0} packages (need ≥5)")
    except Exception as e:
        print(f"❌ Groq FAILED: {e}")
        print(f"   Will use fallback patterns")
    
    print(f"🔄 FALLBACK TRIGGERED: Using predefined patterns")

    name = recipe.get("name", "Recipe")
    benefit = recipe.get("benefit", "Quick Weeknight")
    return [
        {"angle": "Time-saver", "hook": f"Fast {name} in minutes", "description": f"Quick {name} recipe! #easydinner #weeknightmeals #simplerecipes", "vibe_prompt": "bright, efficient weeknight dinner"},
        {"angle": "Lazy Dinner", "hook": f"Low-effort {name} tonight", "description": f"Effortless {name} with amazing flavor! #lazycooking #minimalcleanup", "vibe_prompt": "cozy one-pan comfort mood"},
        {"angle": "Weeknight Hero", "hook": f"Weeknight {name} hero", "description": f"Family-approved {name}! Save this recipe for busy nights! #familydinner", "vibe_prompt": "family dinner table warmth"},
        {"angle": "Ingredient-Count", "hook": f"Simple {name} ingredient win", "description": f"5-ingredient {name} anyone can make! #simplecooking #pantryrecipes", "vibe_prompt": "minimal ingredients styled cleanly"},
        {"angle": "Core Method", "hook": f"Best method for {name}", "description": f"Perfect {name} every time! Try this foolproof method! #cookingtips", "vibe_prompt": "close-up food texture detail"},
    ]


def generate_hooks(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> dict[str, str]:
    packages = generate_hook_packages(recipe, trend_context=trend_context, model=model)
    hooks = {p.get("angle", ""): p.get("hook", "") for p in packages}
    result = {}
    for angle in ANGLES:
        result[angle] = hooks.get(angle, f"{recipe.get('name', 'Recipe')} idea")
    return result


def debug_groq_context(recipe: dict, trend_context: list[dict] | None = None) -> None:
    """Debug function to show exactly what context Groq receives."""
    print("\n" + "="*80)
    print("🔍 GROQ CONTEXT DEBUG REPORT")
    print("="*80)
    
    print(f"\n📋 RECIPE INPUT:")
    print(f"   Name: {recipe.get('name', 'N/A')}")
    print(f"   Time: {recipe.get('time', 'N/A')}")
    print(f"   Ingredients: {recipe.get('ingredients', 'N/A')}")
    print(f"   Benefit: {recipe.get('benefit', 'N/A')}")
    print(f"   URL: {recipe.get('url', 'N/A')}")
    
    print(f"\n🌐 TRENDING CONTEXT ANALYSIS:")
    if trend_context and len(trend_context) > 0:
        print(f"   ✅ Context available: {len(trend_context)} items")
        print(f"   📊 Context quality analysis:")
        
        # Analyze context quality
        total_hashtags = 0
        total_keywords = 0
        avg_desc_length = 0
        
        for i, pin in enumerate(trend_context[:5]):
            title = pin.get('title', '')
            desc = pin.get('description', '')
            
            # Count hashtags
            import re
            hashtags = len(re.findall(r'#\w+', desc))
            total_hashtags += hashtags
            
            # Count keywords
            keywords = len([kw for kw in ['easy', 'quick', 'simple', 'best', 'perfect'] if kw in desc.lower()])
            total_keywords += keywords
            
            avg_desc_length += len(desc)
            
            print(f"     Pin {i+1}: {title[:40]}... | {desc[:40]}... | #{hashtags} hashtags")
        
        avg_desc_length = avg_desc_length // len(trend_context[:5]) if trend_context else 0
        print(f"   📈 Context metrics:")
        print(f"      Total hashtags: {total_hashtags}")
        print(f"      Total keywords: {total_keywords}")
        print(f"      Avg description length: {avg_desc_length} chars")
        
        # Predict Groq success
        if len(trend_context) >= 3 and total_hashtags > 0:
            print(f"   🎯 Prediction: HIGH chance of Groq using context")
        elif len(trend_context) >= 1:
            print(f"   ⚠️  Prediction: MEDIUM chance of Groq using context")
        else:
            print(f"   ❌ Prediction: LOW chance - will likely fallback")
            
    else:
        print(f"   ❌ NO CONTEXT AVAILABLE - Groq will definitely fallback")
    
    print("\n" + "="*80)

def generate_description(recipe: dict, trend_context: list[dict] | None = None, model: str | None = None) -> str:
    """Generate enhanced Pinterest SEO description that learns from trending context."""
    
    # Debug context before generation
    debug_groq_context(recipe, trend_context)
    
    packages = generate_hook_packages(recipe, trend_context=trend_context, model=model)
    base_description = (packages[0].get("description", "") if packages else "").strip()
    
    # If we have trending context, enhance the description further
    if trend_context and len(trend_context) > 0:
        enhanced = enhance_pinterest_seo_description(base_description, recipe, trend_context)
        print(f"\n🔧 ENHANCED DESCRIPTION: {enhanced}")
        return enhanced
    
    print(f"\n🔧 BASE DESCRIPTION (no enhancement): {base_description}")
    return base_description

def enhance_pinterest_seo_description(base_desc: str, recipe: dict, trend_context: list[dict]) -> str:
    """Enhance base description with Pinterest SEO optimization learned from trends."""
    # Extract successful patterns from trending pins
    trending_hashtags = extract_trending_hashtags(trend_context)
    trending_keywords = extract_trending_keywords(trend_context)
    
    # Build enhanced description
    name = recipe.get("name", "")
    benefit = recipe.get("benefit", "")
    
    # Start with compelling keywords
    enhanced_desc = f"{name} recipe"
    
    # Add benefit if not already in description
    if benefit.lower() not in base_desc.lower():
        enhanced_desc += f" - {benefit}"
    
    # Add trending keywords naturally
    for keyword in trending_keywords[:2]:  # Add top 2 keywords
        if keyword.lower() not in enhanced_desc.lower():
            enhanced_desc += f" {keyword}"
    
    # Add call-to-action if missing
    if not any(cta in enhanced_desc.lower() for cta in ["save", "try", "make", "pin"]):
        enhanced_desc += " - Save this recipe!"
    
    # Add trending hashtags
    hashtags = " ".join(trending_hashtags[:3])  # Top 3 hashtags
    if hashtags:
        enhanced_desc += f" {hashtags}"
    
    # Ensure under 150 characters
    if len(enhanced_desc) > 150:
        enhanced_desc = enhanced_desc[:147].rsplit(' ', 1)[0] + "..."
    
    return enhanced_desc

def extract_trending_hashtags(trend_context: list[dict]) -> list[str]:
    """Extract hashtags from trending pin descriptions."""
    hashtags = []
    for pin in trend_context[:5]:  # Analyze top 5 trending pins
        desc = pin.get('description', '').lower()
        # Find hashtags
        import re
        found_hashtags = re.findall(r'#\w+', desc)
        hashtags.extend(found_hashtags)
    
    # Remove duplicates and return most common
    from collections import Counter
    hashtag_counts = Counter(hashtags)
    return [tag for tag, _ in hashtag_counts.most_common(5)]

def extract_trending_keywords(trend_context: list[dict]) -> list[str]:
    """Extract popular keywords from trending pin titles and descriptions."""
    keywords = []
    for pin in trend_context[:5]:
        title = pin.get('title', '').lower()
        desc = pin.get('description', '').lower()
        
        # Common Pinterest food keywords to look for
        food_keywords = ['easy', 'quick', 'simple', 'healthy', 'delicious', 'homemade', 
                       'best', 'perfect', 'amazing', 'flavor', 'recipe', 'dinner', 'lunch',
                       'family', 'kids', 'weeknight', 'comfort', 'creamy', 'crispy']
        
        text = f"{title} {desc}"
        for keyword in food_keywords:
            if keyword in text and keyword not in keywords:
                keywords.append(keyword)
    
    return keywords[:5]  # Return top 5 keywords
