"""Lazy, asynchronous, stateless Gemini provider adapter.

Google SDK values are translated at this edge and never cross Aura's stable
provider boundary.  Each operation creates an ephemeral async chat from the
complete request, so the adapter owns no hidden conversation history.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any

from aura_backend.providers.base import (
    BaseProvider,
    Completed,
    Message,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderResult,
    ProviderUsage,
    StreamEvent,
    TextDelta,
    ToolCallDelta,
    ToolDefinition,
)
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.tools import ToolExecutor


ClientFactory = Callable[..., object]
_NORMAL_FINISH_REASONS = {"STOP", "FINISH_REASON_UNSPECIFIED", ""}
_RESOURCE_FINISH_REASONS = {"MAX_TOKENS", "RECITATION"}


def _default_client_factory(**kwargs: object) -> object:
    """Import and construct the optional SDK only after Gemini is selected."""
    from google import genai

    return genai.Client(**kwargs)


def _field(value: object, name: str, default: Any = None) -> Any:
    """Read one field from an SDK-like mapping or object."""
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _plain_json(value: object) -> object:
    """Convert immutable JSON-like values into SDK-safe containers."""
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


async def _close_resource(resource: object) -> None:
    """Close an SDK stream/client through its supported local method."""
    close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
    if close is None:
        return
    outcome = close()
    if inspect.isawaitable(outcome):
        await outcome


class GeminiProvider(BaseProvider):
    """Provider-neutral Gemini implementation using only ``client.aio``."""

    def __init__(
        self,
        api_key: str | None,
        model_name: str | None = None,
        thinking_budget: int = 16000,
        mcp_client_manager: object | None = None,
        aura_internal_tools: object | None = None,
        *,
        client: object | None = None,
        client_factory: ClientFactory = _default_client_factory,
        tool_executor: ToolExecutor | None = None,
        max_tool_turns: int | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderFailure(
                code=ProviderErrorCode.CONFIGURATION,
                provider="gemini",
                setting_name="GEMINI_API_KEY",
            )
        del mcp_client_manager, aura_internal_tools
        self.provider_name = "gemini"
        self.model_name = model_name or os.getenv(
            "AURA_MODEL", "gemini-2.0-flash-thinking-exp-01-21"
        )
        self.thinking_budget = thinking_budget
        self._tool_executor = tool_executor
        configured_turns = max_tool_turns or int(os.getenv("TOOL_CALL_MAX_RETRIES", "3"))
        self._max_tool_turns = max(1, configured_turns)
        self._closed = False
        if client is None:
            client = client_factory(
                api_key=api_key,
                http_options={"api_version": "v1alpha"},
            )
        try:
            self._aio = getattr(client, "aio")
        except (AttributeError, TypeError):
            raise ProviderFailure(
                code=ProviderErrorCode.CONFIGURATION,
                provider="gemini",
                setting_name="GEMINI_API_KEY",
            ) from None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(provider={self.provider_name!r}, "
            f"model={self.model_name!r}, closed={self._closed!r})"
        )

    def _failure(
        self,
        code: ProviderErrorCode,
        request: ProviderRequest | None = None,
        *,
        retryable: bool = False,
        partial_event_count: int = 0,
    ) -> ProviderFailure:
        return ProviderFailure(
            code=code,
            provider=self.provider_name,
            model=self.model_name,
            retryable=retryable,
            correlation_id=request.correlation_id if request is not None else None,
            partial_event_count=partial_event_count,
        )

    def _map_error(
        self,
        error: BaseException,
        request: ProviderRequest,
        *,
        partial_event_count: int = 0,
    ) -> ProviderFailure:
        if isinstance(error, ProviderFailure):
            if error.partial_event_count >= partial_event_count:
                return error
            return self._failure(
                error.code,
                request,
                retryable=error.retryable,
                partial_event_count=partial_event_count,
            )
        if partial_event_count:
            return self._failure(
                ProviderErrorCode.STREAM_INTERRUPTED,
                request,
                retryable=True,
                partial_event_count=partial_event_count,
            )
        status = _field(error, "code", _field(error, "status_code"))
        if isinstance(status, str) and status.isdigit():
            status = int(status)
        if isinstance(error, (TimeoutError, asyncio.TimeoutError)) or status in {408, 504}:
            code, retryable = ProviderErrorCode.TIMEOUT, True
        elif status in {401, 403}:
            code, retryable = ProviderErrorCode.AUTHENTICATION, False
        elif status == 404:
            code, retryable = ProviderErrorCode.MODEL_NOT_FOUND, False
        elif status == 429:
            code, retryable = ProviderErrorCode.RATE_LIMITED, True
        elif isinstance(error, (ConnectionError, OSError)) or (
            isinstance(status, int) and status >= 500
        ):
            code, retryable = ProviderErrorCode.UNAVAILABLE, True
        else:
            code, retryable = ProviderErrorCode.MALFORMED_RESPONSE, False
        return self._failure(code, request, retryable=retryable)

    @staticmethod
    def _finish_reason(candidate: object) -> str | None:
        raw = _field(candidate, "finish_reason")
        if raw is None:
            return None
        value = _field(raw, "value", raw)
        return str(value).rsplit(".", 1)[-1].upper()

    def _validate_finish(
        self,
        candidate: object,
        request: ProviderRequest,
        *,
        partial_event_count: int = 0,
    ) -> None:
        reason = self._finish_reason(candidate)
        if reason is None or reason in _NORMAL_FINISH_REASONS:
            return
        if reason in _RESOURCE_FINISH_REASONS:
            raise self._failure(
                ProviderErrorCode.RESOURCE_LIMIT,
                request,
                partial_event_count=partial_event_count,
            )
        raise self._failure(
            ProviderErrorCode.MALFORMED_RESPONSE,
            request,
            partial_event_count=partial_event_count,
        )

    @staticmethod
    def _candidate(response: object) -> object:
        candidates = _field(response, "candidates")
        if not isinstance(candidates, (list, tuple)) or not candidates:
            raise ValueError("missing Gemini candidate")
        candidate = candidates[0]
        content = _field(candidate, "content")
        parts = _field(content, "parts") if content is not None else None
        if not isinstance(parts, (list, tuple)) or not parts:
            raise ValueError("missing Gemini content parts")
        return candidate

    @staticmethod
    def _parts(candidate: object) -> list[object]:
        content = _field(candidate, "content")
        parts = _field(content, "parts") if content is not None else None
        if not isinstance(parts, (list, tuple)):
            raise ValueError("invalid Gemini content parts")
        return list(parts)

    @staticmethod
    def _extract_parts(candidate: object) -> tuple[list[str], list[tuple[str, object]]]:
        text_parts: list[str] = []
        function_calls: list[tuple[str, object]] = []
        for part in GeminiProvider._parts(candidate):
            if _field(part, "thought") is True:
                continue
            text = _field(part, "text")
            if text is not None:
                if not isinstance(text, str):
                    raise ValueError("invalid Gemini text")
                if text:
                    text_parts.append(text)
            call = _field(part, "function_call")
            if call is not None:
                name = _field(call, "name")
                arguments = _field(call, "args")
                if not isinstance(name, str) or not name or not isinstance(arguments, Mapping):
                    raise ValueError("invalid Gemini function call")
                function_calls.append((name, arguments))
        return text_parts, function_calls

    @staticmethod
    def _usage(response: object) -> ProviderUsage | None:
        usage = _field(response, "usage_metadata")
        if usage is None:
            return None
        try:
            return ProviderUsage(
                input_tokens=int(_field(usage, "prompt_token_count", 0) or 0),
                output_tokens=int(_field(usage, "candidates_token_count", 0) or 0),
                total_tokens=int(_field(usage, "total_token_count", 0) or 0),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _tool_config(definitions: tuple[ToolDefinition, ...]) -> list[dict[str, object]]:
        if not definitions:
            return []
        return [
            {
                "function_declarations": [
                    {
                        "name": definition.name,
                        "description": definition.description,
                        "parameters_json_schema": _plain_json(definition.input_schema),
                    }
                    for definition in definitions
                ]
            }
        ]

    def _config(self, request: ProviderRequest) -> dict[str, object]:
        system_parts = [
            message.content for message in request.messages if message.role == "system"
        ]
        if request.system_instruction:
            system_parts.insert(0, request.system_instruction)
        config: dict[str, object] = {"temperature": request.temperature}
        if system_parts:
            config["system_instruction"] = "\n\n".join(system_parts)
        if request.max_tokens is not None:
            config["max_output_tokens"] = request.max_tokens
        if request.tools:
            config["tools"] = self._tool_config(request.tools)
        if self.thinking_budget != 0:
            config["thinking_config"] = {
                "thinking_budget": self.thinking_budget,
                "include_thoughts": True,
            }
        return config

    @staticmethod
    def _conversation(request: ProviderRequest) -> tuple[list[dict[str, object]], str]:
        messages = [message for message in request.messages if message.role != "system"]
        if not messages:
            raise ValueError("Gemini request has no sendable message")
        history = [
            {
                "role": "model" if message.role == "assistant" else "user",
                "parts": [{"text": message.content}],
            }
            for message in messages[:-1]
        ]
        return history, messages[-1].content

    def _chat(self, request: ProviderRequest) -> tuple[object, str]:
        history, message = self._conversation(request)
        chat = self._aio.chats.create(
            model=self.model_name,
            config=self._config(request),
            history=history,
        )
        return chat, message

    async def _execute_tools(
        self,
        calls: list[tuple[str, object]],
        request: ProviderRequest,
        *,
        tool_turn: int,
    ) -> list[dict[str, object]]:
        if not calls or self._tool_executor is None:
            raise self._failure(ProviderErrorCode.UNAVAILABLE, request)
        responses: list[dict[str, object]] = []
        for name, arguments in calls:
            result = await self._tool_executor.execute(
                name,
                arguments,  # type: ignore[arg-type]
                tool_turn=tool_turn,
                correlation_id=request.correlation_id,
            )
            responses.append(
                {
                    "function_response": {
                        "name": name,
                        "response": {"result": _plain_json(result.value)},
                    }
                }
            )
        return responses

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        """Return one normalized answer or raise a typed content-free failure."""
        try:
            chat, message = self._chat(request)
            for tool_turn in range(1, self._max_tool_turns + 1):
                response = await chat.send_message(message)
                candidate = self._candidate(response)
                self._validate_finish(candidate, request)
                text_parts, calls = self._extract_parts(candidate)
                if calls:
                    if tool_turn >= self._max_tool_turns:
                        raise self._failure(ProviderErrorCode.RESOURCE_LIMIT, request)
                    message = await self._execute_tools(
                        calls,
                        request,
                        tool_turn=tool_turn,
                    )
                    continue
                content = "".join(text_parts)
                if not content.strip():
                    raise ValueError("empty Gemini answer")
                return ProviderResult(content=content, usage=self._usage(response))
            raise self._failure(ProviderErrorCode.RESOURCE_LIMIT, request)
        except asyncio.CancelledError:
            raise
        except ProviderFailure:
            raise
        except Exception as error:
            raise self._map_error(error, request) from error

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        """Yield real Gemini deltas and exactly one validated completion."""
        emitted_count = 0
        content_parts: list[str] = []
        usage: ProviderUsage | None = None
        try:
            chat, message = self._chat(request)
            for tool_turn in range(1, self._max_tool_turns + 1):
                upstream: object | None = None
                calls: list[tuple[str, object]] = []
                finish_reason_seen = False
                try:
                    upstream = await chat.send_message_stream(message)
                    async for chunk in upstream:  # type: ignore[attr-defined]
                        candidate = self._candidate(chunk)
                        reason = self._finish_reason(candidate)
                        if reason is not None:
                            finish_reason_seen = True
                            self._validate_finish(
                                candidate,
                                request,
                                partial_event_count=emitted_count,
                            )
                        chunk_text, chunk_calls = self._extract_parts(candidate)
                        current_usage = self._usage(chunk)
                        if current_usage is not None:
                            usage = current_usage
                        for text in chunk_text:
                            content_parts.append(text)
                            emitted_count += 1
                            yield TextDelta(text)
                        for name, arguments in chunk_calls:
                            calls.append((name, arguments))
                            encoded = json.dumps(
                                _plain_json(arguments),
                                allow_nan=False,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )
                            emitted_count += 1
                            yield ToolCallDelta(
                                index=len(calls) - 1,
                                name=name,
                                arguments_fragment=encoded,
                            )
                finally:
                    if upstream is not None:
                        await _close_resource(upstream)

                if not finish_reason_seen:
                    raise self._failure(
                        ProviderErrorCode.STREAM_INTERRUPTED,
                        request,
                        retryable=True,
                        partial_event_count=emitted_count,
                    )
                if calls:
                    if tool_turn >= self._max_tool_turns:
                        raise self._failure(
                            ProviderErrorCode.RESOURCE_LIMIT,
                            request,
                            partial_event_count=emitted_count,
                        )
                    message = await self._execute_tools(
                        calls,
                        request,
                        tool_turn=tool_turn,
                    )
                    continue
                content = "".join(content_parts)
                if not content.strip():
                    raise self._failure(
                        ProviderErrorCode.MALFORMED_RESPONSE,
                        request,
                        partial_event_count=emitted_count,
                    )
                yield Completed(ProviderResult(content=content, usage=usage))
                return
            raise self._failure(
                ProviderErrorCode.RESOURCE_LIMIT,
                request,
                partial_event_count=emitted_count,
            )
        except asyncio.CancelledError:
            raise
        except ProviderFailure:
            raise
        except Exception as error:
            raise self._map_error(
                error,
                request,
                partial_event_count=emitted_count,
            ) from error

    async def health(self) -> ProviderHealth:
        """Return an explicit unknown state without making a billable request."""
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            status=ProviderHealthStatus.UNKNOWN,
        )

    async def clear_session(self, session_id: str) -> None:
        """No-op because the adapter retains no provider conversation state."""
        del session_id

    async def aclose(self) -> None:
        """Close the asynchronous SDK client exactly once."""
        if self._closed:
            return
        self._closed = True
        await _close_resource(self._aio)

    async def generate_response(
        self,
        messages: list[Message],
        system_instruction: str | None = None,
        tools: object | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        session_id: str | None = None,
    ) -> ProviderResponse:
        """Temporary legacy route adapter; typed failures still propagate."""
        definitions = tools if isinstance(tools, tuple) else ()
        request = ProviderRequest(
            messages=tuple(
                ProviderMessage(role=message.role, content=message.content)
                for message in messages
            ),
            system_instruction=system_instruction,
            tools=definitions,
            temperature=temperature,
            max_tokens=max_tokens,
            session_id=session_id,
        )
        result = await self.generate(request)
        return ProviderResponse(
            content=result.content,
            thoughts=result.reflection_summary,
        )

    async def stream_response(
        self,
        messages: list[Message],
        system_instruction: str | None = None,
        tools: object | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[ProviderResponse]:
        """Temporary legacy adapter over the real incremental stream."""
        definitions = tools if isinstance(tools, tuple) else ()
        request = ProviderRequest(
            messages=tuple(
                ProviderMessage(role=message.role, content=message.content)
                for message in messages
            ),
            system_instruction=system_instruction,
            tools=definitions,
            temperature=temperature,
            max_tokens=max_tokens,
            session_id=session_id,
        )
        async for event in self.stream(request):
            if isinstance(event, TextDelta):
                yield ProviderResponse(content=event.text)

    async def convert_mcp_tools(self, mcp_tools: list[dict[str, Any]]) -> object:
        """Convert legacy schemas without retaining an SDK-specific catalog."""
        definitions = tuple(
            ToolDefinition(
                name=str(tool["name"]),
                description=str(tool.get("description", "")),
                input_schema=tool.get(
                    "inputSchema", {"type": "object", "properties": {}}
                ),  # type: ignore[arg-type]
            )
            for tool in mcp_tools
            if tool.get("name")
        )
        return self._tool_config(definitions)
