"""
MCP Integration Fix for Aura Backend
====================================

This module provides a proper integration between MCP client and Aura backend,
ensuring all MCP tools are available to the Gemini model.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from aura_backend.aura_internal_tools import AuraInternalTools
from aura_backend.mcp_client import AuraMCPClient, AuraMCPIntegration
from aura_backend.mcp_to_gemini_bridge import MCPGeminiBridge
from aura_backend.providers.base import JsonValue, ToolDefinition
from aura_backend.providers.tools import (
    ToolCatalog,
    ToolExecutionLimits,
    ToolExecutor,
    ToolRegistration,
    ToolSource,
)

logger = logging.getLogger(__name__)

# Global MCP client instance
_mcp_client: Optional[AuraMCPClient] = None
_mcp_integration: Optional[AuraMCPIntegration] = None
_mcp_bridge: Optional[MCPGeminiBridge] = None
_aura_internal_tools: Optional[AuraInternalTools] = None
_initialized = False


class _MCPToolClient(Protocol):
    """Structural subset required by the provider-neutral MCP surface."""

    async def list_all_tools(self) -> Mapping[str, Mapping[str, Any]]: ...

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any: ...


class _InternalToolRegistry(Protocol):
    """Structural subset required by the provider-neutral internal surface."""

    def get_tool_list(self) -> List[Dict[str, Any]]: ...

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any: ...


async def initialize_mcp_system(
    aura_internal_tools: AuraInternalTools,
) -> Dict[str, Any]:
    """
    Initialize the complete MCP system with proper error handling

    Returns:
        Dict with initialization status and available tools
    """
    global _mcp_client, _mcp_integration, _mcp_bridge, _aura_internal_tools, _initialized

    # Retain internal-tool ownership even when optional MCP startup is unavailable.
    _aura_internal_tools = aura_internal_tools

    if _initialized:
        logger.info("MCP system already initialized")
        return get_mcp_status()

    try:
        # Create MCP client with config
        # 1. Try project root first
        root_config = Path(__file__).parent.parent / "mcp_client_config.json"
        # 2. Try package directory
        local_config = Path(__file__).parent / "mcp_client_config.json"

        if root_config.exists():
            config_path = root_config
            logger.info("📄 Using MCP config from project root: %s", config_path)
        else:
            config_path = local_config
            logger.info("📄 Using MCP config from package directory: %s", config_path)

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
        logger.info("📦 Found %s tools total", capabilities["available_tools"])

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


def _object_schema(value: object) -> object:
    """Supply the legacy empty-object default without weakening validation."""
    if isinstance(value, Mapping) and value:
        return value
    return {"type": "object", "properties": {}}


async def get_provider_tool_catalog(
    *,
    mcp_client: _MCPToolClient | None = None,
    internal_tools: _InternalToolRegistry | None = None,
) -> ToolCatalog:
    """Enumerate available MCP/internal tools into one immutable neutral catalog.

    Discovery failures from the optional sources produce no registrations and do
    not expose source exception text.  Invalid definitions still fail closed when
    :class:`ToolRegistration` validates their names and schemas.
    """
    active_mcp: _MCPToolClient | None = mcp_client or _mcp_client
    active_internal: _InternalToolRegistry | None = (
        internal_tools or _aura_internal_tools
    )
    registrations: list[ToolRegistration] = []

    if active_internal is not None:
        try:
            internal_definitions = active_internal.get_tool_list()
        except Exception:
            logger.warning("Internal tool catalog is unavailable")
            internal_definitions = []
        for item in internal_definitions:
            registrations.append(
                ToolRegistration(
                    definition=ToolDefinition(
                        name=item["name"],
                        description=item.get("description", ""),
                        input_schema=_object_schema(item.get("parameters")),
                    ),
                    source=ToolSource.INTERNAL,
                    server=item.get("server", "aura-internal"),
                )
            )

    if active_mcp is not None:
        try:
            mcp_definitions = await active_mcp.list_all_tools()
        except Exception:
            logger.warning("Optional MCP tool catalog is unavailable")
            mcp_definitions = {}
        for qualified_name, item in mcp_definitions.items():
            if item.get("connected", True) is not True:
                continue
            registrations.append(
                ToolRegistration(
                    definition=ToolDefinition(
                        name=qualified_name,
                        description=item.get("description", ""),
                        input_schema=_object_schema(item.get("input_schema")),
                    ),
                    source=ToolSource.MCP,
                    server=item.get("server", "unknown"),
                )
            )

    return ToolCatalog(tuple(registrations))


def _mutable_arguments(arguments: Mapping[str, JsonValue]) -> Dict[str, Any]:
    """Copy immutable validated arguments for legacy execution entry points."""

    def thaw(value: JsonValue) -> Any:
        if isinstance(value, Mapping):
            return {key: thaw(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [thaw(item) for item in value]
        return value

    return {key: thaw(value) for key, value in arguments.items()}


def get_provider_tool_executor(
    catalog: ToolCatalog,
    *,
    mcp_client: _MCPToolClient | None = None,
    internal_tools: _InternalToolRegistry | None = None,
    limits: ToolExecutionLimits | None = None,
) -> ToolExecutor:
    """Return a neutral executor routed only by catalog registration metadata."""
    active_mcp: _MCPToolClient | None = mcp_client or _mcp_client
    active_internal: _InternalToolRegistry | None = (
        internal_tools or _aura_internal_tools
    )

    async def dispatch(
        registration: ToolRegistration,
        arguments: Mapping[str, JsonValue],
    ) -> object:
        mutable = _mutable_arguments(arguments)
        if registration.source is ToolSource.INTERNAL:
            if active_internal is None:
                raise RuntimeError("internal tool registry unavailable")
            return await active_internal.execute_tool(
                registration.original_name,
                mutable,
            )
        if registration.source is ToolSource.MCP:
            if active_mcp is None:
                raise RuntimeError("MCP tool client unavailable")
            return await active_mcp.call_tool(
                registration.original_name,
                mutable,
            )
        raise RuntimeError("unsupported tool source")

    return ToolExecutor(catalog, dispatch, limits=limits)


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
    global _mcp_client, _mcp_integration, _mcp_bridge, _aura_internal_tools, _initialized

    if _mcp_client:
        try:
            await _mcp_client.stop()
            logger.info("✅ MCP client stopped")
        except Exception as e:
            logger.error("Error stopping MCP client: %s", e)

    _mcp_client = None
    _mcp_integration = None
    _mcp_bridge = None
    _aura_internal_tools = None
    _initialized = False
