#!/usr/bin/env python3
"""
Test script to verify Aura's conversation and MCP tools are working
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_conversation():
    """Test Aura's conversation endpoint"""
    url = "http://localhost:8000/conversation"
    headers = {"Content-Type": "application/json"}
    
    # Test messages
    test_messages = [
        {
            "user_id": "test_user_ty",
            "message": "Hello Aura! Can you tell me what internal MCP tools you have available?"
        },
        {
            "user_id": "test_user_ty", 
            "message": "Can you search my memories for our previous conversations about emotions?"
        },
        {
            "user_id": "test_user_ty",
            "message": "Please store this conversation in your memory system. I'm feeling happy today!"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test_data in test_messages:
            print(f"\n{'='*60}")
            print(f"Testing: {test_data['message']}")
            print(f"{'='*60}")
            
            try:
                async with session.post(url, json=test_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("\n✅ Success!")
                        print(f"\nAura's Response: {result['response']}")
                        print(f"\nEmotional State: {result['emotional_state']}")
                        print(f"Cognitive State: {result['cognitive_state']}")
                        print(f"Session ID: {result['session_id']}")
                    else:
                        print(f"❌ Error: {response.status}")
                        print(await response.text())
                        
            except Exception as e:
                print(f"❌ Exception: {e}")
                
            # Small delay between requests
            await asyncio.sleep(2)

async def test_mcp_tools():
    """Test MCP tool execution directly"""
    url = "http://localhost:8000/mcp/execute-tool"
    headers = {"Content-Type": "application/json"}
    
    # Test tools
    test_tools = [
        {
            "tool_name": "aura.query_emotional_states",
            "arguments": {},
            "user_id": "test_user_ty"
        },
        {
            "tool_name": "aura.search_memories",
            "arguments": {
                "user_id": "test_user_ty",
                "query": "happy emotions",
                "n_results": 3
            },
            "user_id": "test_user_ty"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test_data in test_tools:
            print(f"\n{'='*60}")
            print(f"Testing Tool: {test_data['tool_name']}")
            print(f"{'='*60}")
            
            try:
                async with session.post(url, json=test_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("\n✅ Tool executed successfully!")
                        print(json.dumps(result, indent=2))
                    else:
                        print(f"❌ Error: {response.status}")
                        print(await response.text())
                        
            except Exception as e:
                print(f"❌ Exception: {e}")
                
            await asyncio.sleep(1)

async def check_system_status():
    """Check MCP system status"""
    url = "http://localhost:8000/mcp/system-status"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    print("\n🔧 MCP System Status:")
                    print(f"Initialized: {result.get('initialized', False)}")
                    print(f"Connected Servers: {result.get('connected_servers', 0)}")
                    print(f"Total Tools: {result.get('total_tools', 0)}")
                    
                    # Check for Aura internal tools
                    tools_by_server = result.get('tools_by_server', {})
                    if 'aura-internal' in tools_by_server:
                        print(f"\n✅ Aura internal tools found: {len(tools_by_server['aura-internal'])}")
                        for tool in tools_by_server['aura-internal']:
                            print(f"  - {tool['name']}")
                    else:
                        print("\n⚠️ Aura internal tools NOT found in system status")
                else:
                    print(f"❌ Error checking system status: {response.status}")
        except Exception as e:
            print(f"❌ Exception checking system status: {e}")

async def main():
    """Run all tests"""
    print("🧪 Starting Aura Tests...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check system status first
    await check_system_status()
    
    # Test MCP tools directly
    print("\n\n" + "="*80)
    print("TESTING MCP TOOLS DIRECTLY")
    print("="*80)
    await test_mcp_tools()
    
    # Test conversations
    print("\n\n" + "="*80)
    print("TESTING CONVERSATIONS")
    print("="*80)
    await test_conversation()
    
    print("\n\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
