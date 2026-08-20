"""Provider-neutral tool catalog and execution boundary tests."""

from __future__ import annotations

import asyncio
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
