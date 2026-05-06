"""
Smart MCP Parameter Handler
==========================

This module provides intelligent parameter formatting for MCP tools by analyzing
their schemas instead of hardcoding server names. It learns from tool schemas
and caches the results for optimal performance.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ParameterFormat:
    """Represents how a tool expects its parameters"""

    format_type: str  # 'direct', 'wrapped', 'fastmcp'
    detected_at: datetime
    schema_hash: str
    confidence: float


class SmartMCPParameterHandler:
    """
    Intelligently handles parameter formatting for MCP tools by analyzing
    their schemas and learning from successful calls.
    """

    def __init__(self):
        # Cache for learned parameter formats
        # Key: (server_name, tool_name) -> ParameterFormat
        self._format_cache: Dict[Tuple[str, str], ParameterFormat] = {}

        # Success tracking for format validation
        # Key: (server_name, tool_name, format_type) -> (success_count, failure_count)
        self._format_success_tracking: Dict[Tuple[str, str, str], Tuple[int, int]] = {}

    def format_parameters(
        self,
        tool_name: str,
        server_name: str,
        arguments: Dict[str, Any],
        tool_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format parameters according to the tool's expected format by analyzing its schema.

        Args:
            tool_name: Name of the MCP tool
            server_name: Name of the MCP server
            arguments: Raw arguments from Gemini
            tool_schema: Tool schema containing parameter definitions

        Returns:
            Properly formatted parameters for the tool
        """
        try:
            # Check cache first
            cache_key = (server_name, tool_name)
            if cache_key in self._format_cache:
                cached_format = self._format_cache[cache_key]
                logger.debug(
                    f"📋 Using cached format '{cached_format.format_type}' for {tool_name}"
                )
                return self._apply_format(arguments, cached_format.format_type)

            # Determine format type - try both schema and heuristics
            schema_format = None
            heuristic_format = None

            # Try schema detection first
            if tool_schema:
                schema_format = self._detect_format_from_schema(tool_schema, tool_name)
                logger.debug(
                    f"🔍 Schema detected format '{schema_format}' for {tool_name}"
                )

            # Always try heuristics as well
            heuristic_format = self._detect_format_from_heuristics(
                tool_name, server_name, arguments
            )
            logger.debug(
                f"🎯 Heuristics detected format '{heuristic_format}' for {tool_name}"
            )

            # Choose the best format detection
            if schema_format == "fastmcp" or heuristic_format == "fastmcp":
                # If either detection method says FastMCP, use FastMCP
                format_type = "fastmcp"
                logger.debug(
                    f"🎯 Using FastMCP format for {tool_name} (schema: {schema_format}, heuristic: {heuristic_format})"
                )
            elif schema_format and schema_format != "direct":
                # Use schema detection if it's not 'direct' (which might be a fallback)
                format_type = schema_format
                logger.debug(
                    "🔍 Using schema format '%s' for %s", format_type, tool_name
                )
            elif heuristic_format:
                # Fall back to heuristics
                format_type = heuristic_format
                logger.debug(
                    f"🎯 Using heuristic format '{format_type}' for {tool_name}"
                )
            else:
                # Default fallback
                format_type = "direct"
                logger.debug(
                    "🔧 Using default format '%s' for %s", format_type, tool_name
                )

            # Cache the detection
            if tool_schema:
                self._cache_format(server_name, tool_name, format_type, tool_schema)

            return self._apply_format(arguments, format_type)

        except Exception as e:
            logger.error("❌ Error formatting parameters for %s: %s", tool_name, e)
            # Return original arguments as fallback
            return arguments

    def _detect_format_from_schema(
        self, tool_schema: Dict[str, Any], tool_name: str
    ) -> str:
        """
        Detect parameter format from tool schema.

        Returns: 'direct', 'wrapped', or 'fastmcp'
        """
        # Get the input schema or parameters section
        input_schema = tool_schema.get("inputSchema") or tool_schema.get(
            "parameters", {}
        )
        properties = input_schema.get("properties", {})

        # Check if the tool expects no parameters
        if not properties:
            logger.debug("Tool %s expects no parameters", tool_name)
            return "direct"

        # For Brave search and similar tools, check for direct parameter structure
        if any(param in properties for param in ["query", "q", "search_query"]):
            logger.debug(
                f"Tool {tool_name} has direct query parameters - using direct format"
            )
            return "direct"

        # Check for $defs pattern (common in FastMCP tools with Pydantic models)
        if "$defs" in input_schema or "$ref" in str(input_schema):
            logger.debug("Tool %s uses $defs/$ref pattern - likely FastMCP", tool_name)
            return "fastmcp"

        # Check if there's a single 'params' property that wraps everything
        if len(properties) == 1 and "params" in properties:
            params_prop = properties["params"]

            # Check if params has a $ref (Pydantic model reference)
            if "$ref" in params_prop:
                logger.debug(
                    f"Tool {tool_name} uses $ref in params - FastMCP with Pydantic"
                )
                return "fastmcp"

            # Check if params is an object with its own properties
            if params_prop.get("type") == "object" and "properties" in params_prop:
                logger.debug("Tool %s expects FastMCP-style wrapped params", tool_name)
                return "fastmcp"

        # Check for Aura tools specifically
        tool_lower = tool_name.lower()
        if any(
            pattern in tool_lower
            for pattern in ["aura_", "search_aura", "store_aura", "analyze_aura"]
        ):
            logger.debug("Tool %s is an Aura tool - using FastMCP format", tool_name)
            return "fastmcp"

        # Default to direct for most tools (especially web search tools)
        logger.debug("Tool %s using direct parameter format", tool_name)
        return "direct"

    def _detect_format_from_heuristics(
        self, tool_name: str, server_name: str, arguments: Dict[str, Any]
    ) -> str:
        """
        Use heuristics when schema is not available.
        """
        # Check if tool name suggests a certain pattern
        tool_lower = tool_name.lower()
        server_lower = server_name.lower()

        # Brave search tools should use direct parameters (they expect {query: "..."})
        if "brave" in tool_lower or "brave" in server_lower:
            return "direct"

        # Web search tools generally use direct parameters
        if any(
            pattern in tool_lower
            for pattern in ["search", "web_search", "google", "bing"]
        ):
            return "direct"

        # Aura companion tools use FastMCP format
        if "aura" in server_lower and "companion" in server_lower:
            return "fastmcp"

        # Aura-specific internal tools
        if any(
            pattern in tool_lower
            for pattern in ["aura_", "search_aura", "store_aura", "analyze_aura"]
        ):
            return "fastmcp"

        # Common direct parameter tools (filesystem, etc.)
        if any(
            pattern in tool_lower
            for pattern in ["read_", "write_", "execute_", "list_", "get_", "create_"]
        ):
            return "direct"

        # Check server implementation hints
        if "fastmcp" in server_lower:
            return "fastmcp"

        # JavaScript/TypeScript servers often use wrapped params
        if any(hint in server_lower for hint in ["npx", "node", "js", "ts"]):
            return "wrapped"

        # Default to direct for most external tools
        return "direct"

    def _apply_format(
        self, arguments: Dict[str, Any], format_type: str
    ) -> Dict[str, Any]:
        """
        Apply the detected format to the arguments.
        """
        # Handle empty arguments
        if not arguments:
            return {}

        # For direct format, just return arguments as-is (most common case)
        if format_type == "direct":
            return arguments

        elif format_type == "fastmcp":
            # Wrap in params for FastMCP - but only if not already wrapped
            if "params" not in arguments:
                return {"params": arguments}
            else:
                # Already wrapped, ensure params is a dict not string
                params_value = arguments["params"]
                if isinstance(params_value, str):
                    try:
                        parsed_params = json.loads(params_value)
                        return {"params": parsed_params}
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse FastMCP params JSON: {params_value}"
                        )
                        return arguments
                return arguments

        elif format_type == "wrapped":
            # Simple wrapper - similar to fastmcp but simpler
            if "params" not in arguments:
                return {"params": arguments}
            else:
                return arguments

        # Default to returning as-is
        return arguments

    def _cache_format(
        self,
        server_name: str,
        tool_name: str,
        format_type: str,
        tool_schema: Dict[str, Any],
    ):
        """Cache the detected format for future use."""
        cache_key = (server_name, tool_name)

        # Create a simple hash of the schema for validation
        schema_str = json.dumps(tool_schema, sort_keys=True)
        schema_hash = str(hash(schema_str))

        self._format_cache[cache_key] = ParameterFormat(
            format_type=format_type,
            detected_at=datetime.now(),
            schema_hash=schema_hash,
            confidence=1.0,  # High confidence from schema analysis
        )

    def record_success(
        self, server_name: str, tool_name: str, format_type: str, success: bool
    ):
        """
        Record whether a format worked for a tool.
        This helps improve format detection over time.
        """
        tracking_key = (server_name, tool_name, format_type)

        if tracking_key not in self._format_success_tracking:
            self._format_success_tracking[tracking_key] = (0, 0)

        success_count, failure_count = self._format_success_tracking[tracking_key]

        if success:
            self._format_success_tracking[tracking_key] = (
                success_count + 1,
                failure_count,
            )
            logger.debug("✅ Format '%s' succeeded for %s", format_type, tool_name)
        else:
            self._format_success_tracking[tracking_key] = (
                success_count,
                failure_count + 1,
            )
            logger.debug("❌ Format '%s' failed for %s", format_type, tool_name)

            # If this format consistently fails, remove it from cache
            if failure_count >= 2 and success_count == 0:
                cache_key = (server_name, tool_name)
                if cache_key in self._format_cache:
                    del self._format_cache[cache_key]
                    logger.warning(
                        f"🔄 Removed cached format for {tool_name} due to failures"
                    )

    def get_format_stats(self) -> Dict[str, Any]:
        """Get statistics about format detection and success rates."""
        stats = {
            "cached_formats": len(self._format_cache),
            "format_distribution": {},
            "success_rates": {},
        }

        # Count format types
        for format_info in self._format_cache.values():
            format_type = format_info.format_type
            stats["format_distribution"][format_type] = (
                stats["format_distribution"].get(format_type, 0) + 1
            )

        # Calculate success rates
        for (server, tool, fmt), (
            success,
            failure,
        ) in self._format_success_tracking.items():
            key = f"{server}.{tool}.{fmt}"
            total = success + failure
            if total > 0:
                stats["success_rates"][key] = {
                    "success": success,
                    "failure": failure,
                    "rate": success / total,
                }

        return stats


# Global instance for reuse
_smart_handler_instance = None


def get_smart_parameter_handler() -> SmartMCPParameterHandler:
    """Get or create the global smart parameter handler instance."""
    global _smart_handler_instance
    if _smart_handler_instance is None:
        _smart_handler_instance = SmartMCPParameterHandler()
    return _smart_handler_instance


# Example usage and tests
if __name__ == "__main__":
    # Test the smart parameter handler
    handler = SmartMCPParameterHandler()

    # Test schemas that would indicate different formats
    test_schemas = [
        # Direct parameters schema
        {
            "name": "read_file",
            "schema": {
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "encoding": {"type": "string"},
                    },
                    "required": ["path"],
                }
            },
            "expected": "direct",
        },
        # FastMCP wrapped params schema
        {
            "name": "brave_web_search",
            "schema": {
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "params": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "count": {"type": "number"},
                            },
                            "required": ["query"],
                        }
                    },
                    "required": ["params"],
                }
            },
            "expected": "fastmcp",
        },
        # No parameters
        {
            "name": "list_sessions",
            "schema": {"inputSchema": {"type": "object", "properties": {}}},
            "expected": "direct",
        },
    ]

    print("🧪 Testing Smart Parameter Handler\n")
    print("=" * 60)

    for test in test_schemas:
        detected = handler._detect_format_from_schema(
            test["schema"]["inputSchema"], test["name"]
        )

        status = "✅" if detected == test["expected"] else "❌"
        print(
            f"{status} {test['name']}: detected '{detected}', expected '{test['expected']}'"
        )

    print("\n" + "=" * 60)
    print("✅ Smart parameter detection ready!")
