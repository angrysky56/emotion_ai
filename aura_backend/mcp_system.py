"""
MCP Integration Fix for Aura Backend
====================================

This module provides a proper integration between MCP client and Aura backend,
ensuring all MCP tools are available to the Gemini model.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_backend.aura_internal_tools import AuraInternalTools
from aura_backend.mcp_client import AuraMCPClient, AuraMCPIntegration
from aura_backend.mcp_to_gemini_bridge import MCPGeminiBridge

logger = logging.getLogger(__name__)

# Global MCP client instance
_mcp_client: Optional[AuraMCPClient] = None
_mcp_integration: Optional[AuraMCPIntegration] = None
_mcp_bridge: Optional[MCPGeminiBridge] = None
_initialized = False


async def initialize_mcp_system(
    aura_internal_tools: AuraInternalTools,
) -> Dict[str, Any]:
    """
    Initialize the complete MCP system with proper error handling

    Returns:
        Dict with initialization status and available tools
    """
    global _mcp_client, _mcp_integration, _mcp_bridge, _initialized

    if _initialized:
        logger.info("MCP system already initialized")
        return get_mcp_status()

    try:
        # Create MCP client with config
        config_path = Path(__file__).parent / "mcp_client_config.json"
        _mcp_client = AuraMCPClient(config_path=str(config_path))

        # Start the MCP client
        logger.info("🚀 Starting MCP client...")
        await _mcp_client.start()

        # Create integration
        _mcp_integration = AuraMCPIntegration(_mcp_client)

        # Get capabilities to verify
        capabilities = await _mcp_integration.get_available_capabilities()
        logger.info(
            f"✅ MCP client connected to {capabilities['connected_servers']}/{capabilities['total_servers']} servers"
        )
        logger.info("📦 Found %s tools total", capabilities['available_tools'])

        # Create MCP-Gemini bridge
        _mcp_bridge = MCPGeminiBridge(_mcp_client, aura_internal_tools)

        # Convert tools to Gemini format
        gemini_tools = await _mcp_bridge.convert_mcp_tools_to_gemini_functions()
        logger.info("🔧 Converted %s tools to Gemini format", len(gemini_tools))

        _initialized = True

        return {
            "status": "success",
            "connected_servers": capabilities["connected_servers"],
            "total_servers": capabilities["total_servers"],
            "available_tools": capabilities["available_tools"],
            "gemini_tools_count": len(gemini_tools),
            "tools_by_server": capabilities.get("tools_by_server", {}),
        }

    except Exception as e:
        logger.error("❌ Failed to initialize MCP system: %s", e)
        import traceback

        traceback.print_exc()

        return {
            "status": "error",
            "error": str(e),
            "connected_servers": 0,
            "total_servers": 0,
            "available_tools": 0,
            "gemini_tools_count": 0,
        }


def get_mcp_status() -> Dict[str, Any]:
    """Get current MCP system status"""
    if not _initialized or not _mcp_client:
        return {"initialized": False, "connected_servers": 0, "available_tools": 0}

    # Count connected servers
    connected = sum(1 for status in _mcp_client.connection_status.values() if status)
    total = len(_mcp_client.connection_status)

    # Count available tools
    tools_count = len(_mcp_client.tool_registry)

    return {
        "initialized": True,
        "connected_servers": connected,
        "total_servers": total,
        "available_tools": tools_count,
    }


def get_mcp_bridge() -> Optional[MCPGeminiBridge]:
    """Get the MCP-Gemini bridge instance"""
    return _mcp_bridge


def get_mcp_client() -> Optional[AuraMCPClient]:
    """Get the MCP client instance"""
    return _mcp_client


async def get_all_available_tools() -> List[Dict[str, Any]]:
    """Get all available tools from all sources"""
    tools = []

    # Get Aura internal tools if bridge and internal_tools are available
    if (
        _mcp_bridge
        and hasattr(_mcp_bridge, "aura_internal_tools")
        and _mcp_bridge.aura_internal_tools is not None
    ):
        internal_tools = _mcp_bridge.aura_internal_tools.get_tool_list()
        for tool in internal_tools:
            tools.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "server": tool.get("server", "aura-internal"),
                    "type": "internal",
                }
            )

    # Get MCP tools
    if _mcp_client:
        mcp_tools = await _mcp_client.list_all_tools()
        for tool_name, tool_info in mcp_tools.items():
            tools.append(
                {
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "server": tool_info.get("server", "unknown"),
                    "type": "mcp",
                }
            )

    return tools


async def shutdown_mcp_system():
    """Properly shutdown the MCP system"""
    global _mcp_client, _mcp_integration, _mcp_bridge, _initialized

    if _mcp_client:
        try:
            await _mcp_client.stop()
            logger.info("✅ MCP client stopped")
        except Exception as e:
            logger.error("Error stopping MCP client: %s", e)

    _mcp_client = None
    _mcp_integration = None
    _mcp_bridge = None
    _initialized = False
