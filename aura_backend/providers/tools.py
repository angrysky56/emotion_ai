"""Immutable provider-neutral tool registration and execution contracts.

Provider adapters may translate :class:`ToolDefinition` values into SDK-specific
shapes, but discovery, routing, validation, deadlines, and result bounds live at
this boundary.  Tool arguments, result bodies, and source exceptions are never
placed in default diagnostics.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

from jsonschema import exceptions as schema_exceptions
from jsonschema.validators import validator_for

from aura_backend.providers.base import JsonValue, ToolDefinition
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure


_UNSAFE_TOOL_NAME = re.compile(r"[^A-Za-z0-9_-]")
_SAFE_SERVER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MAX_PROVIDER_NAME_LENGTH = 64
_MAX_SCHEMA_BYTES = 64 * 1024


def normalize_tool_name(name: str) -> str:
    """Return the shared OpenAI-compatible name used by every adapter.

    Normalization is intentionally lossy.  :class:`ToolCatalog` therefore rejects
    every post-normalization collision instead of guessing which tool to route.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool name must be non-empty text")
    normalized = _UNSAFE_TOOL_NAME.sub("_", name)[:_MAX_PROVIDER_NAME_LENGTH]
    if not normalized:
        raise ValueError("tool name has no provider-safe representation")
    return normalized


def _to_json_data(value: object) -> Any:
    """Copy JSON-compatible data into ordinary dict/list/scalar containers."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            result[key] = _to_json_data(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_to_json_data(item) for item in value]
    raise TypeError("value must contain only JSON-compatible data")


def _freeze_json(value: object) -> JsonValue:
    """Recursively freeze already validated JSON-compatible data."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise TypeError("value must contain only JSON-compatible data")


def _encoded_json_size(value: object) -> int:
    """Return canonical UTF-8 JSON size while rejecting non-standard values."""
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return len(encoded.encode("utf-8"))


def _contains_remote_reference(value: object) -> bool:
    """Reject schemas that could retrieve a reference outside the local document."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str) and not item.startswith("#"):
                return True
            if _contains_remote_reference(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_remote_reference(item) for item in value)
    return False


def _validated_schema(definition: ToolDefinition) -> dict[str, Any]:
    """Return a validated object-input schema without echoing invalid content."""
    try:
        schema = _to_json_data(definition.input_schema)
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise ValueError("tool schema must describe an argument object")
        if _encoded_json_size(schema) > _MAX_SCHEMA_BYTES:
            raise ValueError("tool schema exceeds the supported bound")
        if _contains_remote_reference(schema):
            raise ValueError("tool schema contains an unsafe remote reference")
        validator = validator_for(schema)
        validator.check_schema(schema)
    except (schema_exceptions.SchemaError, TypeError, ValueError):
        raise ValueError("tool schema is invalid or unsupported") from None
    return schema


class ToolSource(str, Enum):
    """Execution owners supported by Aura's neutral tool boundary."""

    INTERNAL = "internal"
    MCP = "mcp"


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    """One immutable definition plus the metadata required for safe dispatch."""

    definition: ToolDefinition
    source: ToolSource
    server: str
    provider_name: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.definition, ToolDefinition):
            raise TypeError("definition must be a ToolDefinition")
        if not isinstance(self.source, ToolSource):
            raise TypeError("source must be a ToolSource")
        if not isinstance(self.server, str) or _SAFE_SERVER_NAME.fullmatch(self.server) is None:
            raise ValueError("server must be safe routing metadata")
        _validated_schema(self.definition)
        object.__setattr__(
            self,
            "provider_name",
            normalize_tool_name(self.definition.name),
        )

    @property
    def original_name(self) -> str:
        """Return the source-owned name used only after catalog resolution."""
        return self.definition.name

    @property
    def provider_definition(self) -> ToolDefinition:
        """Return the immutable definition safe to expose to provider adapters."""
        return ToolDefinition(
            name=self.provider_name,
            description=self.definition.description,
            input_schema=self.definition.input_schema,
        )


@dataclass(frozen=True, slots=True)
class ToolCatalog:
    """Collision-safe immutable catalog of all available tool registrations."""

    registrations: tuple[ToolRegistration, ...]
    _lookup: Mapping[str, ToolRegistration] = field(init=False, repr=False)
    _definitions: tuple[ToolDefinition, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.registrations, tuple) or not all(
            isinstance(item, ToolRegistration) for item in self.registrations
        ):
            raise TypeError("registrations must be an immutable ToolRegistration tuple")

        original_names: set[str] = set()
        by_provider_name: dict[str, ToolRegistration] = {}
        for item in self.registrations:
            if item.original_name in original_names:
                raise ValueError("duplicate original tool name")
            if item.provider_name in by_provider_name:
                raise ValueError("provider-safe tool name collision")
            original_names.add(item.original_name)
            by_provider_name[item.provider_name] = item

        object.__setattr__(self, "_lookup", MappingProxyType(by_provider_name))
        object.__setattr__(
            self,
            "_definitions",
            tuple(item.provider_definition for item in self.registrations),
        )

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        """Return provider-safe definitions in deterministic registration order."""
        return self._definitions

    def resolve(self, provider_name: str) -> ToolRegistration:
        """Resolve provider-safe name to immutable routing metadata."""
        try:
            return self._lookup[provider_name]
        except (KeyError, TypeError):
            raise ProviderFailure(
                code=ProviderErrorCode.UNAVAILABLE,
                provider="tools",
                retryable=False,
            ) from None

    def __len__(self) -> int:
        return len(self.registrations)


@dataclass(frozen=True, slots=True)
class ToolExecutionLimits:
    """Finite policy applied before and during every neutral tool call."""

    timeout_seconds: float = 30.0
    max_argument_bytes: int = 64 * 1024
    max_result_bytes: int = 1024 * 1024
    max_tool_turns: int = 5

    def __post_init__(self) -> None:
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(float(self.timeout_seconds))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be finite and positive")
        for name in ("max_argument_bytes", "max_result_bytes", "max_tool_turns"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """A successful bounded result whose content is hidden from diagnostics."""

    tool_name: str
    value: JsonValue = field(repr=False)
    output_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.tool_name, str) or not self.tool_name:
            raise ValueError("tool_name must be non-empty text")
        if not isinstance(self.output_bytes, int) or self.output_bytes < 0:
            raise ValueError("output_bytes must be a non-negative integer")
        object.__setattr__(self, "value", _freeze_json(_to_json_data(self.value)))

    def __str__(self) -> str:
        """Return content-free metadata suitable for default diagnostics."""
        return f"tool execution succeeded: tool={self.tool_name} bytes={self.output_bytes}"


ToolDispatcher = Callable[
    [ToolRegistration, Mapping[str, JsonValue]],
    Awaitable[object],
]


class ToolExecutor:
    """Validate and dispatch calls through one bounded provider-neutral policy."""

    __slots__ = ("catalog", "limits", "_dispatch")

    def __init__(
        self,
        catalog: ToolCatalog,
        dispatch: ToolDispatcher,
        *,
        limits: ToolExecutionLimits | None = None,
    ) -> None:
        if not isinstance(catalog, ToolCatalog):
            raise TypeError("catalog must be a ToolCatalog")
        if not callable(dispatch):
            raise TypeError("dispatch must be callable")
        self.catalog = catalog
        self.limits = limits or ToolExecutionLimits()
        self._dispatch = dispatch

    async def execute(
        self,
        provider_name: str,
        arguments: str | Mapping[str, object],
        *,
        tool_turn: int = 1,
        correlation_id: str | None = None,
    ) -> ToolExecutionResult:
        """Execute one validated call or raise a content-free typed failure."""
        self._validate_turn(tool_turn, correlation_id)
        route = self.catalog.resolve(provider_name)
        validated_arguments = self._validate_arguments(
            route,
            arguments,
            correlation_id,
        )

        try:
            async with asyncio.timeout(float(self.limits.timeout_seconds)):
                raw_result = await self._dispatch(route, validated_arguments)
        except TimeoutError:
            raise self._failure(
                ProviderErrorCode.TIMEOUT,
                correlation_id,
                retryable=True,
            ) from None
        except asyncio.CancelledError:
            raise
        except Exception:
            raise self._failure(
                ProviderErrorCode.UNAVAILABLE,
                correlation_id,
                retryable=True,
            ) from None

        try:
            result_data = _to_json_data(raw_result)
            output_bytes = _encoded_json_size(result_data)
        except (TypeError, ValueError):
            raise self._failure(
                ProviderErrorCode.MALFORMED_RESPONSE,
                correlation_id,
            ) from None
        if output_bytes > self.limits.max_result_bytes:
            raise self._failure(
                ProviderErrorCode.RESOURCE_LIMIT,
                correlation_id,
            ) from None

        return ToolExecutionResult(
            tool_name=route.provider_name,
            value=_freeze_json(result_data),
            output_bytes=output_bytes,
        )

    def _validate_turn(self, tool_turn: int, correlation_id: str | None) -> None:
        if (
            not isinstance(tool_turn, int)
            or isinstance(tool_turn, bool)
            or tool_turn <= 0
            or tool_turn > self.limits.max_tool_turns
        ):
            raise self._failure(
                ProviderErrorCode.RESOURCE_LIMIT,
                correlation_id,
            ) from None

    def _validate_arguments(
        self,
        route: ToolRegistration,
        arguments: str | Mapping[str, object],
        correlation_id: str | None,
    ) -> Mapping[str, JsonValue]:
        try:
            if isinstance(arguments, str):
                if len(arguments.encode("utf-8")) > self.limits.max_argument_bytes:
                    raise OverflowError
                parsed = json.loads(
                    arguments,
                    parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
                )
            else:
                parsed = _to_json_data(arguments)
            if not isinstance(parsed, dict):
                raise TypeError
            argument_bytes = _encoded_json_size(parsed)
        except OverflowError:
            raise self._failure(
                ProviderErrorCode.RESOURCE_LIMIT,
                correlation_id,
            ) from None
        except (json.JSONDecodeError, TypeError, ValueError):
            raise self._failure(
                ProviderErrorCode.MALFORMED_RESPONSE,
                correlation_id,
            ) from None

        if argument_bytes > self.limits.max_argument_bytes:
            raise self._failure(
                ProviderErrorCode.RESOURCE_LIMIT,
                correlation_id,
            ) from None

        schema = _validated_schema(route.definition)
        try:
            validator_for(schema)(schema).validate(parsed)
        except Exception:
            raise self._failure(
                ProviderErrorCode.MALFORMED_RESPONSE,
                correlation_id,
            ) from None
        return _freeze_json(parsed)  # type: ignore[return-value]

    @staticmethod
    def _failure(
        code: ProviderErrorCode,
        correlation_id: str | None,
        *,
        retryable: bool = False,
    ) -> ProviderFailure:
        return ProviderFailure(
            code=code,
            provider="tools",
            retryable=retryable,
            correlation_id=correlation_id,
        )
