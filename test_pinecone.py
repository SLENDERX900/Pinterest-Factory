#!/usr/bin/env python3
"""
Test script to verify Pinecone integration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Pinecone integration...")

try:
    from utils.rag_memory import store_trending_pins, query_similar_trends
    print("✓ RAG memory module imported successfully")
except Exception as e:
    print(f"✗ Error importing RAG memory: {e}")
    exit(1)

# Check if Pinecone API key is configured
api_key = os.getenv('PINECONE_API_KEY')
if api_key and api_key != 'your_pinecone_api_key_here':
    print("✓ Pinecone API key found")
else:
    print("⚠ Pinecone API key not configured - will use fallback storage")
    print("To get a free API key: https://app.pinecone.io/")

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
        }
    ]
    
    # Test storing pins
    result = store_trending_pins(test_pins)
    print(f"✓ Stored {result} pins successfully")
    
    # Test querying similar trends
    query_result = query_similar_trends("kitchen design", top_k=2)
    print(f"✓ Query returned {len(query_result)} results:")
    for i, item in enumerate(query_result):
        print(f"  {i+1}. {item.get('title', 'No title')} - {item.get('score', 'N/A')}")
    
    print("✓ All tests passed!")
    
except Exception as e:
    print(f"✗ Error during functionality test: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\nPinecone integration test complete!")
print("Note: Without a valid PINECONE_API_KEY, the system uses fallback in-memory storage.")
