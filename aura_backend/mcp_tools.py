#!/usr/bin/env python3
"""
MCP Tools Integration Helper for Aura
====================================

This module provides utility functions to help Aura use MCP tools more effectively,
parsing tool calls from messages and integrating tool results into responses.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPToolParser:
    """
    Parser for MCP tool references in user and AI messages.
    Handles both @mcp.tool and @tool formats.
    """

    def __init__(self, available_tools: Optional[List[Dict[str, Any]]] = None):
        self.available_tools = available_tools or []
        self.tool_pattern = re.compile(
            r'@(?:mcp\.)?tool\s*\(\s*["\']?([a-zA-Z0-9_.-]+)["\']?\s*(?:,\s*({.*?}))?\s*\)'
        )
        self.multi_line_tool_pattern = re.compile(
            r'@(?:mcp\.)?tool\s*\(\s*["\']?([a-zA-Z0-9_.-]+)["\']?\s*,\s*\n([\s\S]+?)\n\s*\)'
        )

    def extract_tool_calls(self, message: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from a message.
        Returns a list of dictionaries with tool name and arguments.
        """
        calls = []

        # Try single-line pattern first
        matches = self.tool_pattern.findall(message)
        for tool_name, args_str in matches:
            try:
                # Parse arguments if provided
                args = {}
                if args_str:
                    args = json.loads(args_str)
                calls.append(
                    {"tool_name": tool_name, "arguments": args, "source": "single_line"}
                )
            except json.JSONDecodeError:
                logger.warning(
                    f"⚠️ Failed to parse arguments for tool {tool_name}: {args_str}"
                )

        # Then try multi-line pattern
        multi_matches = self.multi_line_tool_pattern.findall(message)
        for tool_name, args_str in multi_matches:
            try:
                # Remove any leading/trailing spaces and try to parse JSON
                args_str = args_str.strip()
                if not args_str.startswith("{"):
                    args_str = "{" + args_str
                if not args_str.endswith("}"):
                    args_str = args_str + "}"
                args = json.loads(args_str)

                # Check if this call was already found in single-line pattern
                if not any(
                    c["tool_name"] == tool_name and c["source"] == "single_line"
                    for c in calls
                ):
                    calls.append(
                        {
                            "tool_name": tool_name,
                            "arguments": args,
                            "source": "multi_line",
                        }
                    )
            except json.JSONDecodeError:
                logger.warning(
                    f"⚠️ Failed to parse multi-line arguments for tool {tool_name}"
                )

        # Add information about whether the tool exists
        for call in calls:
            call["exists"] = self._tool_exists(call["tool_name"])

            # Try to find the full qualified name if using short name
            if not call["exists"] and "." not in call["tool_name"]:
                qualified_name = self._find_qualified_name(call["tool_name"])
                if qualified_name:
                    call["qualified_name"] = qualified_name
                    call["exists"] = True
                    # Keep the original tool_name for reference
                    call["original_name"] = call["tool_name"]
                    call["tool_name"] = qualified_name

        return calls

    def _tool_exists(self, tool_name: str) -> bool:
        """Check if the tool exists in available tools"""
        return any(t["name"] == tool_name for t in self.available_tools)

    def _find_qualified_name(self, short_name: str) -> Optional[str]:
        """Find the full qualified name for a short tool name"""
        for tool in self.available_tools:
            parts = tool["name"].split(".")
            if parts[-1] == short_name:
                return tool["name"]
        return None

    def replace_tool_calls_with_results(
        self, message: str, tool_results: Dict[str, Any]
    ) -> str:
        """
        Replace tool call notation in the message with the actual results.
        This makes the final message cleaner for the user.
        """
        # First do the single-line replacements
        for tool_name, result in tool_results.items():
            # Create a pattern that matches this specific tool call
            tool_pattern = re.compile(
                rf'@(?:mcp\.)?tool\s*\(\s*["\']?{re.escape(tool_name)}["\']?\s*(?:,\s*{{.*?}})?\s*\)'
            )

            # Format the result nicely for insertion
            if isinstance(result, dict):
                result_str = f"**Tool Result ({tool_name})**: \n```json\n{json.dumps(result, indent=2)}\n```"
            else:
                result_str = f"**Tool Result ({tool_name})**: {str(result)}"

            # Replace all occurrences of this tool call with the result
            message = tool_pattern.sub(result_str, message)

        # Then do the multi-line replacements
        for tool_name, result in tool_results.items():
            multi_pattern = re.compile(
                rf'@(?:mcp\.)?tool\s*\(\s*["\']?{re.escape(tool_name)}["\']?\s*,\s*\n[\s\S]+?\n\s*\)'
            )

            # Format the result nicely for insertion
            if isinstance(result, dict):
                result_str = f"**Tool Result ({tool_name})**: \n```json\n{json.dumps(result, indent=2)}\n```"
            else:
                result_str = f"**Tool Result ({tool_name})**: {str(result)}"

            # Replace all occurrences of this tool call with the result
            message = multi_pattern.sub(result_str, message)

        return message


async def process_mcp_tool_calls(
    message: str, user_id: str, execute_tool_fn, available_tools: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Process MCP tool calls in a message, execute the tools, and replace calls with results.

    Args:
        message: The message text potentially containing tool calls
        user_id: User ID for context
        execute_tool_fn: Async function to execute a tool (tool_name, arguments, user_id)
        available_tools: List of available tools

    Returns:
        Tuple of (updated_message, tool_results)
    """
    # Parse the message for tool calls
    parser = MCPToolParser(available_tools)
    tool_calls = parser.extract_tool_calls(message)

    if not tool_calls:
        return message, {}

    # Execute all tool calls
    tool_results = {}
    execution_tasks = []

    for call in tool_calls:
        if call["exists"]:
            tool_name = call["tool_name"]
            arguments = call["arguments"]

            # Add user_id if not present and tool accepts it
            if "user_id" not in arguments:
                # Check if the tool accepts user_id parameter
                tool_info = next(
                    (t for t in available_tools if t["name"] == tool_name), None
                )
                if tool_info and tool_info.get("parameters", {}).get(
                    "properties", {}
                ).get("user_id"):
                    arguments["user_id"] = user_id

            # Create task for execution
            task = asyncio.create_task(execute_tool_fn(tool_name, arguments, user_id))
            execution_tasks.append((tool_name, task))
            logger.info("🔄 Executing MCP tool: %s", tool_name)

    # Wait for all tool executions to complete
    for tool_name, task in execution_tasks:
        try:
            result = await task
            tool_results[tool_name] = result
            logger.info("✅ Completed MCP tool execution: %s", tool_name)
        except Exception as e:
            logger.error("❌ Error executing tool %s: %s", tool_name, e)
            tool_results[tool_name] = {"status": "error", "error": str(e)}

    # Replace tool calls with results
    updated_message = parser.replace_tool_calls_with_results(message, tool_results)

    return updated_message, tool_results


def create_tool_usage_guide(available_tools: List[Dict[str, Any]]) -> str:
    """
    Create a markdown guide showing how to use available MCP tools.
    This can be shown to the user when they need help with tools.
    """
    if not available_tools:
        return "No MCP tools are currently available."

    guide = "# Available MCP Tools\n\n"
    guide += 'You can use these tools by typing `@mcp.tool("tool_name", {parameters})` in your message.\n\n'

    # Group tools by server
    tools_by_server = {}
    for tool in available_tools:
        server = tool.get("server", "unknown")
        if server not in tools_by_server:
            tools_by_server[server] = []
        tools_by_server[server].append(tool)

    # Format each server's tools
    for server, tools in tools_by_server.items():
        guide += f"## {server} Tools\n\n"

        for tool in tools:
            guide += f"### {tool['name']}\n\n"
            guide += f"{tool['description']}\n\n"

            # Add parameter information if available
            if tool.get("parameters") and isinstance(tool["parameters"], dict):
                guide += "**Parameters:**\n\n"

                properties = tool["parameters"].get("properties", {})
                required = tool["parameters"].get("required", [])

                if properties:
                    for param_name, param_info in properties.items():
                        param_type = param_info.get("type", "any")
                        param_desc = param_info.get("description", "")
                        param_required = (
                            "Required" if param_name in required else "Optional"
                        )

                        guide += f"- `{param_name}` ({param_type}, {param_required}): {param_desc}\n"

                guide += "\n"

            # Add usage example
            guide += "**Example:**\n\n"
            example_params = {}

            if tool.get("parameters") and isinstance(tool["parameters"], dict):
                properties = tool["parameters"].get("properties", {})
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "any")

                    # Create sample value based on type
                    if param_name == "user_id":
                        example_params[param_name] = "YOUR_USER_ID"
                    elif param_type == "string":
                        example_params[param_name] = f"sample_{param_name}"
                    elif param_type == "integer" or param_type == "number":
                        example_params[param_name] = 123
                    elif param_type == "boolean":
                        example_params[param_name] = True
                    elif param_type == "array":
                        example_params[param_name] = ["item1", "item2"]
                    elif param_type == "object":
                        example_params[param_name] = {"key": "value"}

            guide += f"```\n@mcp.tool(\"{tool['name']}\", {json.dumps(example_params, indent=2)})\n```\n\n"

    return guide


# Function to test the MCP tool parser
async def test_parser():
    """Test the MCP tool parser functionality"""
    test_message = """
    Let me search for that using @mcp.tool("search_tool", {"query": "test query"})

    Or we could try this other tool:
    @mcp.tool("complex_tool",
    {
      "param1": "value1",
      "param2": 123
    }
    )

    And here's one without arguments: @tool("simple_tool")
    """

    parser = MCPToolParser(
        [
            {"name": "search_tool", "description": "A search tool"},
            {"name": "complex_tool", "description": "A complex tool"},
            {"name": "server.simple_tool", "description": "A simple tool"},
        ]
    )

    tool_calls = parser.extract_tool_calls(test_message)
    print("Found tool calls:", json.dumps(tool_calls, indent=2))

    # Test replacing tool calls with results
    tool_results = {
        "search_tool": {"results": ["result1", "result2"]},
        "complex_tool": "Simple text result",
        "simple_tool": {"status": "success"},
    }

    updated_message = parser.replace_tool_calls_with_results(test_message, tool_results)
    print("\nUpdated message:")
    print(updated_message)


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_parser())
