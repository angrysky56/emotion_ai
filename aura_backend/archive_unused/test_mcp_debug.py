#!/usr/bin/env python3
"""
Targeted test to understand MCP tool execution issues
"""

import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_brave_search_directly():
    """Test the Brave search tool execution directly through MCP endpoint"""
    
    test_data = {
        "tool_name": "brave_web_search",
        "arguments": {
            "query": "Meta AI developer services"
        },
        "user_id": "test_user"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info("🔧 Testing direct MCP tool execution: %s", test_data['tool_name'])
            
            async with session.post(
                "http://localhost:8000/mcp/execute-tool",
                json=test_data
            ) as response:
                status = response.status
                result = await response.text()
                
                logger.info("📊 Response status: %s", status)
                
                if status == 200:
                    result_json = json.loads(result)
                    logger.info("✅ Tool execution response: %s", json.dumps(result_json, indent=2))
                else:
                    logger.error("❌ Tool execution failed: %s", result)
                    
        except Exception as e:
            logger.error("❌ Direct tool test failed: %s", e)
            import traceback
            traceback.print_exc()

async def test_conversation_debug():
    """Test conversation with debug logging to see tool execution flow"""
    
    test_data = {
        "user_id": "debug_user",
        "message": "Please use the brave_web_search tool to find information about Python FastAPI framework",
        "session_id": "debug_session"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info("🧪 Testing conversation with tool call request...")
            
            async with session.post(
                "http://localhost:8000/conversation",
                json=test_data,
                timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for tool execution
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "")
                    
                    logger.info("📝 Full response:")
                    logger.info(response_text)
                    
                    # Check for error indicators
                    error_phrases = [
                        "small issue",
                        "try again", 
                        "error",
                        "failed",
                        "couldn't",
                        "unable"
                    ]
                    
                    for phrase in error_phrases:
                        if phrase.lower() in response_text.lower():
                            logger.warning("⚠️ Detected error indicator: '%s'", phrase)
                            
                else:
                    error_text = await response.text()
                    logger.error("❌ Request failed: %s", error_text)
                    
        except Exception as e:
            logger.error("❌ Conversation test failed: %s", e)
            import traceback
            traceback.print_exc()

async def test_mcp_bridge_status():
    """Check MCP bridge status and available functions"""
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/mcp/bridge-status") as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("🌉 MCP Bridge Status: %s", result.get('status'))
                    logger.info("📊 Available functions: %s", result.get('available_functions', 0))
                    
                    if 'sample_functions' in result:
                        for func in result['sample_functions']:
                            if 'brave' in func.get('name', '').lower():
                                logger.info("🔍 Found Brave function: %s", func['name'])
                                logger.info("   Description: %s", func.get('description', 'N/A'))
                                logger.info("   Parameters: %s), indent=2)}", json.dumps(func.get('parameters', {)
                                
        except Exception as e:
            logger.error("❌ Bridge status check failed: %s", e)

async def main():
    """Run targeted tests"""
    logger.info("🔬 Starting targeted MCP issue investigation...")
    
    # Test 1: Check bridge status
    await test_mcp_bridge_status()
    
    # Test 2: Direct tool execution
    await test_brave_search_directly()
    
    # Test 3: Conversation with debug
    await test_conversation_debug()
    
    logger.info("\n✅ Investigation completed!")

if __name__ == "__main__":
    asyncio.run(main())
