"""Characterize production MCP parameter formatting without contacting MCP."""

from collections.abc import Callable
from typing import Any

import pytest

from aura_backend.smart_mcp_parameter_handler import SmartMCPParameterHandler


@pytest.fixture
def handler_factory() -> Callable[[], SmartMCPParameterHandler]:
    """Return a fresh handler so learned formats cannot leak between tests."""
    return SmartMCPParameterHandler


@pytest.fixture
def direct_schema() -> dict[str, Any]:
    """Describe a tool that accepts ordinary top-level arguments."""
    return {
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "encoding": {"type": "string"},
            },
            "required": ["path"],
        }
    }


@pytest.fixture
def fastmcp_schema() -> dict[str, Any]:
    """Describe the current FastMCP Pydantic-model wrapper shape."""
    return {
        "inputSchema": {
            "type": "object",
            "properties": {
                "params": {"$ref": "#/$defs/AuraMemorySearch"},
            },
            "required": ["params"],
            "$defs": {
                "AuraMemorySearch": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["user_id", "query"],
                }
            },
        }
    }


def test_direct_schema_preserves_arguments(
    handler_factory: Callable[[], SmartMCPParameterHandler],
    direct_schema: dict[str, Any],
) -> None:
    arguments = {"path": "/synthetic/example.txt", "encoding": "utf-8"}

    result = handler_factory().format_parameters(
        tool_name="read_file",
        server_name="filesystem",
        arguments=arguments,
        tool_schema=direct_schema,
    )

    assert result == arguments


def test_node_server_heuristic_wraps_arguments(
    handler_factory: Callable[[], SmartMCPParameterHandler],
) -> None:
    arguments = {"path": "/synthetic/example.txt"}

    result = handler_factory().format_parameters(
        tool_name="custom_tool",
        server_name="npx-server",
        arguments=arguments,
    )

    assert result == {"params": arguments}


def test_fastmcp_schema_wraps_direct_arguments(
    handler_factory: Callable[[], SmartMCPParameterHandler],
    fastmcp_schema: dict[str, Any],
) -> None:
    arguments = {"user_id": "synthetic-user", "query": "synthetic-query"}

    result = handler_factory().format_parameters(
        tool_name="search_aura_memories",
        server_name="aura-companion",
        arguments=arguments,
        tool_schema=fastmcp_schema,
    )

    assert result == {"params": arguments}


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        pytest.param(
            {"params": '{"user_id": "synthetic-user", "query": "memory"}'},
            {"params": {"user_id": "synthetic-user", "query": "memory"}},
            id="json-string-is-decoded",
        ),
        pytest.param(
            {"params": {"user_id": "synthetic-user", "query": "memory"}},
            {"params": {"user_id": "synthetic-user", "query": "memory"}},
            id="already-wrapped-dict-is-preserved",
        ),
        pytest.param({}, {}, id="empty-arguments-remain-empty"),
        pytest.param(
            {"params": "{malformed-json"},
            {"params": "{malformed-json"},
            id="malformed-json-falls-back-to-original",
        ),
    ],
)
def test_fastmcp_special_cases_preserve_current_fallbacks(
    handler_factory: Callable[[], SmartMCPParameterHandler],
    fastmcp_schema: dict[str, Any],
    arguments: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    result = handler_factory().format_parameters(
        tool_name="search_aura_memories",
        server_name="aura-companion",
        arguments=arguments,
        tool_schema=fastmcp_schema,
    )

    assert result == expected


def test_cached_format_is_reused_without_a_schema(
    handler_factory: Callable[[], SmartMCPParameterHandler],
    fastmcp_schema: dict[str, Any],
) -> None:
    handler = handler_factory()
    handler.format_parameters(
        tool_name="custom_store",
        server_name="synthetic-server",
        arguments={"value": 1},
        tool_schema=fastmcp_schema,
    )

    result = handler.format_parameters(
        tool_name="custom_store",
        server_name="synthetic-server",
        arguments={"value": 2},
    )

    assert result == {"params": {"value": 2}}
