#!/usr/bin/env python3
"""
Test script to validate MCP to Gemini Bridge improvements
"""

import sys
import os
import asyncio
import traceback

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aura_backend'))

async def test_imports():
    """Test that all imports work correctly"""
    print("🧪 Testing imports...")

    try:
        from mcp_to_gemini_bridge import MCPGeminiBridge
        print("✅ Successfully imported MCPGeminiBridge")

        # Test that the class can be instantiated (with mock client)
        class MockMCPClient:
            async def list_all_tools(self):
                return {}

            async def call_tool(self, tool_name, args):
                return {"result": f"Mock result for {tool_name}"}

        bridge = MCPGeminiBridge(MockMCPClient())
        print("✅ Successfully created MCPGeminiBridge instance")

        # Test configuration constants
        from mcp_to_gemini_bridge import (
            TOOL_CALL_MAX_RETRIES,
            TOOL_CALL_TIMEOUT
        )
        print(f"✅ Configuration loaded: timeout={TOOL_CALL_TIMEOUT}s, retries={TOOL_CALL_MAX_RETRIES}")

        # Test performance tracking
        stats = bridge.get_tool_performance_stats()
        print(f"✅ Performance stats available: {len(stats)} metrics")

        # Test large result handling
        large_result = {"data": "x" * 10000}  # 10KB of data
        processed = bridge._handle_large_result(large_result, "test_tool")
        print(f"✅ Large result handling works: {type(processed)}")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

async def test_json_serialization():
    """Test JSON serialization improvements"""
    print("\n🧪 Testing JSON serialization...")

    try:
        from mcp_to_gemini_bridge import ensure_json_serializable
        import numpy as np

        # Test NumPy type handling
        test_data = {
            "int64": np.int64(42),
            "float32": np.float32(3.14),
            "array": np.array([1, 2, 3]),
            "nested": {
                "bool": np.bool_(True),
                "complex": np.complex64(1 + 2j)
            }
        }

        serializable_data = ensure_json_serializable(test_data)

        import json
        json_str = json.dumps(serializable_data)
        print(f"✅ JSON serialization successful: {len(json_str)} chars")

        return True

    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        return False

async def test_heartbeat_system():
    """Test heartbeat monitoring system"""
    print("\n🧪 Testing heartbeat system...")

    try:
        from mcp_to_gemini_bridge import MCPGeminiBridge

        class MockMCPClient:
            async def list_all_tools(self):
                return {}

        bridge = MCPGeminiBridge(MockMCPClient())

        # Test heartbeat with short operation
        async def quick_operation():
            await asyncio.sleep(0.1)
            return "quick_result"

        result = await bridge._execute_with_heartbeat(quick_operation(), "test_tool")
        print(f"✅ Heartbeat system works: {result}")

        return True

    except Exception as e:
        print(f"❌ Heartbeat test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting MCP Bridge improvement validation tests...\n")

    tests = [
        test_imports,
        test_json_serialization,
        test_heartbeat_system
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            success = await test()
            if success:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! MCP Bridge improvements are working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
