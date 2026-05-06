#!/usr/bin/env python3
"""
Test script to verify NumPy type serialization fixes
"""

import asyncio
import json
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the serialization fix
from json_serialization_fix import ensure_json_serializable

def test_numpy_serialization():
    """Test that NumPy types can be serialized after conversion"""
    print("🧪 Testing NumPy type serialization fixes...")
    
    test_cases = [
        ("int64", np.int64(42)),
        ("float64", np.float64(3.14159)),
        ("array", np.array([1, 2, 3])),
        ("bool_", np.bool_(True)),
        ("nested dict", {"value": np.int64(100), "array": np.array([1.1, 2.2, 3.3])}),
        ("nested list", [np.int64(1), np.float64(2.5), {"val": np.int32(3)}]),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_value in test_cases:
        try:
            # Test direct JSON serialization (should fail)
            try:
                json.dumps(test_value)
                print(f"❌ {name}: Direct serialization should have failed but didn't")
                failed += 1
                continue
            except (TypeError, ValueError):
                pass  # Expected to fail
            
            # Test with conversion
            cleaned_value = ensure_json_serializable(test_value)
            json_str = json.dumps(cleaned_value)
            print(f"✅ {name}: Successfully serialized after conversion")
            print(f"   Original type: {type(test_value)}")
            print(f"   Cleaned type: {type(cleaned_value)}")
            print(f"   JSON: {json_str[:50]}...")
            passed += 1
            
        except Exception as e:
            print(f"❌ {name}: Failed with error: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0

async def test_embedding_conversion():
    """Test that embeddings are properly converted"""
    print("\n🧪 Testing embedding conversion...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Create a small test embedding
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_text = "This is a test message"
        
        # Generate embedding
        embedding = model.encode(test_text)
        print(f"✅ Generated embedding with shape: {embedding.shape}")
        print(f"   Embedding type: {type(embedding)}")
        print(f"   Element type: {type(embedding[0])}")
        
        # Test conversion methods
        # Method 1: Simple tolist()
        simple_list = embedding.tolist()
        print(f"   Simple tolist type: {type(simple_list[0])}")
        
        # Method 2: Explicit float conversion (what we're using in the fix)
        safe_list = [float(x) for x in embedding.tolist()]
        print(f"   Safe conversion type: {type(safe_list[0])}")
        
        # Verify JSON serialization
        json.dumps(safe_list)
        print("✅ Embedding successfully serialized to JSON")
        
        return True
        
    except ImportError:
        print("⚠️ sentence_transformers not available, skipping embedding test")
        return True
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False

async def test_tool_result_cleaning():
    """Test that tool results with NumPy types are cleaned"""
    print("\n🧪 Testing tool result cleaning...")
    
    # Simulate a tool result that might contain NumPy types
    mock_tool_result = {
        "status": "success",
        "count": np.int64(42),
        "scores": np.array([0.95, 0.87, 0.92]),
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "confidence": np.float64(0.95),
            "features": {
                "extracted": np.int32(15),
                "processed": True
            }
        },
        "memories": [
            {
                "content": "Test memory",
                "similarity": np.float32(0.89),
                "metadata": {
                    "emotion_intensity": np.int64(3)
                }
            }
        ]
    }
    
    try:
        # This should fail
        json.dumps(mock_tool_result)
        print("❌ Mock tool result should have failed JSON serialization")
        return False
    except (TypeError, ValueError):
        print("✅ Mock tool result correctly fails without cleaning")
    
    # Clean the result
    cleaned_result = ensure_json_serializable(mock_tool_result)
    
    try:
        json_str = json.dumps(cleaned_result, indent=2)
        print("✅ Cleaned tool result successfully serialized")
        print(f"   Sample JSON:\n{json_str[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to serialize cleaned result: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting NumPy serialization fix tests...\n")
    
    results = []
    
    # Run basic serialization tests
    results.append(test_numpy_serialization())
    
    # Run embedding conversion test
    results.append(await test_embedding_conversion())
    
    # Run tool result cleaning test
    results.append(await test_tool_result_cleaning())
    
    # Summary
    print("\n" + "="*50)
    if all(results):
        print("✅ All tests passed! The NumPy serialization fixes should work.")
        print("\n💡 The fixes will:")
        print("   1. Clean tool results before sending to Gemini")
        print("   2. Convert embeddings to pure Python floats")
        print("   3. Handle nested NumPy types in complex data structures")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    print("\n📝 Next steps:")
    print("   1. Restart the Aura backend to apply the fixes")
    print("   2. Test with a real conversation that uses tools")
    print("   3. Verify that subsequent chats save successfully")

if __name__ == "__main__":
    asyncio.run(main())
