"""
generator.py - STEP 3: Tailored Hook Generation (Groq)
Feeds Recipe Data + Learning Summary into Groq to generate 5 distinct hooks
with uniquely tailored Pin Descriptions for each hook
"""

import os
import json
from typing import List, Dict, Any
from groq import Groq


class HookGenerator:
    """
    Generates tailored Pinterest hooks and descriptions using Groq AI
    """
    
    def __init__(self):
        self.client = None
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Groq client"""
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables")
            
            self.client = Groq(api_key=api_key)
            print(f"✅ Groq client initialized with model: {self.model}")
            
        except Exception as e:
            print(f"❌ Groq client initialization failed: {e}")
    
    def generate_tailored_hooks(
        self, 
        recipe_data: Dict, 
        learning_summary: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate 5 distinct hooks with tailored descriptions
        Uses Recipe Data + Learning Summary from reasoning loop
        """
        print(f"🤖 Generating tailored hooks for: {recipe_data.get('name', 'Unknown recipe')}")
        
        try:
            # Construct the prompt with recipe data and learning summary
            prompt = self._construct_generation_prompt(recipe_data, learning_summary)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Pinterest content strategist. Generate highly engaging, humanized hooks and descriptions."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            hooks_data = self._parse_response(response_text)
            
            print(f"✅ Generated {len(hooks_data)} tailored hooks")
            return hooks_data
            
        except Exception as e:
            print(f"❌ Hook generation failed: {e}")
            return []
    
    def _construct_generation_prompt(self, recipe_data: Dict, learning_summary: Dict[str, Any]) -> str:
        """Construct the detailed prompt for Groq"""
        
        # Extract recipe information
        recipe_name = recipe_data.get('name', 'Unknown Recipe')
        recipe_time = recipe_data.get('time', 'Unknown time')
        recipe_ingredients = recipe_data.get('ingredients', 'Unknown')
        recipe_benefit = recipe_data.get('benefit', 'Delicious')
        
        # Extract learning summary information
        summary = learning_summary.get('learning_summary', 'No learning summary available')
        triggers = learning_summary.get('psychological_triggers', [])
        insights = learning_summary.get('engagement_insights', [])
        
        prompt = f"""
Generate 5 distinct, highly humanized Pinterest hooks and descriptions for this recipe:

**RECIPE DATA:**
- Name: {recipe_name}
- Time: {recipe_time}
- Ingredients: {recipe_ingredients}
- Benefit: {recipe_benefit}

**LEARNING SUMMARY FROM PINTEREST ANALYSIS:**
{summary}

**PSYCHOLOGICAL TRIGGERS IDENTIFIED:**
{', '.join(triggers) if triggers else 'None identified'}

**ENGAGEMENT INSIGHTS:**
{', '.join(insights) if insights else 'No insights available'}

**REQUIREMENTS:**
1. Generate exactly 5 distinct hooks, each with a different angle
2. Each hook must be highly humanized, catchy, and Pinterest-optimized
3. For EACH hook, generate a uniquely tailored Pin Description that matches that specific hook's angle
4. Use the psychological triggers and engagement insights from the learning summary
5. Make hooks emotionally compelling and action-oriented
6. Descriptions should be SEO-optimized and promote the Pinterest pin

**OUTPUT FORMAT:**
Return a JSON array with exactly 5 objects, each containing:
- "hook": The catchy Pinterest hook
- "description": The tailored pin description for that specific hook
- "angle": The psychological angle used (e.g., urgency, curiosity, social proof)

Example format:
[
  {{
    "hook": "Your 5-minute dinner secret is here",
    "description": "This {recipe_name} takes just {recipe_time} and uses only {recipe_ingredients} ingredients. The {benefit} benefit makes it perfect for busy weeknights. Save this recipe now!",
    "angle": "curiosity"
  }}
]

Generate the JSON array now:
"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> List[Dict[str, str]]:
        """Parse Groq response and extract JSON array"""
        try:
            # Try to extract JSON from response
            # Look for JSON array pattern
            import re
            
            # Find JSON array in response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                hooks_data = json.loads(json_str)
                
                # Validate structure
                validated_hooks = []
                for hook_data in hooks_data:
                    if isinstance(hook_data, dict) and 'hook' in hook_data and 'description' in hook_data:
                        validated_hooks.append({
                            'hook': hook_data['hook'],
                            'description': hook_data['description'],
                            'angle': hook_data.get('angle', 'general')
                        })
                
                return validated_hooks[:5]  # Ensure exactly 5 hooks
            
            # Fallback: try to parse entire response as JSON
            try:
                hooks_data = json.loads(response_text)
                if isinstance(hooks_data, list):
                    return hooks_data[:5]
            except:
                pass
            
            print("⚠️ Could not parse JSON from response, using fallback")
            return self._generate_fallback_hooks()
            
        except Exception as e:
            print(f"❌ Response parsing failed: {e}")
            return self._generate_fallback_hooks()
    
    def _generate_fallback_hooks(self) -> List[Dict[str, str]]:
        """Generate fallback hooks if parsing fails"""
        return [
            {
                "hook": "The secret ingredient that makes this recipe unforgettable",
                "description": "Discover the magic behind this amazing recipe. Perfect for any occasion and guaranteed to impress.",
                "angle": "curiosity"
            },
            {
                "hook": "Why this recipe has 10,000+ saves on Pinterest",
                "description": "Join thousands of home cooks who love this recipe. Simple ingredients, incredible results.",
                "angle": "social_proof"
            },
            {
                "hook": "You'll never believe how easy this is to make",
                "description": "Ready in minutes with ingredients you already have. The perfect solution for busy weeknights.",
                "angle": "urgency"
            },
            {
                "hook": "The recipe that changed my dinner routine forever",
                "description": "Once you try this, you'll make it every week. Family-approved and absolutely delicious.",
                "angle": "authority"
            },
            {
                "hook": "Don't scroll past this - it's exactly what you need",
                "description": "The perfect recipe for today. Quick, easy, and incredibly satisfying. Save it now!",
                "angle": "urgency"
            }
        ]


# Convenience function for the complete 3-step pipeline
def generate_pinterest_factory_hooks(recipe_data: Dict, learning_summary: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Complete pipeline: Generate 5 tailored hooks with descriptions
    """
    generator = HookGenerator()
    return generator.generate_tailored_hooks(recipe_data, learning_summary)


# Main pipeline function that orchestrates all 3 steps
def run_pinterest_factory_pipeline(recipe_url: str, recipe_data: Dict) -> Dict[str, Any]:
    """
    Complete Pinterest Factory Pipeline - All 3 Steps
    Step 1: Contextual Scraping → Step 2: Reasoning Agent → Step 3: Hook Generation
    """
    print("🏭 Starting Pinterest Factory Pipeline")
    print("=" * 60)
    
    # STEP 1: Contextual Scraping
    print("\n📌 STEP 1: Contextual Scraping")
    from scraper import ContextualScraper
    scraper = ContextualScraper()
    pinterest_pins = scraper.scrape_pinterest_context(recipe_url, max_pins=10)
    
    if not pinterest_pins:
        return {
            'success': False,
            'error': 'No Pinterest pins scraped',
            'step_1_status': 'failed'
        }
    
    print(f"✅ Step 1 Complete: {len(pinterest_pins)} pins scraped")
    
    # STEP 2: Reasoning Agent & Memory
    print("\n🧠 STEP 2: Reasoning Agent & Memory")
    from memory_agent import MemoryAgent
    memory_agent = MemoryAgent()
    
    # Process pins through semantic chunking
    memory_agent.process_pinterest_pins(pinterest_pins)
    
    # Run reasoning verification loop
    query = f"{recipe_data.get('name', '')} {recipe_data.get('benefit', '')}"
    learning_summary = memory_agent.reasoning_verification_loop(query, top_k=5)
    
    print(f"✅ Step 2 Complete: Learning summary generated")
    
    # STEP 3: Tailored Hook Generation
    print("\n🤖 STEP 3: Tailored Hook Generation")
    hooks = generate_pinterest_factory_hooks(recipe_data, learning_summary)
    
    if not hooks:
        return {
            'success': False,
            'error': 'Hook generation failed',
            'step_1_status': 'success',
            'step_2_status': 'success',
            'step_3_status': 'failed'
        }
    
    print(f"✅ Step 3 Complete: {len(hooks)} hooks generated")
    
    # Final result
    result = {
        'success': True,
        'recipe_name': recipe_data.get('name', 'Unknown'),
        'pinterest_pins_scraped': len(pinterest_pins),
        'learning_summary': learning_summary.get('learning_summary', ''),
        'generated_hooks': hooks,
        'psychological_triggers': learning_summary.get('psychological_triggers', []),
        'engagement_insights': learning_summary.get('engagement_insights', []),
        'step_1_status': 'success',
        'step_2_status': 'success', 
        'step_3_status': 'success'
    }
    
    print("\n🎉 Pinterest Factory Pipeline Complete!")
    print(f"📊 Generated {len(hooks)} tailored hooks with descriptions")
    
    return result
