#!/usr/bin/env python3
"""
Debug script to test MCP client initialization
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_client import AuraMCPClient, AuraMCPIntegration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_initialization():
    """Test MCP client initialization and tool discovery"""
    
    # Create MCP client
    config_path = Path(__file__).parent / "mcp_client_config.json"
    client = AuraMCPClient(config_path=str(config_path))
    
    try:
        # Start the client
        logger.info("🚀 Starting MCP client...")
        await client.start()
        
        # Create integration
        integration = AuraMCPIntegration(client)
        
        # Get capabilities
        capabilities = await integration.get_available_capabilities()
        
        print("\n" + "="*60)
        print("MCP CLIENT STATUS")
        print("="*60)
        print(f"Connected servers: {capabilities['connected_servers']}/{capabilities['total_servers']}")
        print(f"Available tools: {capabilities['available_tools']}")
        
        # List all tools
        tools = await client.list_all_tools()
        
        print("\n" + "="*60)
        print("AVAILABLE TOOLS BY SERVER")
        print("="*60)
        
        tools_by_server = {}
        for tool_name, tool_info in tools.items():
            server = tool_info['server']
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append({
                'name': tool_name,
                'description': tool_info['description'][:80] + '...' if len(tool_info['description']) > 80 else tool_info['description']
            })
        
        for server, server_tools in tools_by_server.items():
            print(f"\n{server}: {len(server_tools)} tools")
            for tool in server_tools[:5]:  # Show first 5 tools
                print(f"  - {tool['name']}: {tool['description']}")
            if len(server_tools) > 5:
                print(f"  ... and {len(server_tools) - 5} more tools")
        
        print("\n" + "="*60)
        print("CONNECTION STATUS")
        print("="*60)
        for server_name, connected in client.connection_status.items():
            status = "✅ Connected" if connected else "❌ Failed"
            print(f"{server_name}: {status}")
            
    except Exception as e:
        logger.error("❌ Test failed: %s", e)
        import traceback
        traceback.print_exc()
    finally:
        # Stop the client
        await client.stop()

if __name__ == "__main__":
    asyncio.run(test_mcp_initialization())
