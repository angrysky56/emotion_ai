"""Provider-neutral tool catalog and execution boundary tests."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from aura_backend.providers.base import ToolDefinition
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.tools import (
    ToolCatalog,
    ToolExecutionLimits,
    ToolExecutionResult,
    ToolExecutor,
    ToolRegistration,
    ToolSource,
    normalize_tool_name,
)


def definition(
    name: str = "memory.search",
    schema: Mapping[str, Any] | None = None,
) -> ToolDefinition:
    """Build a small object-input definition for catalog tests."""
    return ToolDefinition(
        name=name,
        description="Search synthetic memory",
        input_schema=schema
        or {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )


def registration(
    name: str = "memory.search",
    *,
    source: ToolSource = ToolSource.MCP,
    server: str = "synthetic-server",
    schema: Mapping[str, Any] | None = None,
) -> ToolRegistration:
    """Build one immutable registration with explicit routing metadata."""
    return ToolRegistration(
        definition=definition(name, schema),
        source=source,
        server=server,
    )


def test_catalog_exposes_immutable_provider_safe_definitions_and_routes() -> None:
    route = registration()
    catalog = ToolCatalog((route,))

    assert normalize_tool_name("memory.search") == "memory_search"
    assert catalog.definitions == (
        ToolDefinition(
            name="memory_search",
            description="Search synthetic memory",
            input_schema=route.definition.input_schema,
        ),
    )
    assert catalog.registrations == (route,)
    assert catalog.resolve("memory_search") is route
    assert route.original_name == "memory.search"
    assert route.provider_name == "memory_search"
    assert route.server == "synthetic-server"

    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        route.server = "changed"  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        route.definition.input_schema["type"] = "array"  # type: ignore[index]


@pytest.mark.parametrize(
    "schema",
    [
        pytest.param(
            {"type": "array", "items": {"type": "string"}},
            id="arguments-must-be-object",
        ),
        pytest.param(
            {"type": "object", "properties": {"count": {"type": "invalid"}}},
            id="invalid-schema-keyword-value",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {"payload": {"$ref": "https://example.invalid/schema"}},
            },
            id="remote-reference",
        ),
    ],
)
def test_registration_rejects_malformed_or_unsafe_schemas(
    schema: Mapping[str, Any],
) -> None:
    with pytest.raises(ValueError, match="schema"):
        registration(schema=schema)


@pytest.mark.parametrize("name", ["", "   "])
def test_definition_rejects_empty_names(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        definition(name)


def test_catalog_rejects_duplicate_and_normalized_name_collisions() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ToolCatalog((registration("memory.search"), registration("memory.search")))

    with pytest.raises(ValueError, match="collision"):
        ToolCatalog((registration("memory.search"), registration("memory_search")))


@pytest.mark.asyncio
async def test_executor_validates_and_dispatches_complete_immutable_arguments() -> None:
    calls: list[tuple[ToolRegistration, dict[str, Any]]] = []

    async def dispatch(
        route: ToolRegistration,
        arguments: Mapping[str, Any],
    ) -> object:
        calls.append((route, dict(arguments)))
        with pytest.raises((AttributeError, TypeError)):
            arguments["query"] = "changed"  # type: ignore[index]
        return {"matches": ["synthetic"]}

    route = registration()
    executor = ToolExecutor(ToolCatalog((route,)), dispatch)

    result = await executor.execute("memory_search", '{"query":"safe"}')

    assert isinstance(result, ToolExecutionResult)
    assert result.tool_name == "memory_search"
    assert result.value == {"matches": ("synthetic",)}
    assert result.output_bytes > 0
    assert calls == [(route, {"query": "safe"})]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "code"),
    [
        pytest.param("{malformed", ProviderErrorCode.MALFORMED_RESPONSE, id="json"),
        pytest.param("[]", ProviderErrorCode.MALFORMED_RESPONSE, id="not-object"),
        pytest.param("{}", ProviderErrorCode.MALFORMED_RESPONSE, id="required"),
        pytest.param(
            '{"query":"safe","extra":true}',
            ProviderErrorCode.MALFORMED_RESPONSE,
            id="extra-property",
        ),
    ],
)
async def test_executor_rejects_malformed_or_incomplete_argument_json(
    arguments: str,
    code: ProviderErrorCode,
) -> None:
    async def dispatch(
        _route: ToolRegistration,
        _arguments: Mapping[str, Any],
    ) -> object:
        raise AssertionError("invalid arguments must fail before dispatch")

    executor = ToolExecutor(ToolCatalog((registration(),)), dispatch)

    with pytest.raises(ProviderFailure) as failure:
        await executor.execute("memory_search", arguments)

    assert failure.value.code is code


@pytest.mark.asyncio
async def test_executor_enforces_timeout_output_argument_and_turn_bounds() -> None:
    async def blocked(
        _route: ToolRegistration,
        _arguments: Mapping[str, Any],
    ) -> object:
        await asyncio.Event().wait()
        return None

    limits = ToolExecutionLimits(
        timeout_seconds=0.01,
        max_argument_bytes=32,
        max_result_bytes=32,
        max_tool_turns=2,
    )
    catalog = ToolCatalog((registration(),))

    with pytest.raises(ProviderFailure) as timeout:
        await ToolExecutor(catalog, blocked, limits=limits).execute(
            "memory_search", {"query": "safe"}
        )
    assert timeout.value.code is ProviderErrorCode.TIMEOUT

    async def oversized_result(
        _route: ToolRegistration,
        _arguments: Mapping[str, Any],
    ) -> object:
        return {"secret": "x" * 64}

    executor = ToolExecutor(catalog, oversized_result, limits=limits)
    for arguments, tool_turn in [({"query": "x" * 64}, 1), ({"query": "safe"}, 3)]:
        with pytest.raises(ProviderFailure) as resource:
            await executor.execute("memory_search", arguments, tool_turn=tool_turn)
        assert resource.value.code is ProviderErrorCode.RESOURCE_LIMIT

    with pytest.raises(ProviderFailure) as output:
        await executor.execute("memory_search", {"query": "safe"})
    assert output.value.code is ProviderErrorCode.RESOURCE_LIMIT


@pytest.mark.asyncio
async def test_executor_failures_and_default_diagnostics_redact_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_secret = "SYNTHETIC_TOOL_SECRET"

    async def failing(
        _route: ToolRegistration,
        _arguments: Mapping[str, Any],
    ) -> object:
        raise RuntimeError(raw_secret)

    executor = ToolExecutor(ToolCatalog((registration(),)), failing)

    with pytest.raises(ProviderFailure) as failure:
        await executor.execute("memory_search", {"query": raw_secret})

    assert failure.value.code is ProviderErrorCode.UNAVAILABLE
    diagnostics = f"{failure.value!s} {failure.value!r} {caplog.text}"
    assert raw_secret not in diagnostics


@pytest.mark.asyncio
async def test_result_default_diagnostics_hide_tool_content() -> None:
    raw_secret = "SYNTHETIC_RESULT_SECRET"

    async def dispatch(
        _route: ToolRegistration,
        _arguments: Mapping[str, Any],
    ) -> object:
        return {"content": raw_secret}

    result = await ToolExecutor(
        ToolCatalog((registration(),)), dispatch
    ).execute("memory_search", {"query": "safe"})

    assert result.value == {"content": raw_secret}
    assert raw_secret not in repr(result)
    assert raw_secret not in str(result)


class RecordingInternalTools:
    """Internal registry fake that records only calls crossing its public seam."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_tool_list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "aura.reflect",
                "description": "Reflect on synthetic text",
                "server": "aura-internal",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            }
        ]

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> object:
        self.calls.append((name, arguments))
        return {"source": "internal", "ok": True}


class RecordingMCPClient:
    """MCP fake that never starts a process or reads an active tool result."""

    def __init__(self, *, fail_listing: bool = False) -> None:
        self.fail_listing = fail_listing
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_all_tools(self) -> dict[str, dict[str, Any]]:
        if self.fail_listing:
            raise RuntimeError("SYNTHETIC_MCP_LIST_SECRET")
        return {
            "weather.current": {
                "name": "current",
                "description": "Read synthetic weather",
                "server": "weather-server",
                "connected": True,
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                    "additionalProperties": False,
                },
            }
        }

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        self.calls.append((name, arguments))
        return {"source": "mcp", "ok": True}


@pytest.mark.asyncio
async def test_mcp_system_builds_and_dispatches_internal_only_neutral_tools() -> None:
    from aura_backend.mcp_system import (
        get_provider_tool_catalog,
        get_provider_tool_executor,
    )

    internal = RecordingInternalTools()
    catalog = await get_provider_tool_catalog(internal_tools=internal)
    executor = get_provider_tool_executor(catalog, internal_tools=internal)

    assert catalog.definitions == (
        ToolDefinition(
            name="aura_reflect",
            description="Reflect on synthetic text",
            input_schema=internal.get_tool_list()[0]["parameters"],
        ),
    )
    result = await executor.execute("aura_reflect", {"text": "synthetic"})
    assert result.value == {"source": "internal", "ok": True}
    assert internal.calls == [("aura.reflect", {"text": "synthetic"})]


@pytest.mark.asyncio
async def test_mcp_system_builds_and_dispatches_mcp_only_neutral_tools() -> None:
    from aura_backend.mcp_system import (
        get_provider_tool_catalog,
        get_provider_tool_executor,
    )

    mcp = RecordingMCPClient()
    catalog = await get_provider_tool_catalog(mcp_client=mcp)
    executor = get_provider_tool_executor(catalog, mcp_client=mcp)

    assert tuple(item.name for item in catalog.definitions) == ("weather_current",)
    route = catalog.resolve("weather_current")
    assert route.source is ToolSource.MCP
    assert route.original_name == "weather.current"
    assert route.server == "weather-server"

    result = await executor.execute("weather_current", {"city": "synthetic"})
    assert result.value == {"source": "mcp", "ok": True}
    assert mcp.calls == [("weather.current", {"city": "synthetic"})]


@pytest.mark.asyncio
async def test_mcp_system_combines_both_sources_with_the_same_catalog_shape() -> None:
    from aura_backend.mcp_system import (
        get_provider_tool_catalog,
        get_provider_tool_executor,
    )

    internal = RecordingInternalTools()
    mcp = RecordingMCPClient()
    catalog = await get_provider_tool_catalog(
        mcp_client=mcp,
        internal_tools=internal,
    )
    executor = get_provider_tool_executor(
        catalog,
        mcp_client=mcp,
        internal_tools=internal,
    )

    assert tuple(item.name for item in catalog.definitions) == (
        "aura_reflect",
        "weather_current",
    )
    internal_result = await executor.execute(
        "aura_reflect", {"text": "synthetic"}
    )
    mcp_result = await executor.execute(
        "weather_current", {"city": "synthetic"}
    )
    assert isinstance(internal_result, ToolExecutionResult)
    assert isinstance(mcp_result, ToolExecutionResult)


@pytest.mark.asyncio
async def test_unavailable_optional_mcp_is_empty_and_execution_fails_typed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from aura_backend.mcp_system import (
        get_mcp_bridge,
        get_provider_tool_catalog,
        get_provider_tool_executor,
    )

    catalog = await get_provider_tool_catalog(
        mcp_client=RecordingMCPClient(fail_listing=True)
    )

    assert len(catalog) == 0
    assert catalog.definitions == ()
    assert callable(get_mcp_bridge)
    assert "SYNTHETIC_MCP_LIST_SECRET" not in caplog.text

    executor = get_provider_tool_executor(catalog)
    with pytest.raises(ProviderFailure) as failure:
        await executor.execute("missing_tool", {})
    assert failure.value.code is ProviderErrorCode.UNAVAILABLE


def test_new_mcp_system_surface_has_no_gemini_types_or_bridge_mapping() -> None:
    from aura_backend import mcp_system

    public_objects = (
        mcp_system.get_provider_tool_catalog,
        mcp_system.get_provider_tool_executor,
    )
    annotations = " ".join(
        str(inspect.get_annotations(item, eval_str=False)) for item in public_objects
    ).lower()

    assert "google" not in annotations
    assert "gemini" not in annotations
    assert "_tool_mapping" not in inspect.getsource(
        mcp_system.get_provider_tool_executor
    )
