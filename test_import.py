#!/usr/bin/env python3
"""
Test script to verify the chromadb import fix
"""

print("Testing imports...")

try:
    from utils.rag_memory import store_trending_pins, query_similar_trends
    print("✓ RAG memory module imported successfully")
except Exception as e:
    print(f"✗ Error importing RAG memory: {e}")
    exit(1)

try:
    # Test basic functionality
    test_pins = [
        {
            "title": "Test Pin",
            "description": "A test pin for verification",
            "image_url": "https://example.com/image.jpg",
            "pin_url": "https://example.com/pin",
            "source": "test"
        }
    ]
    
    result = store_trending_pins(test_pins)
    print(f"✓ Stored {result} pins successfully")
    
    query_result = query_similar_trends("test query")
    print(f"✓ Query returned {len(query_result)} results")
    
    print("✓ All tests passed!")
    
except Exception as e:
    print(f"✗ Error during functionality test: {e}")
    exit(1)

print("Import fix verification complete!")
