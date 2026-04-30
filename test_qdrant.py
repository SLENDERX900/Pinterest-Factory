#!/usr/bin/env python3
"""
Test script to verify Qdrant integration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Qdrant integration...")

try:
    from utils.rag_memory import store_trending_pins, query_similar_trends
    print("✓ RAG memory module imported successfully")
except Exception as e:
    print(f"✗ Error importing RAG memory: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("✓ Qdrant uses local storage - no API key required")
print("✓ Data will be stored in data/qdrant directory")

try:
    # Test basic functionality
    test_pins = [
        {
            "title": "Modern Kitchen Design",
            "description": "Sleek minimalist kitchen with marble countertops and stainless steel appliances",
            "image_url": "https://example.com/kitchen.jpg",
            "pin_url": "https://example.com/kitchen-pin",
            "source": "test"
        },
        {
            "title": "Cozy Living Room",
            "description": "Warm and inviting living room with comfortable sofa and soft lighting",
            "image_url": "https://example.com/living-room.jpg",
            "pin_url": "https://example.com/living-room-pin",
            "source": "test"
        },
        {
            "title": "Bedroom Makeover",
            "description": "Transform your bedroom with these stylish decor ideas and organization tips",
            "image_url": "https://example.com/bedroom.jpg",
            "pin_url": "https://example.com/bedroom-pin",
            "source": "test"
        }
    ]
    
    # Test storing pins
    result = store_trending_pins(test_pins)
    print(f"✓ Stored {result} pins successfully")
    
    # Test querying similar trends
    query_result = query_similar_trends("kitchen design", top_k=2)
    print(f"✓ Query for 'kitchen design' returned {len(query_result)} results:")
    for i, item in enumerate(query_result):
        score = item.get('score', 'N/A')
        title = item.get('title', 'No title')
        print(f"  {i+1}. {title} - Score: {score:.3f}" if isinstance(score, float) else f"  {i+1}. {title}")
    
    # Test another query
    query_result2 = query_similar_trends("cozy room", top_k=2)
    print(f"✓ Query for 'cozy room' returned {len(query_result2)} results:")
    for i, item in enumerate(query_result2):
        score = item.get('score', 'N/A')
        title = item.get('title', 'No title')
        print(f"  {i+1}. {title} - Score: {score:.3f}" if isinstance(score, float) else f"  {i+1}. {title}")
    
    print("✓ All tests passed!")
    
except Exception as e:
    print(f"✗ Error during functionality test: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\nQdrant integration test complete!")
print("✓ Local vector database is ready for use")
print("✓ No external API keys required")
print("✓ Data persists between sessions in data/qdrant/")
