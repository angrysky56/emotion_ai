"""Characterize MCP bridge result formatting with synthetic in-memory values."""

import json
from typing import NoReturn

import numpy as np
import pytest

from aura_backend.mcp_to_gemini_bridge import (
    MCPGeminiBridge,
    ToolExecutionResult,
    ensure_json_serializable,
    format_function_call_result_for_model,
)


class NoCallMCPClient:
    """Fail loudly if a bridge characterization accidentally contacts MCP."""

    def list_all_tools(self) -> NoReturn:
        raise AssertionError("characterization tests must not list MCP tools")

    def call_tool(self, _tool_name: str, _arguments: object) -> NoReturn:
        raise AssertionError("characterization tests must not call MCP tools")


@pytest.fixture
def bridge() -> MCPGeminiBridge:
    """Build the production bridge around a client that cannot perform I/O."""
    return MCPGeminiBridge(NoCallMCPClient())


def test_numpy_result_becomes_json_safe_native_values() -> None:
    raw_result = {
        "count": np.int64(3),
        "score": np.float32(1.25),
        "items": np.array([1, 2, 3], dtype=np.int32),
        "nested": {"available": np.bool_(True)},
    }

    cleaned = ensure_json_serializable(raw_result)

    assert cleaned == {
        "count": 3,
        "score": pytest.approx(1.25),
        "items": [1, 2, 3],
        "nested": {"available": True},
    }
    assert type(cleaned["count"]) is int
    assert type(cleaned["score"]) is float
    assert type(cleaned["nested"]["available"]) is bool
    assert json.loads(json.dumps(cleaned)) == cleaned


def test_model_formatter_unwraps_mcp_text_content() -> None:
    result = ToolExecutionResult(
        tool_name="synthetic_tool",
        success=True,
        result={
            "content": [
                {"type": "text", "text": "synthetic MCP response"},
            ]
        },
    )

    formatted = format_function_call_result_for_model(result)

    assert formatted == (
        "Tool synthetic_tool executed successfully:\nsynthetic MCP response"
    )


def test_model_formatter_unwraps_result_mapping() -> None:
    result = ToolExecutionResult(
        tool_name="synthetic_tool",
        success=True,
        result={"result": {"answer": 42}},
    )

    formatted = format_function_call_result_for_model(result)

    assert formatted == (
        'Tool synthetic_tool executed successfully:\n{\n  "answer": 42\n}'
    )


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        pytest.param(
            ToolExecutionResult(
                tool_name="synthetic_tool",
                success=True,
                result="plain output",
            ),
            "Tool synthetic_tool executed successfully:\nplain output",
            id="successful-string",
        ),
        pytest.param(
            ToolExecutionResult(
                tool_name="synthetic_tool",
                success=True,
                result=[],
            ),
            "Tool synthetic_tool executed successfully (empty list)",
            id="successful-empty-list",
        ),
        pytest.param(
            ToolExecutionResult(
                tool_name="synthetic_tool",
                success=False,
                result=None,
                error="synthetic failure",
                execution_time=1.25,
            ),
            "Tool synthetic_tool failed: synthetic failure (after 1.25s)",
            id="failed-with-duration",
        ),
    ],
)
def test_model_formatter_preserves_success_and_failure_meaning(
    result: ToolExecutionResult,
    expected: str,
) -> None:
    assert format_function_call_result_for_model(result) == expected


def test_large_mapping_is_bounded_and_reports_truncation(
    bridge: MCPGeminiBridge,
) -> None:
    raw_result = {"payload": "x" * (1024 * 1024)}

    processed = bridge._handle_large_result(raw_result, "synthetic_tool")

    assert processed["payload"].startswith("x" * 1000)
    assert processed["payload"].endswith("(truncated from 1048576 chars)")
    assert len(processed["payload"]) < 1100
    assert processed["_metadata"] == {
        "original_size_bytes": 1048591,
        "truncated": True,
        "tool_name": "synthetic_tool",
    }


def test_large_list_is_bounded_and_reports_omitted_count(
    bridge: MCPGeminiBridge,
) -> None:
    raw_result = ["x" * 11000 for _ in range(101)]

    processed = bridge._handle_large_result(raw_result, "synthetic_tool")

    assert processed[:50] == raw_result[:50]
    assert processed[50] == "... (51 more items truncated)"
    assert len(processed) == 51


def test_large_string_is_bounded_and_reports_original_length(
    bridge: MCPGeminiBridge,
) -> None:
    raw_result = "x" * (1024 * 1024)

    processed = bridge._handle_large_result(raw_result, "synthetic_tool")

    assert processed.startswith("x" * 5000)
    assert processed.endswith("(truncated from 1048576 characters)")
    assert len(processed) < 5100
