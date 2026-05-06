#!/usr/bin/env python3
"""
Test script for MCP Bridge functionality
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
from mcp_client import AuraMCPClient
from mcp_to_gemini_bridge import MCPGeminiBridge
from aura_internal_tools import AuraInternalTools

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockVectorDB:
    """Mock vector database for testing"""
    async def search_conversations(self, query, user_id, n_results=5):
        return [{"content": f"Mock memory for query: {query}", "metadata": {"user_id": user_id}}]
    
    async def analyze_emotional_trends(self, user_id, days=7):
        return {"message": f"Mock emotional analysis for {user_id} over {days} days"}

class MockFileSystem:
    """Mock file system for testing"""
    async def load_user_profile(self, user_id):
        return {"user_id": user_id, "name": f"Mock User {user_id}"}

async def test_mcp_bridge():
    """Test the MCP bridge functionality"""
    logger.info("🧪 Starting MCP Bridge test...")
    
    try:
        # Create mock dependencies
        mock_vector_db = MockVectorDB()
        mock_file_system = MockFileSystem()
        
        # Create internal tools
        aura_internal_tools = AuraInternalTools(mock_vector_db, mock_file_system)
        logger.info("✅ Created Aura internal tools")
        
        # Create MCP client (this might fail if servers aren't running)
        config_path = Path(__file__).parent / "mcp_client_config.json"
        mcp_client = AuraMCPClient(config_path=str(config_path))
        
        # Try to start MCP client
        try:
            await mcp_client.start()
            logger.info("✅ MCP client started successfully")
        except Exception as e:
            logger.warning("⚠️ MCP client failed to start: %s", e)
            logger.info("🔄 Continuing with internal tools only...")
        
        # Create the bridge
        bridge = MCPGeminiBridge(mcp_client, aura_internal_tools)
        logger.info("✅ Created MCP-Gemini bridge")
        
        # Test the conversion method (this was the failing part)
        logger.info("🔧 Testing tool conversion...")
        gemini_tools = await bridge.convert_mcp_tools_to_gemini_functions()
        logger.info("✅ Successfully converted %s tools to Gemini format", len(gemini_tools))
        
        # Test getting available functions
        available_functions = bridge.get_available_functions()
        logger.info("📦 Available functions: %s", len(available_functions))
        
        for func in available_functions:
            logger.info("  - %s: %s...", func['name'], func['description'][:50])
        
        # Test tool execution with internal tool
        if available_functions:
            test_func = available_functions[0]
            logger.info("🧪 Testing tool execution: %s", test_func['name'])
            
            # Create a mock function call
            from google.genai import types
            
            # Test with a simple internal tool call
            if "emotional_states" in test_func['name'].lower():
                mock_call = types.FunctionCall(
                    name=test_func['name'],
                    args={}
                )
                
                result = await bridge.execute_function_call(mock_call, "test_user")
                logger.info("✅ Tool execution result: %s", result.success)
                if result.success:
                    logger.info("📄 Result: %s...", str(result.result)[:100])
                else:
                    logger.warning("❌ Error: %s", result.error)
        
        # Stop MCP client
        await mcp_client.stop()
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error("❌ Test failed: %s", e)
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_mcp_bridge())
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Tests failed!")
        sys.exit(1)
