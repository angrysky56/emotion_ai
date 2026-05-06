#!/usr/bin/env python3
"""
Test script to validate MCP brave_search tool fixes
Tests parameter handling and response formatting
"""

import asyncio
import logging
from mcp_system import initialize_mcp_system, get_mcp_bridge, shutdown_mcp_system
from mcp_to_gemini_bridge import format_function_call_result_for_model, ToolExecutionResult
from google.genai import types

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_brave_search_integration():
    """Test the brave_search tool with the fixed parameter handling"""

    print("\n🧪 Testing MCP Brave Search Integration\n")

    # Initialize MCP system
    print("1️⃣ Initializing MCP system...")
    # Import or create an AuraInternalTools instance as required by your application
    from mcp_system import AuraInternalTools

    # TODO: Replace the following mock or placeholder objects with your actual implementations
    mock_vector_db = None  # Replace with your actual vector_db instance
    mock_file_system = None  # Replace with your actual file_system instance

    aura_internal_tools = AuraInternalTools(vector_db=mock_vector_db, file_system=mock_file_system)
    status = await initialize_mcp_system(aura_internal_tools=aura_internal_tools)

    if status["status"] != "success":
        print(f"❌ Failed to initialize MCP system: {status}")
        return

    print(f"✅ MCP system initialized: {status['connected_servers']}/{status['total_servers']} servers")

    # Get the bridge
    bridge = get_mcp_bridge()
    if not bridge:
        print("❌ Failed to get MCP bridge")
        return

    print("✅ Got MCP bridge instance")

    # Test parameter handling
    print("\n2️⃣ Testing parameter handling...")

    # Create a mock function call for brave_search
    function_call = types.FunctionCall(
        name="brave_search_brave_web_search",  # The clean name used by Gemini
        args={"query": "Meta AI developer services"}
    )

    # Execute the function call
    try:
        query = function_call.args['query'] if function_call.args and 'query' in function_call.args else "<no query>"
        print(f"📤 Executing brave_search with query: {query}")
        result = await bridge.execute_function_call(function_call, user_id="test_user")

        print("\n📥 Execution result:")
        print(f"   Success: {result.success}")
        print(f"   Tool name: {result.tool_name}")
        print(f"   Execution time: {result.execution_time:.2f}s")

        if result.success:
            print(f"\n📊 Result type: {type(result.result)}")
            print(f"📊 Result keys: {list(result.result.keys()) if isinstance(result.result, dict) else 'N/A'}")

            # Test formatting
            print("\n3️⃣ Testing response formatting...")
            formatted = format_function_call_result_for_model(result)
            print("\n📝 Formatted result (first 500 chars):")
            print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
        else:
            print(f"❌ Error: {result.error}")

    except Exception as e:
        print(f"❌ Exception during execution: {e}")
        import traceback
        traceback.print_exc()

    # Test formatting with mock results
    print("\n\n4️⃣ Testing response formatting with mock data...")

    # Mock brave_search result
    mock_brave_result = {
        "result": {
            "web": {
                "results": [
                    {
                        "title": "Meta AI - Build with Llama",
                        "url": "https://ai.meta.com/",
                        "description": "Meta AI offers developer tools and services..."
                    },
                    {
                        "title": "Meta AI Studio",
                        "url": "https://ai.meta.com/studio",
                        "description": "Create custom AI assistants with Meta AI Studio..."
                    }
                ]
            }
        }
    }

    mock_execution_result = ToolExecutionResult(
        tool_name="brave_search_brave_web_search",
        success=True,
        result=mock_brave_result,
        execution_time=0.5
    )

    formatted_mock = format_function_call_result_for_model(mock_execution_result)
    print("\n📝 Formatted mock result:")
    print(formatted_mock)

    # Shutdown
    print("\n\n5️⃣ Shutting down MCP system...")
    await shutdown_mcp_system()
    print("✅ Test complete!")

async def test_internal_tool():
    """Test internal tool parameter handling"""
    print("\n\n🧪 Testing Internal Tool Parameter Handling\n")

    # This would test the aura internal tools
    # For now, just showing the structure
    print("Internal tools use direct parameter passing (no 'params' wrapper)")
    print("Example: search_aura_memories(user_id='test', query='hello', n_results=5)")

if __name__ == "__main__":
    asyncio.run(test_brave_search_integration())
