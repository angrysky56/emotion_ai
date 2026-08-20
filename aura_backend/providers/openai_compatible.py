"""Shared, fail-closed OpenAI-compatible provider transport.

Ollama and OpenRouter supply endpoint policy only.  This module owns SDK client
construction, request translation, bounded tool turns, streaming, error mapping,
and resource cleanup without exposing SDK objects or source exception text.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

from .base import (
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
from .config import ProviderSettings
from .errors import ProviderErrorCode, ProviderFailure
from .tools import ToolExecutor


ClientFactory = Callable[..., Any]


def _field(value: object, name: str, default: Any = None) -> Any:
    """Read one SDK-like field from a mapping or attribute object."""
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _plain_json(value: object) -> object:
    """Convert immutable JSON-like tool results into SDK-safe containers."""
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


async def _close_resource(resource: object) -> None:
    """Close an SDK stream/client through its supported local close method."""
    close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
    if close is None:
        return
    outcome = close()
    if inspect.isawaitable(outcome):
        await outcome


class OpenAICompatibleProvider:
    """Provider-neutral implementation shared by compatible HTTP services."""

    def __init__(
        self,
        *,
        settings: ProviderSettings,
        provider_name: str,
        api_key: str,
        default_headers: Mapping[str, str] | None = None,
        client: object | None = None,
        client_factory: ClientFactory = AsyncOpenAI,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        if settings.base_url is None:
            raise ProviderFailure(
                code=ProviderErrorCode.CONFIGURATION,
                provider=provider_name,
                setting_name="BASE_URL",
            )
        if settings.max_retries != 0:
            raise ProviderFailure(
                code=ProviderErrorCode.CONFIGURATION,
                provider=provider_name,
                setting_name="AURA_PROVIDER_MAX_RETRIES",
            )
        self.provider_name = provider_name
        self.model_name = settings.model
        self._settings = settings
        self._tool_executor = tool_executor
        self._closed = False
        if client is None:
            timeout = httpx.Timeout(
                connect=settings.connect_timeout_seconds,
                read=settings.read_timeout_seconds,
                write=settings.write_timeout_seconds,
                pool=settings.pool_timeout_seconds,
            )
            kwargs: dict[str, object] = {
                "api_key": api_key,
                "base_url": settings.base_url,
                "max_retries": 0,
                "timeout": timeout,
            }
            if default_headers:
                kwargs["default_headers"] = dict(default_headers)
            client = client_factory(**kwargs)
        self._client = client

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
        if isinstance(error, AuthenticationError):
            code, retryable = ProviderErrorCode.AUTHENTICATION, False
        elif isinstance(error, NotFoundError):
            code, retryable = ProviderErrorCode.MODEL_NOT_FOUND, False
        elif isinstance(error, RateLimitError):
            code, retryable = ProviderErrorCode.RATE_LIMITED, True
        elif isinstance(error, (APITimeoutError, TimeoutError, httpx.TimeoutException)):
            code, retryable = ProviderErrorCode.TIMEOUT, True
        elif isinstance(error, (APIConnectionError, httpx.NetworkError)):
            code, retryable = ProviderErrorCode.UNAVAILABLE, True
        elif isinstance(error, APIStatusError):
            status = getattr(error, "status_code", 0)
            if status in {401, 403}:
                code, retryable = ProviderErrorCode.AUTHENTICATION, False
            elif status == 404:
                code, retryable = ProviderErrorCode.MODEL_NOT_FOUND, False
            elif status == 429:
                code, retryable = ProviderErrorCode.RATE_LIMITED, True
            elif status >= 500:
                code, retryable = ProviderErrorCode.UNAVAILABLE, True
            else:
                code, retryable = ProviderErrorCode.MALFORMED_RESPONSE, False
        else:
            code, retryable = ProviderErrorCode.MALFORMED_RESPONSE, False
        return self._failure(code, request, retryable=retryable)

    @staticmethod
    def _messages(request: ProviderRequest) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.extend(
            {"role": message.role, "content": message.content}
            for message in request.messages
        )
        return messages

    @staticmethod
    def _tools(definitions: tuple[ToolDefinition, ...]) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": _plain_json(definition.input_schema),
                },
            }
            for definition in definitions
        ]

    def _request_kwargs(
        self,
        request: ProviderRequest,
        messages: list[dict[str, object]],
        *,
        stream: bool,
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.tools:
            kwargs["tools"] = self._tools(request.tools)
        return kwargs

    @staticmethod
    def _usage(response: object) -> ProviderUsage | None:
        usage = _field(response, "usage")
        if usage is None:
            return None
        try:
            return ProviderUsage(
                input_tokens=int(_field(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(_field(usage, "completion_tokens", 0) or 0),
                total_tokens=int(_field(usage, "total_tokens", 0) or 0),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _choices(response: object) -> list[object]:
        choices = _field(response, "choices")
        if not isinstance(choices, (list, tuple)) or not choices:
            raise ValueError("invalid provider choices")
        return list(choices)

    @staticmethod
    def _error_status(value: object) -> int | None:
        error = _field(value, "error")
        if error is None:
            return None
        code = _field(error, "code")
        if isinstance(code, int) and not isinstance(code, bool):
            return code
        return 500

    def _envelope_failure(
        self,
        value: object,
        request: ProviderRequest,
        *,
        partial_event_count: int = 0,
    ) -> ProviderFailure | None:
        status = self._error_status(value)
        if status is None:
            return None
        if partial_event_count:
            code, retryable = ProviderErrorCode.STREAM_INTERRUPTED, True
        elif status in {401, 403}:
            code, retryable = ProviderErrorCode.AUTHENTICATION, False
        elif status == 404:
            code, retryable = ProviderErrorCode.MODEL_NOT_FOUND, False
        elif status == 429:
            code, retryable = ProviderErrorCode.RATE_LIMITED, True
        elif status >= 500:
            code, retryable = ProviderErrorCode.UNAVAILABLE, True
        else:
            code, retryable = ProviderErrorCode.MALFORMED_RESPONSE, False
        return self._failure(
            code,
            request,
            retryable=retryable,
            partial_event_count=partial_event_count,
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[tuple[str, str, str]],
        messages: list[dict[str, object]],
        request: ProviderRequest,
        *,
        tool_turn: int,
    ) -> None:
        if not tool_calls or self._tool_executor is None:
            raise self._failure(ProviderErrorCode.UNAVAILABLE, request)
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": arguments},
                    }
                    for call_id, name, arguments in tool_calls
                ],
            }
        )
        for call_id, name, arguments in tool_calls:
            result = await self._tool_executor.execute(
                name,
                arguments,
                tool_turn=tool_turn,
                correlation_id=request.correlation_id,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(
                        _plain_json(result.value),
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                }
            )

    def _nonstream_tool_calls(
        self,
        message: object,
        request: ProviderRequest,
    ) -> list[tuple[str, str, str]]:
        raw_calls = _field(message, "tool_calls", [])
        if not raw_calls:
            return []
        parsed: list[tuple[str, str, str]] = []
        try:
            for call in raw_calls:
                function = _field(call, "function")
                call_id = _field(call, "id")
                name = _field(function, "name")
                arguments = _field(function, "arguments")
                if not all(isinstance(item, str) and item for item in (call_id, name, arguments)):
                    raise ValueError
                json.loads(arguments)
                parsed.append((call_id, name, arguments))
        except (TypeError, ValueError, json.JSONDecodeError):
            raise self._failure(ProviderErrorCode.MALFORMED_RESPONSE, request) from None
        return parsed

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        """Return one normalized result or raise a typed content-free failure."""
        messages = self._messages(request)
        try:
            for tool_turn in range(1, self._settings.max_tool_turns + 1):
                response = await self._client.chat.completions.create(
                    **self._request_kwargs(request, messages, stream=False)
                )
                envelope_failure = self._envelope_failure(response, request)
                if envelope_failure is not None:
                    raise envelope_failure
                choice = self._choices(response)[0]
                message = _field(choice, "message")
                if message is None:
                    raise ValueError("missing message")
                tool_calls = self._nonstream_tool_calls(message, request)
                if tool_calls:
                    await self._execute_tool_calls(
                        tool_calls,
                        messages,
                        request,
                        tool_turn=tool_turn,
                    )
                    continue
                content = _field(message, "content")
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("empty provider content")
                return ProviderResult(content=content, usage=self._usage(response))
            raise self._failure(ProviderErrorCode.RESOURCE_LIMIT, request)
        except asyncio.CancelledError:
            raise
        except ProviderFailure:
            raise
        except Exception as error:
            raise self._map_error(error, request) from error

    @staticmethod
    def _stream_tool_fragments(choice: object) -> list[object]:
        delta = _field(choice, "delta")
        raw_calls = _field(delta, "tool_calls", [])
        return list(raw_calls) if isinstance(raw_calls, (list, tuple)) else []

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        """Yield true upstream deltas and exactly one validated completion."""
        messages = self._messages(request)
        emitted_count = 0
        try:
            for tool_turn in range(1, self._settings.max_tool_turns + 1):
                upstream: object | None = None
                text_parts: list[str] = []
                tool_parts: dict[int, dict[str, str]] = {}
                finish_reason: str | None = None
                try:
                    upstream = await self._client.chat.completions.create(
                        **self._request_kwargs(request, messages, stream=True)
                    )
                    async for chunk in upstream:
                        envelope_failure = self._envelope_failure(
                            chunk,
                            request,
                            partial_event_count=emitted_count,
                        )
                        if envelope_failure is not None:
                            raise envelope_failure
                        choice = self._choices(chunk)[0]
                        delta = _field(choice, "delta")
                        content = _field(delta, "content")
                        if content is not None:
                            if not isinstance(content, str):
                                raise ValueError("invalid stream content")
                            if content:
                                text_parts.append(content)
                                emitted_count += 1
                                yield TextDelta(content)
                        for raw_call in self._stream_tool_fragments(choice):
                            index = _field(raw_call, "index")
                            if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                                raise ValueError("invalid tool-call index")
                            function = _field(raw_call, "function")
                            call_id = _field(raw_call, "id")
                            name = _field(function, "name") if function is not None else None
                            arguments = (
                                _field(function, "arguments") if function is not None else None
                            )
                            if not any(item is not None for item in (call_id, name, arguments)):
                                raise ValueError("empty tool-call fragment")
                            bucket = tool_parts.setdefault(
                                index,
                                {"id": "", "name": "", "arguments": ""},
                            )
                            if call_id is not None:
                                if not isinstance(call_id, str):
                                    raise ValueError("invalid tool call id")
                                bucket["id"] += call_id
                            if name is not None:
                                if not isinstance(name, str):
                                    raise ValueError("invalid tool call name")
                                bucket["name"] += name
                            if arguments is not None:
                                if not isinstance(arguments, str):
                                    raise ValueError("invalid tool arguments")
                                bucket["arguments"] += arguments
                            emitted_count += 1
                            yield ToolCallDelta(
                                index=index,
                                call_id=call_id,
                                name=name,
                                arguments_fragment=arguments,
                            )
                        chunk_finish = _field(choice, "finish_reason")
                        if chunk_finish is not None:
                            if not isinstance(chunk_finish, str):
                                raise ValueError("invalid finish reason")
                            finish_reason = chunk_finish
                finally:
                    if upstream is not None:
                        await _close_resource(upstream)

                if finish_reason == "tool_calls":
                    assembled = [
                        (parts["id"], parts["name"], parts["arguments"])
                        for _index, parts in sorted(tool_parts.items())
                    ]
                    try:
                        for call_id, name, arguments in assembled:
                            if not call_id or not name or not arguments:
                                raise ValueError
                            json.loads(arguments)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        raise self._failure(
                            ProviderErrorCode.MALFORMED_RESPONSE,
                            request,
                            partial_event_count=emitted_count,
                        ) from None
                    await self._execute_tool_calls(
                        assembled,
                        messages,
                        request,
                        tool_turn=tool_turn,
                    )
                    continue
                if finish_reason in {"length", "content_filter"}:
                    raise self._failure(
                        ProviderErrorCode.RESOURCE_LIMIT,
                        request,
                        partial_event_count=emitted_count,
                    )
                if finish_reason != "stop" or tool_parts:
                    raise self._failure(
                        ProviderErrorCode.MALFORMED_RESPONSE,
                        request,
                        partial_event_count=emitted_count,
                    )
                content = "".join(text_parts)
                if not content.strip():
                    raise self._failure(
                        ProviderErrorCode.MALFORMED_RESPONSE,
                        request,
                        partial_event_count=emitted_count,
                    )
                yield Completed(ProviderResult(content=content))
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
        """Return an explicit unknown state; concrete adapters own readiness."""
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            status=ProviderHealthStatus.UNKNOWN,
        )

    async def clear_session(self, session_id: str) -> None:
        """Compatible providers retain no hidden conversation history."""
        del session_id

    async def aclose(self) -> None:
        """Close the shared SDK client exactly once."""
        if self._closed:
            return
        self._closed = True
        await _close_resource(self._client)

    async def generate_response(
        self,
        messages: list[Message],
        system_instruction: str | None = None,
        tools: object | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        session_id: str | None = None,
    ) -> ProviderResponse:
        """Temporary legacy route adapter; typed failures continue to propagate."""
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
        return ProviderResponse(content=result.content, thoughts=result.reflection_summary)

    async def stream_response(
        self,
        messages: list[Message],
        system_instruction: str | None = None,
        tools: object | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[ProviderResponse]:
        """Temporary legacy streaming adapter over real incremental deltas."""
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

    async def convert_mcp_tools(self, mcp_tools: list[dict[str, object]]) -> object:
        """Translate legacy schemas without retaining a second routing catalog."""
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
        return self._tools(definitions)
