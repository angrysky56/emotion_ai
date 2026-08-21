"""
Aura MCP Client Integration
==========================

This module enables Aura to act as an MCP client, connecting to and using
tools from other MCP servers. This expands Aura's capabilities by allowing
access to databases, filesystems, and other services through MCP.

Features:
- Connect to multiple MCP servers simultaneously
- Discover and use tools from connected servers
- Automatic retry and error handling
- Integration with Aura's memory and context systems
"""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# MCP client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Resource, TextContent, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class MCPServerConnection:
    """Represents a connection to an MCP server"""

    name: str
    command: str
    args: List[str]
    description: str
    enabled: bool = True
    session: Optional[ClientSession] = None
    tools: Dict[str, "Tool"] = field(default_factory=dict)
    resources: Dict[str, Resource] = field(default_factory=dict)
    connected: bool = False
    error_count: int = 0
    last_error: Optional[str] = None
    exit_stack: Optional[AsyncExitStack] = None


@dataclass
class MCPToolCall:
    """Represents a tool call to an MCP server"""

    server_name: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    result: Optional[Any] = None
    error: Optional[str] = None


# ============================================================================
# Aura MCP Client
# ============================================================================


class AuraMCPClient:
    """
    MCP Client for Aura that manages connections to multiple MCP servers
    and provides a unified interface for tool discovery and execution.
    """

    def __init__(self, config_path: str = "mcp_client_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.servers: Dict[str, MCPServerConnection] = {}
        self.exit_stack = AsyncExitStack()
        self._running = False
        self._connection_tasks: Set[asyncio.Task] = set()

        # Tool registry: maps qualified tool names to (server_name, tool)
        self.tool_registry: Dict[str, tuple[str, "Tool"]] = {}

        # Resource registry: maps qualified resource names to (server_name, resource)
        self.resource_registry: Dict[str, tuple[str, Resource]] = {}

        # Call history for debugging and analysis
        self.call_history: List[MCPToolCall] = []

        # Connection status tracking
        self.connection_status: Dict[str, bool] = {}
        self.last_error: Optional[str] = None

        logger.info("🔗 Initialized Aura MCP Client with config: %s", config_path)

    def _load_config(self) -> Dict[str, Any]:
        """Load MCP client configuration"""
        try:
            # 1. Try specified path
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return json.load(f)

            # 2. Try parent directory if not found (root check)
            root_path = self.config_path.parent.parent / self.config_path.name
            if root_path.exists():
                logger.info("📄 Found config in parent directory: %s", root_path)
                with open(root_path, "r") as f:
                    return json.load(f)

            logger.warning("Config file not found: %s", self.config_path)
            return {"mcpServers": {}, "client_settings": {}}
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            return {"mcpServers": {}, "client_settings": {}}

    async def start(self):
        """Start the MCP client and connect to all enabled servers"""
        if self._running:
            logger.warning("MCP Client is already running")
            return

        self._running = True
        logger.info("🚀 Starting Aura MCP Client...")

        # Clear connection statuses
        self.connection_status.clear()

        # Create server connections from config
        for server_name, server_config in self.config.get("mcpServers", {}).items():
            if server_config.get("enabled", True):
                # Store environment variables if specified

                self.servers[server_name] = MCPServerConnection(
                    name=server_name,
                    command=server_config["command"],
                    args=server_config.get("args", []),
                    description=server_config.get("description", ""),
                    enabled=True,
                    exit_stack=AsyncExitStack(),
                )

                # Track this server's connection status
                self.connection_status[server_name] = False

        # Connect to all enabled servers
        await self._connect_all_servers()

        # Log connection summary
        connected_count = sum(1 for s in self.connection_status.values() if s)
        total_count = len(self.connection_status)
        logger.info(
            f"✅ MCP Client startup complete: {connected_count}/{total_count} servers connected"
        )

    async def _connect_all_servers(self):
        """Connect to all enabled MCP servers"""
        tasks = []
        for server_name, server in self.servers.items():
            if server.enabled and not server.connected:
                task = asyncio.create_task(self._connect_to_server(server_name))
                self._connection_tasks.add(task)
                task.add_done_callback(self._connection_tasks.discard)
                tasks.append(task)

        if tasks:
            # Important: We gather in the main task to keep the stacks tied to the main task if possible,
            # or we ensure they are managed per server.
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for server_name, result in zip(self.servers.keys(), results, strict=False):
                if isinstance(result, Exception):
                    logger.error("❌ Failed to connect to %s: %s", server_name, result)

    async def _connect_to_server(self, server_name: str):
        """Connect to a specific MCP server"""
        server = self.servers.get(server_name)
        if not server:
            return

        try:
            logger.info("🔌 Connecting to MCP server: %s", server_name)

            # Create server parameters with environment variables if specified
            env_vars = None
            # Get the environment variables from the config
            if "env" in self.config.get("mcpServers", {}).get(server_name, {}):
                env_vars = self.config["mcpServers"][server_name]["env"]
                logger.info(
                    f"Using environment variables for {server_name}: {list(env_vars.keys())}"
                )

            # Create server parameters
            server_params = StdioServerParameters(
                command=server.command, args=server.args, env=env_vars
            )

            # Connect to server using its own exit stack
            # This ensures that contexts are properly managed and avoids anyio cross-task errors
            # if we close them from the task that created them.
            if server.exit_stack is None:
                server.exit_stack = AsyncExitStack()
            transport = await server.exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            # Create session
            session = await server.exit_stack.enter_async_context(
                ClientSession(transport[0], transport[1])
            )

            # Initialize the connection
            await session.initialize()

            server.session = session
            server.connected = True
            server.error_count = 0
            self.connection_status[server_name] = True

            # Discover tools and resources
            await self._discover_server_capabilities(server_name)

            logger.info(
                f"✅ Connected to {server_name} - Found {len(server.tools)} tools, {len(server.resources)} resources"
            )

        except Exception as e:
            server.connected = False
            server.error_count += 1
            server.last_error = str(e)
            self.connection_status[server_name] = False
            self.last_error = f"Failed to connect to {server_name}: {e}"
            logger.error("❌ Failed to connect to %s: %s", server_name, e)
            # Don't raise, just log the error to allow other servers to connect

    async def _discover_server_capabilities(self, server_name: str):
        """Discover tools and resources from a connected server"""
        server = self.servers.get(server_name)
        if not server or not server.session:
            return

        try:
            # List tools
            tools_result = await server.session.list_tools()
            for tool in tools_result.tools:
                qualified_name = f"{server_name}_{tool.name}"
                server.tools[tool.name] = tool
                self.tool_registry[qualified_name] = (server_name, tool)
                logger.debug("  📦 Tool: %s - %s", qualified_name, tool.description)

            # List resources
            try:
                resources_result = await server.session.list_resources()
                for resource in resources_result.resources:
                    qualified_name = f"{server_name}_{resource.name}"
                    server.resources[resource.name] = resource
                    self.resource_registry[qualified_name] = (server_name, resource)
                    logger.debug("  📄 Resource: %s", qualified_name)
            except Exception as e:
                logger.debug("Server %s doesn't support resources: %s", server_name, e)

        except Exception as e:
            logger.error("Failed to discover capabilities for %s: %s", server_name, e)

    async def list_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools from all connected servers"""
        all_tools = {}

        for qualified_name, (server_name, tool) in self.tool_registry.items():
            all_tools[qualified_name] = {
                "server": server_name,
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
                "connected": self.servers[server_name].connected,
            }

        return all_tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool from any connected MCP server.

        Args:
            tool_name: Either a qualified name (server_toolname) or just toolname
            arguments: Arguments to pass to the tool

        Returns:
            The result from the tool call
        """
        # Handle both qualified and unqualified tool names
        if "_" in tool_name and tool_name in self.tool_registry:
            # Qualified name
            server_name, tool = self.tool_registry[tool_name]
        else:
            # Search for unqualified name
            matches = [
                (sn, t)
                for qn, (sn, t) in self.tool_registry.items()
                if t.name == tool_name
            ]
            if not matches:
                raise ValueError(f"Tool not found: {tool_name}")
            elif len(matches) > 1:
                servers = [m[0] for m in matches]
                raise ValueError(
                    f"Tool {tool_name} found in multiple servers: {servers}. Use qualified name."
                )
            server_name, tool = matches[0]

        # Check if server is connected
        server = self.servers.get(server_name)
        if not server or not server.connected:
            raise ConnectionError(f"Server {server_name} is not connected")

        # Record the call
        call_record = MCPToolCall(
            server_name=server_name, tool_name=tool.name, arguments=arguments
        )
        self.call_history.append(call_record)

        try:
            # Make the tool call
            logger.info("🔧 Calling tool %s on server %s", tool.name, server_name)
            if server.session is None:
                raise ValueError(f"Session is not initialized for server {server_name}")
            result = await server.session.call_tool(tool.name, arguments)

            # Extract text content from result
            if hasattr(result, "content") and result.content:
                text_content = []
                for content in result.content:
                    if isinstance(content, TextContent):
                        text_content.append(content.text)
                call_record.result = (
                    "\n".join(text_content) if text_content else str(result)
                )
            else:
                call_record.result = str(result)

            logger.info("✅ Tool call successful: %s", tool.name)
            return call_record.result

        except Exception as e:
            call_record.error = str(e)
            logger.error("❌ Tool call failed: %s", e)
            raise

    async def read_resource(self, resource_uri: str) -> Any:
        """Read a resource from any connected MCP server"""
        # Find which server can handle this resource
        for server_name, server in self.servers.items():
            if server.connected and server.session:
                try:
                    from pydantic.networks import AnyUrl

                    uri_obj = AnyUrl(resource_uri)
                    result = await server.session.read_resource(uri_obj)
                    logger.info(
                        "📄 Read resource %s from %s", resource_uri, server_name
                    )
                    return result
                except Exception:
                    continue

        raise ValueError(f"No server could read resource: {resource_uri}")

    async def stop(self):
        """Stop the MCP client and disconnect from all servers"""
        if not self._running:
            return

        logger.info("🛑 Stopping Aura MCP Client...")
        self._running = False

        # Cancel any pending connection tasks
        for task in self._connection_tasks:
            task.cancel()

        # Clean up connections per server
        for server in self.servers.values():
            if server.exit_stack:
                try:
                    await server.exit_stack.aclose()
                except Exception as e:
                    logger.error("Error closing stack for %s: %s", server.name, e)
            server.connected = False
            server.session = None

        await self.exit_stack.aclose()

        logger.info("✅ MCP Client stopped")

    def get_call_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tool call history"""
        history = []
        for call in self.call_history[-limit:]:
            history.append(
                {
                    "timestamp": call.timestamp.isoformat(),
                    "server": call.server_name,
                    "tool": call.tool_name,
                    "arguments": call.arguments,
                    "success": call.error is None,
                    "error": call.error,
                }
            )
        return history


# ============================================================================
# Integration with Aura
# ============================================================================


class AuraMCPIntegration:
    """
    Integration layer between Aura and the MCP Client.
    This class provides high-level methods for Aura to use MCP tools.
    """

    def __init__(self, mcp_client: AuraMCPClient):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_available_capabilities(self) -> Dict[str, Any]:
        """Get a summary of all available MCP capabilities for Aura"""
        tools = await self.mcp_client.list_all_tools()

        capabilities = {
            "connected_servers": len(
                [s for s in self.mcp_client.servers.values() if s.connected]
            ),
            "total_servers": len(self.mcp_client.servers),
            "available_tools": len([t for t in tools.values() if t["connected"]]),
            "tools_by_server": {},
        }

        # Group tools by server
        for _tool_name, tool_info in tools.items():
            server = tool_info["server"]
            if server not in capabilities["tools_by_server"]:
                capabilities["tools_by_server"][server] = []
            capabilities["tools_by_server"][server].append(
                {"name": tool_info["name"], "description": tool_info["description"]}
            )

        return capabilities


# ============================================================================
# Standalone Testing
# ============================================================================


async def test_mcp_client():
    """Test the MCP client functionality"""
    client = AuraMCPClient()
    integration = AuraMCPIntegration(client)

    try:
        # Start the client
        await client.start()

        # List available tools
        tools = await client.list_all_tools()
        print("\n🔧 Available Tools:")
        for name, info in tools.items():
            print(f"  - {name}: {info['description']}")

        # Get capabilities summary
        capabilities = await integration.get_available_capabilities()
        print("\n📊 MCP Capabilities:")
        print(
            f"  Connected servers: {capabilities['connected_servers']}/{capabilities['total_servers']}"
        )
        print(f"  Available tools: {capabilities['available_tools']}")

    finally:
        await client.stop()


if __name__ == "__main__":
    # Run test
    asyncio.run(test_mcp_client())
