"""
MCP Client Integration for Aura
==============================

This module provides MCP client functionality for Aura to connect to any MCP servers
configured in the system. It's designed to be flexible and work with any MCP server,
not hardcode specific ones.
"""

import asyncio
import atexit
import importlib.util
import json
import logging

# Import Python standard library modules for subprocess management
import os
import shutil
import signal
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

# Configure logging first
logger = logging.getLogger(__name__)

# ============================================================================
# MCP Client imports - Dynamic loading to handle missing dependencies
# ============================================================================

try:
    # Try fastmcp first (newer package)
    if importlib.util.find_spec("fastmcp") is not None:
        HAS_FASTMCP = True
        logger.info("✅ FastMCP library available")
    else:
        HAS_FASTMCP = False
        logger.warning("⚠️ FastMCP library not available - trying standard MCP")
except Exception:
    HAS_FASTMCP = False
    logger.warning("⚠️ FastMCP library not available - trying standard MCP")

try:
    # Try standard MCP package
    HAS_MCP = True
    try:
        from mcp.client.stdio import (  # Import stdio_client for standard MCP
            stdio_client,
        )

        logger.info("✅ MCP library loaded successfully")
    except ImportError as e:
        HAS_MCP = False
        stdio_client = None
        logger.warning("⚠️ stdio_client not available in MCP library: %s", e)
        stdio_client = None
        if not HAS_FASTMCP:
            logger.warning("⚠️ stdio_client not available in MCP library: %s", e)
except ImportError as e:
    HAS_MCP = False
    if not HAS_FASTMCP:
        logger.warning("⚠️ Standard MCP library not available: %s", e)

# Determine if any MCP version is available
MCP_AVAILABLE = HAS_FASTMCP or HAS_MCP

# Try direct subprocess communication as a fallback
if not MCP_AVAILABLE:
    import json

    logger.warning("⚠️ Falling back to direct subprocess communication for MCP servers")

# Define fallback classes if needed
if not MCP_AVAILABLE:

    class Tool:
        def __init__(self, name="", description="", inputSchema=None):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema or {}

    class Resource:
        def __init__(self, name="", uri="", description=""):
            self.name = name
            self.uri = uri
            self.description = description

    class StdioServerParameters:
        def __init__(self, command, args=None, env=None):
            self.command = command
            self.args = args or []
            self.env = env or {}


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""

    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None


@dataclass
class MCPTool:
    """Represents an MCP tool"""

    name: str
    description: str
    server: str
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class MCPPrompt:
    """Represents an MCP prompt"""

    name: str
    description: str
    server: str
    arguments: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# MCP Client Manager
# ============================================================================


class DirectMCPManager:
    """
    Direct MCP communication manager using subprocess.
    This is a fallback when MCP libraries are not available.
    """

    def __init__(self):
        self.processes = {}
        self.temp_dirs = {}
        self.tools = {}
        self.prompts = {}
        self.resources = {}
        self._initialized = False
        self.connection_status = {}

        # Register cleanup function
        atexit.register(self._cleanup)

    def _cleanup(self):
        """Clean up all running processes and temporary directories"""
        for name, process in self.processes.items():
            try:
                if process.poll() is None:  # Process is still running
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    logger.info("Terminated MCP server process: %s", name)
            except Exception as e:
                logger.error("Error terminating process %s: %s", name, e)

        # Clean up temporary directories
        for name, temp_dir in self.temp_dirs.items():
            try:
                shutil.rmtree(temp_dir)
                logger.info("Removed temporary directory for %s", name)
            except Exception as e:
                logger.error("Error removing temporary directory for %s: %s", name, e)

    async def start_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Start an MCP server process"""
        try:
            # Create a temporary directory for the server's files
            temp_dir = tempfile.mkdtemp(prefix=f"mcp_{server_name}_")
            self.temp_dirs[server_name] = temp_dir

            # Build command
            cmd = [config.command] + config.args

            # Set up environment
            env = os.environ.copy()
            if config.env:
                env.update(config.env)

            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
                start_new_session=True,  # Create a new process group
            )

            self.processes[server_name] = process
            self.connection_status[server_name] = True

            logger.info("Started MCP server %s with PID %s", server_name, process.pid)

            # Wait a bit for the server to initialize
            await asyncio.sleep(2)

            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(
                    "MCP server %s failed to start. Exit code: %s",
                    server_name,
                    process.returncode,
                )
                logger.error("Stdout: %s", stdout)
                logger.error("Stderr: %s", stderr)
                self.connection_status[server_name] = False
                return False

            return True

        except Exception as e:
            logger.error("Failed to start MCP server %s: %s", server_name, e)
            self.connection_status[server_name] = False
            return False

    async def stop_server(self, server_name: str) -> bool:
        """Stop an MCP server process"""
        if server_name not in self.processes:
            return True

        process = self.processes[server_name]

        try:
            if process.poll() is None:  # Process is still running
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                logger.info("Stopped MCP server %s", server_name)

            # Clean up temporary directory
            if server_name in self.temp_dirs:
                shutil.rmtree(self.temp_dirs[server_name])
                del self.temp_dirs[server_name]

            del self.processes[server_name]
            self.connection_status[server_name] = False
            return True

        except Exception as e:
            logger.error("Failed to stop MCP server %s: %s", server_name, e)
            return False

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool on an MCP server using direct process communication"""
        if server_name not in self.processes:
            raise ValueError(f"MCP server {server_name} not running")

        process = self.processes[server_name]

        if process.poll() is not None:
            raise ValueError(f"MCP server {server_name} is not running")

        # Create tool call message
        message = {
            "jsonrpc": "2.0",
            "method": "call_tool",
            "params": {"name": tool_name, "arguments": arguments},
            "id": str(uuid.uuid4()),
        }

        try:
            # Send the message to the server
            message_str = json.dumps(message) + "\n"
            process.stdin.write(message_str)
            process.stdin.flush()

            # Read the response
            response_str = process.stdout.readline()
            response = json.loads(response_str)

            if "error" in response:
                raise ValueError(f"Tool call error: {response['error']}")

            return response.get("result")

        except Exception as e:
            logger.error(
                "Error calling tool %s on server %s: %s", tool_name, server_name, e
            )
            raise


class MCPClientManager:
    """Manages multiple MCP client connections"""

    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.sessions: Dict[str, Any] = {}  # Store active sessions
        self.tools: Dict[str, MCPTool] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.resources: Dict[str, Dict] = {}
        self._initialized = False
        self._active_connections: Dict[str, Any] = {}  # Store read/write streams
        self.last_error: Optional[str] = None
        self.connection_status: Dict[str, bool] = (
            {}
        )  # Track connection status by server

        # References to the robust implementation
        self._aura_mcp_client: Any = None  # Will be set during initialization
        self._aura_mcp_integration: Any = None  # Will be set during initialization

        # Aura internal tools
        self._aura_internal_tools: List[Dict[str, Any]] = []

        # Create direct MCP manager for fallback
        self.direct_manager = DirectMCPManager() if not MCP_AVAILABLE else None

    async def initialize(self) -> bool:
        """Initialize MCP clients from configuration"""
        if not MCP_AVAILABLE:
            logger.warning(
                "⚠️ MCP client library not available, skipping initialization"
            )
            self._initialized = True  # Mark as initialized to avoid repeated attempts
            return True  # Return success to allow application to continue

        try:
            # Load MCP server configurations
            config_path = Path(__file__).parent / "mcp_client_config.json"
            if not config_path.exists():
                logger.warning("⚠️ MCP config file not found, using defaults")
                return False

            with open(config_path, "r") as f:
                config = json.load(f)

            # Get MCP server configurations directly from the config file
            mcp_servers = config.get("mcpServers", {})

            if not mcp_servers:
                logger.warning("⚠️ No MCP servers found in configuration")
                return False

            # Load server configurations from the mcp_servers dictionary
            for server_name, server_config in mcp_servers.items():
                self.servers[server_name] = MCPServerConfig(
                    name=server_name,
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                    description=server_config.get("description", ""),
                )

            # Track number of connection attempts
            connection_attempts = 0
            connection_successes = 0

            # Try to connect to each server with timeout protection
            for server_name, server_config in self.servers.items():
                connection_attempts += 1
                logger.info("🔄 Attempting to connect to MCP server: %s", server_name)

                try:
                    # Set a timeout for each connection attempt to prevent hanging
                    try:
                        # Use asyncio.wait_for to add timeout
                        await asyncio.wait_for(
                            self._connect_to_server(server_name, server_config),
                            timeout=10.0,  # 10 second timeout per server
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "⏱️ Connection attempt to %s timed out after 10 seconds, skipping",
                            server_name,
                        )
                        self.connection_status[server_name] = False
                        continue

                    # Check if connection was successful
                    if server_name in self.sessions and self.connection_status.get(
                        server_name, False
                    ):
                        connection_successes += 1
                        logger.info("✅ Successfully connected to %s", server_name)
                    else:
                        logger.warning(
                            "⚠️ Failed to establish session with %s", server_name
                        )
                except Exception as e:
                    logger.error(
                        "❌ Failed to connect to MCP server %s: %s", server_name, e
                    )
                    self.connection_status[server_name] = False

            self._initialized = True

            # Log initialization status
            if connection_successes == 0 and connection_attempts > 0:
                logger.warning(
                    f"⚠️ MCP Client Manager initialized but no servers connected ({connection_attempts} attempted)"
                )
                return True  # Still return success to allow the application to continue
            else:
                logger.info(
                    "✅ MCP Client Manager initialized with %s/%s servers connected",
                    connection_successes,
                    connection_attempts,
                )
                return True

        except Exception as e:
            logger.error("❌ Failed to initialize MCP Client Manager: %s", e)
            return False

    async def _connect_to_server(self, server_name: str, config: MCPServerConfig):
        """Connect to a single MCP server"""
        if not MCP_AVAILABLE:
            logger.warning(
                "⚠️ MCP client library not available, skipping connection to %s",
                server_name,
            )
            self.connection_status[server_name] = False
            return

        try:
            # Create server parameters with proper environment setup
            from mcp.client.stdio import (
                StdioServerParameters as MCPStdioServerParameters,
            )

            # Ensure proper environment variables
            env_dict = os.environ.copy()
            if config.env:
                env_dict.update(config.env)

            # Log server command for debugging
            cmd_str = f"{config.command} {' '.join(config.args)}"
            logger.info(
                "🔄 Connecting to MCP server: %s with command: %s", server_name, cmd_str
            )

            server_params = MCPStdioServerParameters(
                command=config.command, args=config.args, env=env_dict
            )

            # Create connection using async context manager
            try:
                if stdio_client is None:
                    logger.error(
                        "❌ stdio_client is not available for server %s. Skipping connection.",
                        server_name,
                    )
                    self.connection_status[server_name] = False
                    return

                # Start process directly to ensure it works
                logger.info("🚀 Starting MCP server process: %s", server_name)

                # Import subprocess related module
                import subprocess

                # First, test if the process starts correctly
                try:
                    # Create a test process to verify it can start
                    process = subprocess.Popen(
                        [config.command] + config.args,
                        env=env_dict,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    # Check if process started successfully
                    if process.poll() is not None:
                        # Process failed to start
                        stdout, stderr = process.communicate(timeout=1)
                        logger.error(
                            "❌ Failed to start MCP server %s: %s", server_name, stderr
                        )
                        self.connection_status[server_name] = False
                        return

                    # Process started, kill it now since stdio_client will start its own
                    process.terminate()
                    process.wait(timeout=1)
                    logger.info("✅ Verified %s process can start", server_name)
                except Exception as e:
                    logger.error(
                        "❌ Failed to create process for %s: %s", server_name, e
                    )
                    self.connection_status[server_name] = False
                    return

                # Now try the actual stdio_client connection
                logger.info("🔄 Establishing stdio connection to %s...", server_name)
                async with stdio_client(server_params) as (read_stream, write_stream):
                    # Store the streams for later cleanup
                    self._active_connections[server_name] = (read_stream, write_stream)

                    # Create session
                    logger.info("📡 Creating session for %s...", server_name)
                    session = ClientSession(read_stream, write_stream)
                    await session.initialize()

                    # Store session
                    self.sessions[server_name] = session
                    self.connection_status[server_name] = True

                    # Discover available tools
                    try:
                        tools_response = await session.list_tools()
                        tools = (
                            tools_response.tools
                            if tools_response and hasattr(tools_response, "tools")
                            else []
                        )

                        for tool in tools:
                            qualified_name = f"{server_name}.{tool.name}"
                            self.tools[qualified_name] = MCPTool(
                                name=qualified_name,  # Use fully qualified name as the tool name
                                description=tool.description or "",
                                server=server_name,
                                parameters=(
                                    tool.inputSchema
                                    if hasattr(tool, "inputSchema")
                                    else None
                                ),
                            )

                        logger.info(
                            "📦 Discovered %s tools from %s", len(tools), server_name
                        )
                    except Exception as e:
                        logger.warning(
                            "⚠️ Could not list tools from %s: %s", server_name, e
                        )

                    # Discover available prompts
                    try:
                        prompts_response = await session.list_prompts()
                        prompts = (
                            prompts_response.prompts
                            if prompts_response and hasattr(prompts_response, "prompts")
                            else []
                        )

                        for prompt in prompts:
                            qualified_name = f"{server_name}.{prompt.name}"
                            self.prompts[qualified_name] = MCPPrompt(
                                name=qualified_name,  # Use fully qualified name
                                description=prompt.description or "",
                                server=server_name,
                                arguments=(
                                    [vars(arg) for arg in prompt.arguments]
                                    if hasattr(prompt, "arguments")
                                    and prompt.arguments is not None
                                    else None
                                ),
                            )

                        logger.info(
                            "📝 Discovered %s prompts from %s",
                            len(prompts),
                            server_name,
                        )
                    except Exception as e:
                        logger.warning(
                            "⚠️ Could not list prompts from %s: %s", server_name, e
                        )

                    # Discover available resources
                    try:
                        resources_response = await session.list_resources()
                        resources = (
                            resources_response.resources
                            if resources_response
                            and hasattr(resources_response, "resources")
                            else []
                        )

                        self.resources[server_name] = {
                            resource.uri: resource for resource in resources
                        }

                        logger.info(
                            "📚 Discovered %s resources from %s",
                            len(resources),
                            server_name,
                        )
                    except Exception as e:
                        logger.warning(
                            "⚠️ Could not list resources from %s: %s", server_name, e
                        )

                    logger.info("✅ Successfully connected to %s", server_name)

            except Exception as e:
                logger.error(
                    "❌ Failed to establish connection to %s: %s", server_name, e
                )
                self.connection_status[server_name] = False
                # Don't re-raise, just log the error to allow other servers to connect

        except Exception as e:
            logger.error("❌ Failed to connect to server %s: %s", server_name, e)
            self.connection_status[server_name] = False
            # Clean up if connection failed
            if server_name in self._active_connections:
                del self._active_connections[server_name]

    async def shutdown(self):
        """Shutdown all MCP client connections"""
        for server_name, session in self.sessions.items():
            try:
                # Exit the session if it has __aexit__
                if hasattr(session, "__aexit__"):
                    await session.__aexit__(None, None, None)
                logger.info("🛑 Closed session for %s", server_name)
            except Exception as e:
                logger.error("❌ Error closing session for %s: %s", server_name, e)

        # Clean up connections
        # No need to call __aexit__ on stdio_client, as the context manager already handles cleanup
        self.tools.clear()
        self.prompts.clear()
        self.resources.clear()
        self._initialized = False

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the appropriate MCP server"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        tool = self.tools[tool_name]
        session = self.sessions.get(tool.server)

        if not session:
            raise ValueError(f"No session for server {tool.server}")

        try:
            result = await session.call_tool(tool.name, arguments)
            return result
        except Exception as e:
            logger.error("❌ Failed to execute tool %s: %s", tool_name, e)
            raise

    async def get_prompt(
        self, prompt_name: str, arguments: Optional[Dict[str, str]] = None
    ) -> Any:
        """Get a prompt from the appropriate MCP server"""
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt {prompt_name} not found")

        prompt = self.prompts[prompt_name]
        session = self.sessions.get(prompt.server)

        if not session:
            raise ValueError(f"No session for server {prompt.server}")

        try:
            result = await session.get_prompt(prompt.name, arguments)
            return result
        except Exception as e:
            logger.error("❌ Failed to get prompt %s: %s", prompt_name, e)
            raise

    async def read_resource(
        self, server_name: str, resource_uri: str
    ) -> Tuple[bytes, str]:
        """Read a resource from an MCP server"""
        session = self.sessions.get(server_name)

        if not session:
            raise ValueError(f"No session for server {server_name}")

        try:
            result = await session.read_resource(resource_uri)
            # Handle different response formats
            if hasattr(result, "contents"):
                content = result.contents[0] if result.contents else None
                if content and hasattr(content, "text"):
                    return content.text.encode(), content.mimeType or "text/plain"
                elif content and hasattr(content, "blob"):
                    return content.blob, content.mimeType or "application/octet-stream"
            return b"", "text/plain"
        except Exception as e:
            logger.error("❌ Failed to read resource %s: %s", resource_uri, e)
            raise

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools across all servers"""
        tools_list = []

        # Add Aura internal tools first (if available)
        if hasattr(self, "_aura_internal_tools"):
            tools_list.extend(self._aura_internal_tools)

        # Add external MCP tools
        for tool_name, tool in self.tools.items():
            tools_list.append(
                {
                    "name": tool_name,
                    "description": tool.description,
                    "server": tool.server,
                    "parameters": tool.parameters,
                }
            )

        return tools_list

    async def _update_tools_async(self):
        """Update tools from AuraMCPClient asynchronously"""
        if self._aura_mcp_client is None:
            return []

        try:
            # Get all tools from the robust client and ensure it's a dictionary
            tools = self._aura_mcp_client.list_all_tools() or {}

            if not isinstance(tools, dict):
                tools = {}
                logger.warning(
                    "⚠️ Tools returned from AuraMCPClient is not a dictionary, defaulting to empty dict"
                )

            # Clear existing tools
            self.tools.clear()

            # Update with new tools
            if tools:
                for qualified_name, tool_info in tools.items():
                    server_name = tool_info["server"]
                    self.tools[qualified_name] = MCPTool(
                        name=qualified_name,
                        description=tool_info["description"],
                        server=server_name,
                        parameters=tool_info.get("input_schema"),
                    )
                logger.info(
                    "✅ Updated tool registry with %s tools from AuraMCPClient",
                    len(self.tools),
                )
            else:
                logger.warning(
                    "⚠️ No tools returned from AuraMCPClient or tools is not a dictionary."
                )

        except Exception as e:
            logger.error("❌ Failed to update tools from AuraMCPClient: %s", e)
            return []

    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """Get list of all available prompts across all servers"""
        prompts_list = []
        for prompt_name, prompt in self.prompts.items():
            prompts_list.append(
                {
                    "name": prompt_name,
                    "description": prompt.description,
                    "server": prompt.server,
                    "arguments": prompt.arguments,
                }
            )
        return prompts_list

    def register_aura_internal_tools(self, tools: List[Dict[str, Any]]):
        """Register Aura's internal tools"""
        self._aura_internal_tools = tools
        # Also add them to the main tools dictionary
        for tool in tools:
            self.tools[tool["name"]] = MCPTool(
                name=tool["name"],
                description=tool["description"],
                server="aura-internal",
                parameters=tool.get("parameters"),
            )
        logger.info("✅ Registered %s Aura internal tools", len(tools))


# ============================================================================
# Global MCP Client Instance
# ============================================================================

mcp_client_manager = MCPClientManager()

# ============================================================================
# Integration Functions
# ============================================================================


async def initialize_mcp_client(aura_internal_tools=None) -> bool:
    """Initialize the MCP client connections"""
    global mcp_client_manager  # <-- Move this to the top!
    try:
        # Register Aura's internal tools first
        if aura_internal_tools:
            tool_list = aura_internal_tools.get_tool_list()
            mcp_client_manager.register_aura_internal_tools(tool_list)
            logger.info("✅ Registered %s Aura internal tools", len(tool_list))

        if not MCP_AVAILABLE:
            logger.warning(
                "⚠️ MCP client library not available - using only Aura internal tools"
            )
            return True

        # Use the robust AuraMCPClient implementation instead
        from aura_backend.mcp_client import AuraMCPClient, AuraMCPIntegration

        # Create a client instance with the correct config path
        try:
            client_config_path = str(Path(__file__).parent / "mcp_client_config.json")
        except NameError:
            client_config_path = str(Path.cwd() / "mcp_client_config.json")
        aura_mcp_client = AuraMCPClient(config_path=client_config_path)

        await aura_mcp_client.start()
        integration = AuraMCPIntegration(aura_mcp_client)

        # Store references to both the client and integration for later use
        capabilities = await integration.get_available_capabilities()
        connected_servers = capabilities.get("connected_servers", 0)
        success = connected_servers > 0

        capabilities = await integration.get_available_capabilities()
        success = capabilities["connected_servers"] > 0
        logger.info(
            f"✅ Connected to {capabilities['connected_servers']} MCP servers with {capabilities['available_tools']} available tools"
        )
        # Store references to MCP client
        mcp_client_manager._aura_mcp_client = aura_mcp_client
        mcp_client_manager._aura_mcp_integration = integration

        # List available tools
        available_tools = mcp_client_manager.get_available_tools()
        logger.info("📦 Total available tools at startup: %s", len(available_tools))

        # Group tools by server
        tools_by_server = {}
        for tool in available_tools:
            server = tool.get("server", "unknown")
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        # Log tools by server
        for server, tools in tools_by_server.items():
            logger.info("  %s: %s tools", server, len(tools))
            for tool in tools[:3]:  # Show first 3 tools per server
                logger.info("    - %s: %s...", tool["name"], tool["description"][:60])
            if len(tools) > 3:
                logger.info("    ... and %s more tools", len(tools) - 3)

        # Check for Aura internal tools
        aura_tools = [t for t in available_tools if t.get("server") == "aura-internal"]
        if not aura_tools:
            logger.warning(
                "⚠️ No Aura internal tools found. Check aura_internal_tools initialization."
            )

        return success
    except Exception as e:
        logger.error("❌ Failed to initialize MCP client: %s", e)
        return False


async def shutdown_mcp_client():
    """Shutdown MCP client connections"""
    try:
        await mcp_client_manager.shutdown()
        logger.info("✅ MCP client shutdown complete")
    except Exception:
        logger.error("❌ Error during MCP client shutdown")


def get_mcp_integration() -> MCPClientManager:
    """Get the MCP client manager instance"""
    return mcp_client_manager


async def enhance_response_with_mcp(
    user_message: str, context: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Get MCP status and available tools without hardcoded suggestions"""
    enhancements = {
        "available_tools": [],
        "available_prompts": [],
        "mcp_status": mcp_client_manager._initialized,
    }

    if not mcp_client_manager._initialized:
        return enhancements

    # Get available tools and prompts
    enhancements["available_tools"] = mcp_client_manager.get_available_tools()
    enhancements["available_prompts"] = mcp_client_manager.get_available_prompts()

    # Add server connection status
    enhancements["server_status"] = {
        server_name: server_name in mcp_client_manager.sessions
        for server_name in mcp_client_manager.servers.keys()
    }

    return enhancements


async def execute_mcp_tool(
    tool_name: str, arguments: Dict[str, Any], user_id: str, aura_internal_tools=None
) -> Dict[str, Any]:
    """Execute an MCP tool and return results"""
    try:
        # Check if it's an Aura internal tool
        if aura_internal_tools and (
            tool_name.startswith("aura.")
            or tool_name
            in [
                "search_aura_memories",
                "analyze_aura_emotional_patterns",
                "get_aura_user_profile",
            ]
        ):
            # Handle legacy tool names
            if not tool_name.startswith("aura."):
                tool_name = f"aura.{tool_name.replace('_aura_', '_')}"

            result = await aura_internal_tools.execute_tool(tool_name, arguments)
            return {
                "status": "success",
                "tool": tool_name,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }

        # Use the robust AuraMCPClient implementation if available
        if mcp_client_manager._aura_mcp_client is not None:
            result = await mcp_client_manager._aura_mcp_client.call_tool(
                tool_name, arguments
            )
        else:
            # Fallback to old implementation
            result = await mcp_client_manager.execute_tool(tool_name, arguments)

        return {
            "status": "success",
            "tool": tool_name,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("❌ Failed to execute MCP tool %s: %s", tool_name, e)
        return {
            "status": "error",
            "tool": tool_name,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def create_mcp_enhanced_prompt(
    base_prompt: str, available_tools: List[Dict[str, Any]], context: Dict[str, Any]
) -> str:
    """Create an enhanced prompt that includes MCP tool information"""
    # This function is deprecated - MCP tools are now handled via Gemini's native function calling
    # Return base prompt without modification to avoid hardcoded patterns
    return base_prompt


def _format_tool_parameters(tool: Dict[str, Any]) -> str:
    """Helper function to format tool parameters"""
    param_info = ""
    if tool.get("parameters"):
        param_info = "\n   Parameters: "
        if isinstance(tool["parameters"], dict) and "properties" in tool["parameters"]:
            properties = tool["parameters"].get("properties", {})
            required = tool["parameters"].get("required", [])
            param_list = []
            for param_name, param_details in properties.items():
                is_required = param_name in required
                param_type = param_details.get("type", "any")
                param_list.append(
                    f"{param_name} ({param_type}{', required' if is_required else ''})"
                )
            param_info += ", ".join(param_list[:3])  # Show first 3 params
            if len(param_list) > 3:
                param_info += f", ... ({len(param_list) - 3} more)"
    return param_info


# ============================================================================
# API Router
# ============================================================================

mcp_router = APIRouter(prefix="/mcp", tags=["MCP Integration"])


class MCPToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str


class MCPPromptRequest(BaseModel):
    prompt_name: str
    arguments: Optional[Dict[str, str]] = None
    user_id: str


@mcp_router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools"""
    return {
        "tools": mcp_client_manager.get_available_tools(),
        "count": len(mcp_client_manager.tools),
    }


@mcp_router.get("/prompts")
async def list_mcp_prompts():
    """List all available MCP prompts"""
    return {
        "prompts": mcp_client_manager.get_available_prompts(),
        "count": len(mcp_client_manager.prompts),
    }


@mcp_router.post("/tools/execute")
async def execute_tool_endpoint(request: MCPToolRequest):
    """Execute an MCP tool"""
    try:
        result = await execute_mcp_tool(
            tool_name=request.tool_name,
            arguments=request.arguments,
            user_id=request.user_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@mcp_router.post("/prompts/get")
async def get_prompt_endpoint(request: MCPPromptRequest):
    """Get an MCP prompt"""
    try:
        result = await mcp_client_manager.get_prompt(
            prompt_name=request.prompt_name, arguments=request.arguments
        )
        return {
            "status": "success",
            "prompt": request.prompt_name,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@mcp_router.get("/status")
async def mcp_status():
    """Get MCP integration status"""
    return {
        "initialized": mcp_client_manager._initialized,
        "mcp_available": MCP_AVAILABLE,
        "connected_servers": list(mcp_client_manager.sessions.keys()),
        "available_tools": len(mcp_client_manager.tools),
        "available_prompts": len(mcp_client_manager.prompts),
        "timestamp": datetime.now().isoformat(),
    }
