#!/usr/bin/env python3
"""
Test script to validate MCP tool response formatting fix
"""

import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_conversation_with_tool_call():
    """Test conversation endpoint with a request that triggers tool use"""
    
    # Test data
    test_requests = [
        {
            "user_id": "test_user",
            "message": "Can you search for information about Meta AI developer services?",
            "session_id": "test_session_1"
        },
        {
            "user_id": "test_user", 
            "message": "What MCP tools do you have available?",
            "session_id": "test_session_2"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test_data in test_requests:
            try:
                logger.info("\n🧪 Testing: %s", test_data['message'])
                
                async with session.post(
                    "http://localhost:8000/conversation",
                    json=test_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Check response structure
                        assert "response" in result, "Missing 'response' field"
                        assert "emotional_state" in result, "Missing 'emotional_state' field"
                        assert "cognitive_state" in result, "Missing 'cognitive_state' field"
                        assert "session_id" in result, "Missing 'session_id' field"
                        
                        # Check for malformed responses
                        response_text = result["response"]
                        
                        # Check for escaped newlines or raw tool output
                        if "\\n" in response_text:
                            logger.warning("⚠️ Found escaped newlines in response")
                        
                        if "Tool " in response_text and "executed successfully:" in response_text:
                            logger.warning("⚠️ Raw tool output detected in response")
                        
                        # Log the cleaned response
                        logger.info("✅ Response structure is valid")
                        logger.info("📝 Response preview: %s...", response_text[:200])
                        
                        # Check emotional state
                        emotional_state = result["emotional_state"]
                        logger.info("🎭 Emotional state: %s (%s)", emotional_state['name'], emotional_state['intensity'])
                        
                    else:
                        error_text = await response.text()
                        logger.error("❌ Request failed with status %s: %s", response.status, error_text)
                        
            except Exception as e:
                logger.error("❌ Test failed: %s", e)

async def test_mcp_status():
    """Test MCP system status endpoint"""
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info("\n🧪 Testing MCP system status...")
            
            async with session.get("http://localhost:8000/mcp/system-status") as response:
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info("✅ MCP Status: %s", result.get('status', 'unknown'))
                    logger.info("📊 Total tools: %s", result.get('total_tools', 0))
                    
                    if "tools_by_server" in result:
                        for server, tools in result["tools_by_server"].items():
                            logger.info("  - %s: %s tools", server, len(tools))
                else:
                    logger.error("❌ Status check failed with status %s", response.status)
                    
        except Exception as e:
            logger.error("❌ MCP status test failed: %s", e)

async def main():
    """Run all tests"""
    logger.info("🚀 Starting MCP fix validation tests...")
    
    # Give the server a moment to start if just launched
    await asyncio.sleep(2)
    
    # Test MCP status first
    await test_mcp_status()
    
    # Test conversation with tool calls
    await test_conversation_with_tool_call()
    
    logger.info("\n✅ Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
