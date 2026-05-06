"""
Base abstractions for Model Providers in Aura.
Defines the shared interface and data structures for LLM integration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional


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
