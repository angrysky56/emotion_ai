"""Offline contract tests for Aura's shared OpenAI-compatible transport."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
)

from aura_backend.providers.base import (
    Completed,
    ProviderMessage,
    ProviderRequest,
    TextDelta,
    ToolDefinition,
)
from aura_backend.providers.config import ProviderSettings
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.tools import (
    ToolCatalog,
    ToolExecutor,
    ToolRegistration,
    ToolSource,
)


def _settings(**overrides: str) -> ProviderSettings:
    values = {"OLLAMA_MODEL": "synthetic-model", **overrides}
    return ProviderSettings.from_mapping(values)


def _request(*, tools: tuple[ToolDefinition, ...] = ()) -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content="private prompt SENTINEL"),),
        system_instruction="private system SENTINEL",
        tools=tools,
        temperature=0.25,
        max_tokens=19,
        correlation_id="corr-04",
    )


def _message(
    content: str | None,
    *,
    tool_calls: list[Any] | None = None,
) -> Any:
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def _response(
    content: str | None,
    *,
    tool_calls: list[Any] | None = None,
    finish_reason: str = "stop",
) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=_message(content, tool_calls=tool_calls),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5),
    )


def _chunk(
    content: str | None = None,
    *,
    finish_reason: str | None = None,
    tool_calls: list[Any] | None = None,
    error: Any = None,
) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=content, tool_calls=tool_calls or []),
                finish_reason=finish_reason,
            )
        ],
        error=error,
    )


class FakeStream:
    def __init__(self, chunks: list[Any], failure: Exception | None = None) -> None:
        self._chunks = chunks
        self._failure = failure
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[Any]:
        for chunk in self._chunks:
            yield chunk
        if self._failure is not None:
            raise self._failure

    async def aclose(self) -> None:
        self.closed = True


class FakeCompletions:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.completions = FakeCompletions(outcomes)
        self.chat = SimpleNamespace(completions=self.completions)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _provider(client: FakeClient, *, executor: ToolExecutor | None = None) -> Any:
    from aura_backend.providers.openai_compatible import OpenAICompatibleProvider

    return OpenAICompatibleProvider(
        settings=_settings(),
        provider_name="ollama",
        api_key="ollama",
        client=client,
        tool_executor=executor,
    )


def test_client_construction_uses_exact_timeouts_and_zero_retries() -> None:
    from aura_backend.providers.openai_compatible import OpenAICompatibleProvider

    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeClient:
        captured.update(kwargs)
        return FakeClient([_response("done")])

    provider = OpenAICompatibleProvider(
        settings=_settings(
            AURA_PROVIDER_CONNECT_TIMEOUT_SECONDS="1",
            AURA_PROVIDER_READ_TIMEOUT_SECONDS="2",
            AURA_PROVIDER_WRITE_TIMEOUT_SECONDS="3",
            AURA_PROVIDER_POOL_TIMEOUT_SECONDS="4",
        ),
        provider_name="ollama",
        api_key="ollama",
        client_factory=factory,
    )

    timeout = captured["timeout"]
    assert captured["max_retries"] == 0
    assert captured["base_url"] == "http://127.0.0.1:11434/v1"
    assert isinstance(timeout, httpx.Timeout)
    assert (timeout.connect, timeout.read, timeout.write, timeout.pool) == (1.0, 2.0, 3.0, 4.0)
    assert "private" not in repr(provider)


@pytest.mark.asyncio
async def test_generate_normalizes_messages_tools_usage_and_sdk_objects() -> None:
    tool = ToolDefinition(
        name="memory_search",
        description="Synthetic lookup",
        input_schema={"type": "object", "properties": {}},
    )
    client = FakeClient([_response("safe answer")])
    provider = _provider(client)

    result = await provider.generate(_request(tools=(tool,)))

    assert result.content == "safe answer"
    assert result.usage is not None and result.usage.total_tokens == 5
    assert not hasattr(result, "raw_response")
    call = client.completions.calls[0]
    assert call["messages"] == [
        {"role": "system", "content": "private system SENTINEL"},
        {"role": "user", "content": "private prompt SENTINEL"},
    ]
    assert call["tools"][0]["function"]["name"] == "memory_search"
    assert call["temperature"] == 0.25
    assert call["max_tokens"] == 19
    assert call["stream"] is False


@pytest.mark.parametrize(
    ("error_factory", "expected"),
    (
        (lambda r: AuthenticationError("credential SENTINEL", response=httpx.Response(401, request=r), body=None), ProviderErrorCode.AUTHENTICATION),
        (lambda r: NotFoundError("model SENTINEL", response=httpx.Response(404, request=r), body=None), ProviderErrorCode.MODEL_NOT_FOUND),
        (lambda r: RateLimitError("rate SENTINEL", response=httpx.Response(429, request=r), body=None), ProviderErrorCode.RATE_LIMITED),
        (lambda r: APITimeoutError(r), ProviderErrorCode.TIMEOUT),
        (lambda r: APIConnectionError(request=r), ProviderErrorCode.UNAVAILABLE),
        (lambda r: InternalServerError("server SENTINEL", response=httpx.Response(503, request=r), body=None), ProviderErrorCode.UNAVAILABLE),
    ),
)
@pytest.mark.asyncio
async def test_sdk_failures_map_to_exact_safe_codes(error_factory: Any, expected: ProviderErrorCode) -> None:
    request = httpx.Request("POST", "https://credential-SENTINEL.invalid/private")
    provider = _provider(FakeClient([error_factory(request)]))

    with pytest.raises(ProviderFailure) as captured:
        await provider.generate(_request())

    assert captured.value.code is expected
    rendered = f"{captured.value!s} {captured.value!r} {captured.value.to_public_dict()!r}"
    assert "SENTINEL" not in rendered
    assert "private prompt" not in rendered


@pytest.mark.parametrize("bad_response", (SimpleNamespace(choices=[]), _response(None)))
@pytest.mark.asyncio
async def test_empty_choices_or_content_are_malformed(bad_response: Any) -> None:
    provider = _provider(FakeClient([bad_response]))
    with pytest.raises(ProviderFailure) as captured:
        await provider.generate(_request())
    assert captured.value.code is ProviderErrorCode.MALFORMED_RESPONSE


@pytest.mark.asyncio
async def test_tool_arguments_assemble_validate_and_execute_once() -> None:
    definition = ToolDefinition(
        name="memory.search",
        description="Synthetic lookup",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    route = ToolRegistration(definition=definition, source=ToolSource.INTERNAL, server="aura-internal")
    calls: list[dict[str, Any]] = []

    async def dispatch(_route: ToolRegistration, arguments: Any) -> object:
        calls.append(dict(arguments))
        return {"found": True}

    executor = ToolExecutor(ToolCatalog((route,)), dispatch)
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name=route.provider_name, arguments='{"query":"safe"}'),
    )
    client = FakeClient([_response(None, tool_calls=[tool_call], finish_reason="tool_calls"), _response("done")])
    provider = _provider(client, executor=executor)

    result = await provider.generate(_request(tools=(route.provider_definition,)))

    assert result.content == "done"
    assert calls == [{"query": "safe"}]
    assert len(client.completions.calls) == 2
    assert client.completions.calls[1]["messages"][-1]["role"] == "tool"


@pytest.mark.asyncio
async def test_malformed_tool_json_and_turn_exhaustion_are_not_answers() -> None:
    definition = ToolDefinition(name="lookup", description="Synthetic", input_schema={"type": "object", "properties": {}})
    route = ToolRegistration(definition=definition, source=ToolSource.INTERNAL, server="aura-internal")

    async def dispatch(_route: ToolRegistration, _arguments: Any) -> object:
        return {}

    malformed = SimpleNamespace(id="call-1", function=SimpleNamespace(name="lookup", arguments="{"))
    provider = _provider(FakeClient([_response(None, tool_calls=[malformed], finish_reason="tool_calls")]), executor=ToolExecutor(ToolCatalog((route,)), dispatch))
    with pytest.raises(ProviderFailure) as captured:
        await provider.generate(_request(tools=(definition,)))
    assert captured.value.code is ProviderErrorCode.MALFORMED_RESPONSE

    valid = SimpleNamespace(id="call-2", function=SimpleNamespace(name="lookup", arguments="{}"))
    exhausting = _provider(FakeClient([_response(None, tool_calls=[valid], finish_reason="tool_calls")] * 3), executor=ToolExecutor(ToolCatalog((route,)), dispatch))
    with pytest.raises(ProviderFailure) as exhausted:
        await exhausting.generate(_request(tools=(definition,)))
    assert exhausted.value.code is ProviderErrorCode.RESOURCE_LIMIT


@pytest.mark.asyncio
async def test_stream_yields_upstream_deltas_then_one_completion_and_closes() -> None:
    upstream = FakeStream([_chunk("first"), _chunk(" second"), _chunk(finish_reason="stop")])
    client = FakeClient([upstream])
    provider = _provider(client)

    events = [event async for event in provider.stream(_request())]

    assert events[:2] == [TextDelta("first"), TextDelta(" second")]
    assert len([event for event in events if isinstance(event, Completed)]) == 1
    assert events[-1].result.content == "first second"
    assert upstream.closed


@pytest.mark.asyncio
async def test_midstream_failure_closes_without_completion_or_content_in_diagnostics() -> None:
    upstream = FakeStream([_chunk("private partial SENTINEL")], RuntimeError("raw response SENTINEL"))
    provider = _provider(FakeClient([upstream]))
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as captured:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert observed == [TextDelta("private partial SENTINEL")]
    assert captured.value.code is ProviderErrorCode.STREAM_INTERRUPTED
    assert captured.value.partial_event_count == 1
    assert "SENTINEL" not in f"{captured.value!s} {captured.value!r}"
    assert upstream.closed


@pytest.mark.asyncio
async def test_stream_cancellation_closes_upstream_and_provider_close_is_idempotent() -> None:
    entered = asyncio.Event()

    class BlockingStream(FakeStream):
        async def __aiter__(self) -> AsyncIterator[Any]:
            entered.set()
            await asyncio.Event().wait()
            yield _chunk("never")

    upstream = BlockingStream([])
    client = FakeClient([upstream])
    provider = _provider(client)
    stream = provider.stream(_request())
    pending = asyncio.create_task(anext(stream))
    await entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    assert upstream.closed
    await provider.aclose()
    await provider.aclose()
    assert client.closed


@pytest.mark.asyncio
async def test_process_control_base_exceptions_are_never_normalized() -> None:
    class ProcessControl(BaseException):
        pass

    provider = _provider(FakeClient([ProcessControl()]))
    with pytest.raises(ProcessControl):
        await provider.generate(_request())
