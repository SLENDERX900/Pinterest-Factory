#!/usr/bin/env python3
"""
Pinterest Factory - Complete Autonomous Pinterest Marketing Loop
$0-budget recipe content creation and Pinterest automation
"""

import os
import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all Pinterest Factory components
from utils.pinterest_scraper import scrape_pinterest_trends_sync
from utils.rag_memory import store_pinterest_pins, query_similar_trends
from utils.groq_client import generate_hook_packages
from utils.image_generator import generate_hook_images
from utils.scheduler import schedule_pinterest_factory_batch
from utils.sitemap_memory import log_scraping_session, get_domain_stats

class PinterestFactory:
    """
    Complete Pinterest Factory automation engine
    """
    
    def __init__(self):
        print("🏭 Pinterest Factory Engine Initialized")
        print("=" * 60)
        
        # Verify environment setup
        self._verify_environment()
        
        # Initialize components
        self.scraped_pins = []
        self.generated_hooks = []
        self.generated_images = []
        self.scheduling_results = {}
        
    def _verify_environment(self):
        """Verify all required environment variables and dependencies"""
        print("🔧 Verifying environment setup...")
        
        required_vars = {
            'GROQ_API_KEY': 'Groq API key for hook generation',
            'PINTEREST_ACCESS_TOKEN': 'Pinterest API token for scheduling',
            'PINTEREST_BOARD_ID': 'Pinterest board ID for posting',
            'NOTION_TOKEN': 'Notion API token for tracking',
            'NOTION_DATABASE_ID': 'Notion database ID for recipe tracking'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"❌ {var}: {description}")
            else:
                print(f"✅ {var}: Configured")
        
        if missing_vars:
            print("\n⚠️  Missing environment variables:")
            for var in missing_vars:
                print(f"   {var}")
            print("\nSome features may not work without these variables.")
        
        # Test optional Hugging Face API
        if os.getenv('HUGGINGFACE_API_KEY'):
            print("✅ HUGGINGFACE_API_KEY: Image generation available")
        else:
            print("⚠️  HUGGINGFACE_API_KEY: Using fallback image generation")
    
    async def process_recipe_url(self, recipe_url: str, recipe_data: Dict) -> Dict:
        """
        Complete Pinterest Factory workflow for a single recipe
        """
        print(f"\n🚀 Starting Pinterest Factory for: {recipe_data.get('name', 'Unknown recipe')}")
        print(f"📎 Recipe URL: {recipe_url}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # STEP 1: Scrape Pinterest trends
            print("\n📌 STEP 1: Scraping Pinterest Trends")
            scraped_pins = await self._scrape_pinterest_trends(recipe_url)
            
            if not scraped_pins:
                print("⚠️  No Pinterest trends found, using fallback patterns")
            
            # STEP 2: Store in RAG memory
            print("\n🧠 STEP 2: Storing in RAG Memory")
            if scraped_pins:
                stored_count = store_pinterest_pins(scraped_pins)
                print(f"✅ Stored {stored_count} Pinterest pins in memory")
            
            # STEP 3: Generate enhanced hooks
            print("\n🤖 STEP 3: Generating AI Hooks")
            hooks = self._generate_enhanced_hooks(recipe_data, scraped_pins)
            
            if not hooks:
                raise Exception("Failed to generate hooks")
            
            # STEP 4: Generate tailored images
            print("\n🎨 STEP 4: Generating Tailored Images")
            images = self._generate_tailored_images(recipe_data, hooks)
            
            # STEP 5: Schedule pins
            print("\n📅 STEP 5: Scheduling Pinterest Pins")
            scheduling_results = self._schedule_pins(recipe_data, hooks)
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Compile results
            results = {
                "success": True,
                "recipe_name": recipe_data.get('name', 'Unknown'),
                "recipe_url": recipe_url,
                "processing_time": total_time,
                "scraped_pins": len(scraped_pins),
                "generated_hooks": len(hooks),
                "generated_images": len(images),
                "scheduling": scheduling_results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            print(f"\n🎉 Pinterest Factory completed successfully!")
            print(f"⏱️  Total processing time: {total_time:.2f} seconds")
            print(f"📊 Results: {len(scraped_pins)} trends, {len(hooks)} hooks, {len(images)} images")
            
            return results
            
        except Exception as e:
            error_msg = f"Pinterest Factory failed: {str(e)}"
            print(f"\n❌ {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "recipe_name": recipe_data.get('name', 'Unknown'),
                "processing_time": time.time() - start_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _scrape_pinterest_trends(self, recipe_url: str) -> List[Dict]:
        """Scrape Pinterest trends with fallback"""
        try:
            pins = await scrape_pinterest_trends_sync(recipe_url, max_pins=10)
            print(f"✅ Scraped {len(pins)} Pinterest pins")
            return pins
        except Exception as e:
            print(f"❌ Pinterest scraping failed: {e}")
            return []
    
    def _generate_enhanced_hooks(self, recipe_data: Dict, trend_context: List[Dict]) -> List[Dict]:
        """Generate AI hooks with Pinterest semantic context"""
        try:
            hooks = generate_hook_packages(recipe_data, trend_context=trend_context)
            print(f"✅ Generated {len(hooks)} enhanced hooks")
            return hooks
        except Exception as e:
            print(f"❌ Hook generation failed: {e}")
            return []
    
    def _generate_tailored_images(self, recipe_data: Dict, hooks: List[Dict]) -> List[Dict]:
        """Generate tailored images for each hook"""
        recipe_image_url = recipe_data.get('image_url', '')
        
        if not recipe_image_url:
            print("⚠️  No recipe image provided, skipping image generation")
            return []
        
        try:
            images = generate_hook_images(recipe_image_url, hooks)
            print(f"✅ Generated {len(images)} tailored images")
            return images
        except Exception as e:
            print(f"❌ Image generation failed: {e}")
            return []
    
    def _schedule_pins(self, recipe_data: Dict, hooks: List[Dict]) -> Dict:
        """Schedule pins with Pinterest API"""
        try:
            results = schedule_pinterest_factory_batch(recipe_data, hooks)
            
            if results.get('success'):
                print(f"✅ Scheduled {len(results.get('scheduled_pins', []))} pins")
            else:
                print(f"⚠️  Scheduling issues: {results.get('error', 'Unknown error')}")
            
            return results
        except Exception as e:
            print(f"❌ Pin scheduling failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_factory_stats(self) -> Dict:
        """Get comprehensive Pinterest Factory statistics"""
        try:
            from utils.sitemap_memory import get_recent_analytics
            
            # Get recent analytics
            analytics = get_recent_analytics(limit=10)
            
            # Calculate stats
            total_sessions = len(analytics)
            success_rate = sum(a.get('success_rate', 0) for a in analytics) / max(1, total_sessions)
            avg_duration = sum(a.get('duration_seconds', 0) for a in analytics) / max(1, total_sessions)
            
            return {
                "total_sessions": total_sessions,
                "success_rate": success_rate,
                "avg_duration_seconds": avg_duration,
                "recent_sessions": analytics[:5],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Stats unavailable: {str(e)}"}

# Convenience functions for easy integration
async def process_recipe_complete(recipe_url: str, recipe_data: Dict) -> Dict:
    """
    Convenience function for complete Pinterest Factory processing
    """
    factory = PinterestFactory()
    return await factory.process_recipe_url(recipe_url, recipe_data)

def process_recipe_sync(recipe_url: str, recipe_data: Dict) -> Dict:
    """
    Synchronous wrapper for Pinterest Factory processing
    """
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(process_recipe_complete(recipe_url, recipe_data))
    except Exception as e:
        return {
            "success": False,
            "error": f"Async processing failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Quick test function
def quick_test():
    """Quick test of Pinterest Factory components"""
    print("🧪 Pinterest Factory Quick Test")
    print("=" * 40)
    
    # Test data
    test_recipe = {
        "name": "Test Chocolate Chip Cookies",
        "time": "25 mins",
        "ingredients": "8",
        "benefit": "Easy Dessert",
        "url": "https://example.com/cookies",
        "image_url": "https://example.com/cookie-image.jpg"
    }
    
    try:
        factory = PinterestFactory()
        print("✅ Factory initialized successfully")
        
        # Test stats
        stats = factory.get_factory_stats()
        print(f"✅ Stats available: {len(stats)} metrics")
        
        print("\n🎉 Quick test passed! Ready for full processing.")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False

if __name__ == "__main__":
    # Run quick test
    quick_test()
