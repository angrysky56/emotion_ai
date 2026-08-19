"""Provider-neutral domain contracts and the temporary legacy provider surface.

The frozen types in this module are the stable boundary used by new provider and
runtime code.  The mutable ``Message``/``ProviderResponse`` records and
``BaseProvider`` ABC remain temporarily available so Aura's characterized route
and existing adapters continue to run while later Phase 2 plans migrate them.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Protocol, runtime_checkable


JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


def _freeze_json(value: object) -> JsonValue:
    """Return a recursively immutable JSON-like value without SDK objects."""
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if isinstance(value, Mapping):
        frozen = {
            str(key): _freeze_json(item)
            for key, item in value.items()
            if isinstance(key, str)
        }
        if len(frozen) != len(value):
            raise TypeError("JSON object keys must be strings")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise TypeError("value must contain only JSON-compatible data")


class ProviderHealthStatus(str, Enum):
    """Provider readiness states that cannot be confused with boolean success."""

    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    """One immutable provider-neutral conversation message."""

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"user", "assistant", "system", "tool"}:
            raise ValueError("unsupported provider message role")
        if not isinstance(self.content, str):
            raise TypeError("message content must be text")


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """An immutable provider-neutral tool description and JSON input schema."""

    name: str
    description: str
    input_schema: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("tool name must be non-empty text")
        if not isinstance(self.description, str):
            raise TypeError("tool description must be text")
        if not isinstance(self.input_schema, Mapping):
            raise TypeError("tool input_schema must be a JSON object")
        frozen_schema = _freeze_json(self.input_schema)
        if not isinstance(frozen_schema, Mapping):
            raise TypeError("tool input_schema must be a JSON object")
        object.__setattr__(self, "input_schema", frozen_schema)


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Normalized non-negative token accounting when a provider supplies it."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Complete immutable input to a provider adapter."""

    messages: tuple[ProviderMessage, ...]
    system_instruction: str | None = None
    tools: tuple[ToolDefinition, ...] = ()
    temperature: float = 0.7
    max_tokens: int | None = None
    session_id: str | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ValueError("provider request requires an immutable message tuple")
        if not all(isinstance(message, ProviderMessage) for message in self.messages):
            raise TypeError("messages must contain only ProviderMessage values")
        if not isinstance(self.tools, tuple) or not all(
            isinstance(tool, ToolDefinition) for tool in self.tools
        ):
            raise TypeError("tools must be an immutable ToolDefinition tuple")
        if self.system_instruction is not None and not isinstance(
            self.system_instruction, str
        ):
            raise TypeError("system_instruction must be text or None")
        if (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not math.isfinite(float(self.temperature))
            or not 0.0 <= float(self.temperature) <= 2.0
        ):
            raise ValueError("temperature must be finite and between 0 and 2")
        if self.max_tokens is not None and (
            not isinstance(self.max_tokens, int)
            or isinstance(self.max_tokens, bool)
            or self.max_tokens <= 0
        ):
            raise ValueError("max_tokens must be a positive integer or None")


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """A completed successful answer; failures are represented only by exceptions."""

    content: str
    usage: ProviderUsage | None = None
    reflection_summary: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("completed provider content must be non-empty text")
        if self.usage is not None and not isinstance(self.usage, ProviderUsage):
            raise TypeError("usage must be ProviderUsage or None")
        if self.reflection_summary is not None and not isinstance(
            self.reflection_summary, str
        ):
            raise TypeError("reflection_summary must be text or None")


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Side-effect-free provider/model readiness state with safe metadata only."""

    provider: str
    model: str | None
    status: ProviderHealthStatus
    retryable: bool = False
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider:
            raise ValueError("provider health requires a provider name")
        if self.model is not None and not isinstance(self.model, str):
            raise TypeError("model must be text or None")
        if not isinstance(self.status, ProviderHealthStatus):
            raise TypeError("status must be ProviderHealthStatus")
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be a bool")

    @property
    def ready(self) -> bool:
        """Return true only for the explicit ready state."""
        return self.status is ProviderHealthStatus.READY


@dataclass(frozen=True, slots=True)
class TextDelta:
    """One incremental text fragment from an open provider stream."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("text delta must contain text")


@dataclass(frozen=True, slots=True)
class ToolCallDelta:
    """One indexed fragment of an in-progress provider tool call."""

    index: int
    call_id: str | None = None
    name: str | None = None
    arguments_fragment: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.index, int) or isinstance(self.index, bool) or self.index < 0:
            raise ValueError("tool-call delta index must be a non-negative integer")
        fragments = (self.call_id, self.name, self.arguments_fragment)
        if not any(fragment is not None for fragment in fragments):
            raise ValueError("tool-call delta requires at least one fragment")
        if not all(fragment is None or isinstance(fragment, str) for fragment in fragments):
            raise TypeError("tool-call delta fragments must be text or None")


@dataclass(frozen=True, slots=True)
class Completed:
    """The sole successful stream terminal, carrying a validated result."""

    result: ProviderResult

    def __post_init__(self) -> None:
        if not isinstance(self.result, ProviderResult):
            raise TypeError("Completed requires a ProviderResult")


StreamEvent = TextDelta | ToolCallDelta | Completed


@runtime_checkable
class Provider(Protocol):
    """Adapter-neutral async provider behavior consumed by Aura's runtime."""

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        """Generate exactly one completed result or raise a provider failure."""
        ...

    def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        """Yield incremental events ending in exactly one valid completion."""
        ...

    async def clear_session(self, session_id: str) -> None:
        """Release any provider-local state associated with a session key."""
        ...

    async def health(self) -> ProviderHealth:
        """Return cached or bounded provider health without generating content."""
        ...

    async def aclose(self) -> None:
        """Close adapter-owned resources."""
        ...


@dataclass
class ToolCall:
    """Represents a tool call from the model."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    call_id: str
    output: Any
    is_error: bool = False


@dataclass
class Message:
    """Represents a single message in a conversation."""

    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_result_id: Optional[str] = None  # Links back to a ToolCall.id


@dataclass
class ProviderResponse:
    content: str
    role: str = "assistant"
    tool_calls: Optional[List[ToolCall]] = None
    thoughts: Optional[str] = None
    raw_response: Any = None
    error: Optional[str] = None


class BaseProvider(ABC):
    """Abstract Base Class for LLM providers."""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[Any] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ProviderResponse:
        """Generate a single response from the model."""
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[Any] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[ProviderResponse]:
        """Stream the response from the model."""
        pass

    @abstractmethod
    async def convert_mcp_tools(self, mcp_tools: List[Dict[str, Any]]) -> Any:
        """Convert MCP tool schemas to provider-specific tool formats."""
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        """Clear a specific chat session."""
        pass
