"""
Aura Internal Server - Direct Integration Version
==================================================

Standalone Internal Server that exposes Aura's capabilities to external agents
using direct subprocess execution rather than module imports.

This version uses subprocess for direct execution and works without requiring
the MCP module to be installed in the same environment.
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(
            sys.stderr
        )  # Log to stderr to keep stdout clean for protocol
    ],
)
logger = logging.getLogger("aura_internal_server")

# Constants
TOOL_DEFINITIONS = [
    {
        "name": "search_aura_memories",
        "description": "Search through Aura's conversation memories using semantic search",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User identifier for memory search",
                },
                "query": {
                    "type": "string",
                    "description": "Search query for semantic memory retrieval",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
            },
            "required": ["user_id", "query"],
        },
    },
    {
        "name": "analyze_aura_emotional_patterns",
        "description": "Analyze emotional patterns and trends for a specific user over time",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User identifier for emotional analysis",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 7)",
                    "minimum": 1,
                    "maximum": 365,
                    "default": 7,
                },
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "store_aura_conversation",
        "description": "Store a conversation memory in Aura's vector database",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "message": {
                    "type": "string",
                    "description": "Message content to store",
                },
                "sender": {
                    "type": "string",
                    "description": "Message sender ('user' or 'aura' or agent name)",
                    "enum": ["user", "aura", "agent", "system"],
                },
                "emotional_state": {
                    "type": "string",
                    "description": "Optional emotional state in format 'Emotion:Intensity' (e.g., 'Happy:Medium')",
                },
                "cognitive_focus": {
                    "type": "string",
                    "description": "Optional ASEKE cognitive focus component",
                    "enum": ["KS", "CE", "IS", "KI", "KP", "ESA", "SDA", "Learning"],
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional session identifier",
                },
            },
            "required": ["user_id", "message", "sender"],
        },
    },
    {
        "name": "get_aura_user_profile",
        "description": "Retrieve user profile information from Aura's file system",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"}
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "export_aura_user_data",
        "description": "Export comprehensive user data including conversations and patterns",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "format": {
                    "type": "string",
                    "description": "Export format",
                    "enum": ["json", "csv", "xml"],
                    "default": "json",
                },
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "query_aura_emotional_states",
        "description": "Get information about Aura's emotional state model and available emotions",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "query_aura_aseke_framework",
        "description": "Get detailed information about Aura's ASEKE cognitive architecture framework",
        "parameters": {"type": "object", "properties": {}},
    },
]


class SimpleMCPServer:
    """
    A simplified Internal Server implementation using direct JSON-RPC over stdout/stdin.

    Provides a lightweight MCP server interface for Aura's capabilities without
    requiring external dependencies. Communicates via JSON-RPC protocol over
    standard input/output streams.
    """

    def __init__(self) -> None:
        """
        Initialize the Simple MCP Server.

        Sets up tool definitions and prepares the server for handling requests.
        """
        self.tools = {tool["name"]: tool for tool in TOOL_DEFINITIONS}

    async def handle_initialize(self, _params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle initialize request from MCP client.

        Args:
            _params: Initialization parameters from the client

        Returns:
            Server information including name and version
        """
        return {"server": {"name": "Aura Advanced AI Companion", "version": "1.0.0"}}

    async def handle_list_tools(self, _params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle list_tools request to enumerate available tools.

        Args:
            _params: Request parameters (typically empty for list_tools)

        Returns:
            Dictionary containing list of available tool definitions
        """
        return {"tools": list(self.tools.values())}

    async def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle call_tool request to execute a specific tool.

        Args:
            params: Tool execution parameters including tool name and arguments

        Returns:
            Tool execution results or error information
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {"error": f"Tool not found: {tool_name}"}

        # In a real implementation, call the actual tool function
        # For this demonstration, we'll return mock data
        if isinstance(tool_name, str):
            result = await self._mock_tool_execution(tool_name, arguments)
            return result
        else:
            return {"error": "Tool name is not a string"}

    async def _mock_tool_execution(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Mock tool execution for demonstration purposes.

        In a real implementation, this would call actual Aura functions
        and return real data from the memory and emotional systems.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments provided for tool execution

        Returns:
            Mock results simulating actual tool execution
        """
        if tool_name == "search_aura_memories":
            return {
                "status": "success",
                "memories": [
                    {
                        "content": "This is a mock memory result",
                        "metadata": {"timestamp": "2023-01-01T12:00:00Z"},
                    }
                ],
            }
        elif tool_name == "analyze_aura_emotional_patterns":
            return {
                "status": "success",
                "dominant_emotions": ["Happy", "Curious"],
                "emotional_stability": 0.8,
            }
        elif tool_name == "store_aura_conversation":
            return {"status": "success", "message": "Conversation stored successfully"}
        elif tool_name == "get_aura_user_profile":
            return {
                "status": "success",
                "profile": {
                    "name": arguments.get("user_id", "Unknown"),
                    "preferences": {"theme": "dark"},
                },
            }
        elif tool_name == "export_aura_user_data":
            return {
                "status": "success",
                "export_path": f"/tmp/aura_export_{arguments.get('user_id', 'unknown')}.{arguments.get('format', 'json')}",
            }
        elif tool_name == "query_aura_emotional_states":
            return {
                "status": "success",
                "emotional_states": [
                    "Happy",
                    "Sad",
                    "Angry",
                    "Excited",
                    "Peace",
                    "Curiosity",
                ],
            }
        elif tool_name == "query_aura_aseke_framework":
            return {
                "status": "success",
                "components": ["KS", "CE", "IS", "KI", "KP", "ESA", "SDA"],
            }
        else:
            return {
                "status": "error",
                "error": f"Tool implementation not found: {tool_name}",
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming JSON-RPC request.

        Routes the request to the appropriate handler based on the method
        and returns a properly formatted JSON-RPC response.

        Args:
            request: JSON-RPC request dictionary with method, params, and id

        Returns:
            JSON-RPC response dictionary with result or error
        """
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        # Prepare response structure
        response = {"jsonrpc": "2.0", "id": request_id}

        try:
            # Route the request to the appropriate handler
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "list_tools":
                result = await self.handle_list_tools(params)
            elif method == "call_tool":
                result = await self.handle_call_tool(params)
            else:
                # Method not supported
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                }
                return response

            # Add result to response
            response["result"] = result

        except Exception as e:
            # Handle any errors
            logger.error("Error processing request: %s", e)
            response["error"] = {"code": -32603, "message": f"Internal error: {str(e)}"}

        return response

    async def process_input(self) -> None:
        """
        Process input from stdin and write responses to stdout.

        Continuously reads JSON-RPC requests from standard input,
        processes them, and writes responses to standard output.
        Uses asyncio for non-blocking I/O operations.
        """
        # Set up non-blocking stdin
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        # Process requests
        while True:
            # Read a line from stdin
            line = await reader.readline()
            if not line:
                break

            line = line.decode().strip()
            if not line:
                continue

            try:
                # Parse JSON request
                request = json.loads(line)

                # Handle the request
                response = await self.handle_request(request)

                # Write response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError:
                logger.error("Invalid JSON: %s", line)
                # Send error response
                response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None,
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


async def main() -> None:
    """
    Main function to start the Aura Internal Server.

    Parses command line arguments, configures logging,
    and starts the server to process MCP requests.
    """
    parser = argparse.ArgumentParser(description="Aura Internal Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("🚀 Starting Aura Internal Server...")

    server = SimpleMCPServer()
    await server.process_input()


if __name__ == "__main__":
    asyncio.run(main())
