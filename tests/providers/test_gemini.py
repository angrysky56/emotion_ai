"""Offline contract tests for Aura's optional Gemini adapter.

The fakes in this module deliberately expose sync tripwires.  Any accidental use
of ``client.models``, ``client.chats``, or a synchronous chat send fails without
contacting Google or another network service.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from aura_backend.providers.base import (
    Completed,
    ProviderMessage,
    ProviderRequest,
    TextDelta,
    ToolCallDelta,
    ToolDefinition,
)
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.tools import (
    ToolCatalog,
    ToolExecutor,
    ToolRegistration,
    ToolSource,
)


API_KEY = "credential-SENTINEL-gemini"


def _part(
    text: str | None = None,
    *,
    thought: bool = False,
    function_call: object | None = None,
) -> object:
    return SimpleNamespace(text=text, thought=thought, function_call=function_call)


def _response(
    *parts: object,
    finish_reason: str = "STOP",
    usage: tuple[int, int, int] = (2, 3, 5),
) -> object:
    prompt, candidates, total = usage
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=list(parts)),
                finish_reason=finish_reason,
            )
        ],
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt,
            candidates_token_count=candidates,
            total_token_count=total,
        ),
    )


class FakeGeminiError(Exception):
    """SDK-like exception carrying only an HTTP-style status for mapping tests."""

    def __init__(self, code: int, detail: str = "exception-SENTINEL") -> None:
        super().__init__(detail)
        self.code = code


class FakeAsyncStream:
    def __init__(
        self,
        chunks: list[object],
        *,
        failure: BaseException | None = None,
        block_after_first: asyncio.Event | None = None,
    ) -> None:
        self._chunks = chunks
        self._failure = failure
        self._block_after_first = block_after_first
        self.first_emitted = asyncio.Event()
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[object]:
        for index, chunk in enumerate(self._chunks):
            yield chunk
            if index == 0:
                self.first_emitted.set()
                if self._block_after_first is not None:
                    await self._block_after_first.wait()
        if self._failure is not None:
            raise self._failure

    async def aclose(self) -> None:
        self.closed = True


class FakeAsyncChat:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.send_calls: list[object] = []
        self.stream_calls: list[object] = []

    def send_message(self, _message: object) -> object:
        raise AssertionError("synchronous Gemini send_message was called")

    async def async_send(self, message: object) -> object:
        self.send_calls.append(message)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def async_stream(self, message: object) -> object:
        self.stream_calls.append(message)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeAsyncChats:
    def __init__(self, chats: list[FakeAsyncChat]) -> None:
        self._chats = chats
        self.create_calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeAsyncChat:
        self.create_calls.append(dict(kwargs))
        chat = self._chats.pop(0)
        chat.send_message = chat.async_send  # type: ignore[method-assign]
        chat.send_message_stream = chat.async_stream  # type: ignore[attr-defined]
        return chat


class FakeAsyncClient:
    def __init__(self, chats: list[FakeAsyncChat]) -> None:
        self.chats = FakeAsyncChats(chats)
        self.close_calls = 0

    async def aclose(self) -> None:
        self.close_calls += 1


class FakeClient:
    def __init__(self, chats: list[FakeAsyncChat]) -> None:
        self.aio = FakeAsyncClient(chats)

    @property
    def chats(self) -> object:
        raise AssertionError("synchronous client.chats was touched")

    @property
    def models(self) -> object:
        raise AssertionError("synchronous client.models was touched")

    def close(self) -> None:
        raise AssertionError("synchronous client.close was called")


def _request(
    text: str = "prompt-SENTINEL",
    *,
    tools: tuple[ToolDefinition, ...] = (),
) -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content=text),),
        system_instruction="system-SENTINEL",
        tools=tools,
        temperature=0.25,
        max_tokens=31,
        session_id="session-SENTINEL",
        correlation_id="gemini-test",
    )


def _provider(client: FakeClient, **kwargs: object) -> object:
    from aura_backend.providers.gemini import GeminiProvider

    return GeminiProvider(api_key=API_KEY, client=client, **kwargs)


def test_adapter_validates_credential_before_lazy_client_construction() -> None:
    from aura_backend.providers.gemini import GeminiProvider

    constructed = False

    def forbidden_factory(**_kwargs: object) -> object:
        nonlocal constructed
        constructed = True
        raise AssertionError("client must not be constructed")

    with pytest.raises(ProviderFailure) as captured:
        GeminiProvider(api_key="", client_factory=forbidden_factory)

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.setting_name == "GEMINI_API_KEY"
    assert constructed is False
    module = __import__("aura_backend.providers.gemini", fromlist=["*"])
    assert "genai" not in vars(module)
    assert "types" not in vars(module)
    assert "genai.Client(" not in inspect.getsource(GeminiProvider)


@pytest.mark.asyncio
async def test_adapter_generation_is_async_stateless_and_normalized() -> None:
    first = FakeAsyncChat([_response(_part("safe answer"), _part("hidden-SENTINEL", thought=True))])
    second = FakeAsyncChat([_response(_part("second answer"))])
    client = FakeClient([first, second])
    provider = _provider(client)

    result = await provider.generate(_request())
    second_result = await provider.generate(_request("another private prompt"))

    assert result.content == "safe answer"
    assert result.reflection_summary is None
    assert result.usage is not None and result.usage.total_tokens == 5
    assert second_result.content == "second answer"
    assert len(client.aio.chats.create_calls) == 2
    assert client.aio.chats.create_calls[0]["history"] == []
    assert first.send_calls == ["prompt-SENTINEL"]
    assert second.send_calls == ["another private prompt"]
    assert not hasattr(provider, "_chat_sessions")
    assert not hasattr(result, "raw_response")


@pytest.mark.asyncio
async def test_adapter_tool_follow_up_uses_async_chat_and_neutral_executor() -> None:
    definition = ToolDefinition(
        name="memory_search",
        description="Synthetic lookup",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    registration = ToolRegistration(
        definition=definition,
        source=ToolSource.INTERNAL,
        server="aura-internal",
    )
    dispatched: list[dict[str, object]] = []

    async def dispatch(_route: ToolRegistration, arguments: Any) -> object:
        dispatched.append(dict(arguments))
        return {"found": True}

    call = SimpleNamespace(name="memory_search", args={"query": "safe"})
    chat = FakeAsyncChat(
        [
            _response(_part(function_call=call)),
            _response(_part("tool-complete")),
        ]
    )
    provider = _provider(
        FakeClient([chat]),
        tool_executor=ToolExecutor(ToolCatalog((registration,)), dispatch),
    )

    result = await provider.generate(_request(tools=(registration.provider_definition,)))

    assert result.content == "tool-complete"
    assert dispatched == [{"query": "safe"}]
    assert len(chat.send_calls) == 2
    follow_up = chat.send_calls[1]
    assert isinstance(follow_up, list)
    assert follow_up[0]["function_response"]["name"] == "memory_search"


@pytest.mark.parametrize(
    ("outcome", "expected"),
    (
        (FakeGeminiError(401), ProviderErrorCode.AUTHENTICATION),
        (FakeGeminiError(429), ProviderErrorCode.RATE_LIMITED),
        (FakeGeminiError(503), ProviderErrorCode.UNAVAILABLE),
        (TimeoutError("exception-SENTINEL"), ProviderErrorCode.TIMEOUT),
        (_response(_part("partial"), finish_reason="MAX_TOKENS"), ProviderErrorCode.RESOURCE_LIMIT),
        (SimpleNamespace(candidates=[]), ProviderErrorCode.MALFORMED_RESPONSE),
    ),
)
@pytest.mark.asyncio
async def test_adapter_failure_mapping_is_typed_and_redacted(
    outcome: object,
    expected: ProviderErrorCode,
) -> None:
    provider = _provider(FakeClient([FakeAsyncChat([outcome])]))

    with pytest.raises(ProviderFailure) as captured:
        await provider.generate(_request())

    assert captured.value.code is expected
    diagnostics = f"{captured.value!s} {captured.value!r} {provider!r}"
    for sentinel in (API_KEY, "prompt-SENTINEL", "system-SENTINEL", "exception-SENTINEL"):
        assert sentinel not in diagnostics


@pytest.mark.asyncio
async def test_stream_is_incremental_and_closes_upstream() -> None:
    release = asyncio.Event()
    upstream = FakeAsyncStream(
        [_response(_part("first"), finish_reason=""), _response(_part("second"))],
        block_after_first=release,
    )
    provider = _provider(FakeClient([FakeAsyncChat([upstream])]))
    stream = provider.stream(_request())

    first = await anext(stream)
    assert first == TextDelta("first")
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    assert not pending.done()
    release.set()
    assert await pending == TextDelta("second")
    terminal = await anext(stream)
    assert terminal == Completed(terminal.result)
    assert terminal.result.content == "firstsecond"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert upstream.closed


@pytest.mark.asyncio
async def test_stream_tool_follow_up_uses_async_chat_and_typed_events() -> None:
    definition = ToolDefinition(
        name="lookup",
        description="Synthetic lookup",
        input_schema={"type": "object", "properties": {}},
    )
    registration = ToolRegistration(
        definition=definition,
        source=ToolSource.INTERNAL,
        server="aura-internal",
    )

    async def dispatch(_route: ToolRegistration, _arguments: Any) -> object:
        return {"ok": True}

    call = SimpleNamespace(name="lookup", args={})
    first_upstream = FakeAsyncStream([_response(_part(function_call=call))])
    second_upstream = FakeAsyncStream([_response(_part("done"))])
    chat = FakeAsyncChat([first_upstream, second_upstream])
    provider = _provider(
        FakeClient([chat]),
        tool_executor=ToolExecutor(ToolCatalog((registration,)), dispatch),
    )

    observed = [event async for event in provider.stream(_request(tools=(definition,)))]

    assert observed[0] == ToolCallDelta(index=0, name="lookup", arguments_fragment="{}")
    assert observed[1] == TextDelta("done")
    assert isinstance(observed[2], Completed)
    assert observed[2].result.content == "done"
    assert first_upstream.closed and second_upstream.closed


@pytest.mark.asyncio
async def test_stream_failure_after_delta_never_completes_and_closes() -> None:
    upstream = FakeAsyncStream(
        [_response(_part("response-SENTINEL partial"), finish_reason="")],
        failure=RuntimeError("exception-SENTINEL"),
    )
    provider = _provider(FakeClient([FakeAsyncChat([upstream])]))
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as captured:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert observed == [TextDelta("response-SENTINEL partial")]
    assert captured.value.code is ProviderErrorCode.STREAM_INTERRUPTED
    assert captured.value.partial_event_count == 1
    assert not any(isinstance(event, Completed) for event in observed)
    assert upstream.closed


@pytest.mark.asyncio
async def test_stream_cancellation_re_raises_and_closes_without_completion() -> None:
    release = asyncio.Event()
    upstream = FakeAsyncStream(
        [_response(_part("first"), finish_reason="")],
        block_after_first=release,
    )
    provider = _provider(FakeClient([FakeAsyncChat([upstream])]))
    stream = provider.stream(_request())
    assert await anext(stream) == TextDelta("first")

    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    assert upstream.closed


@pytest.mark.asyncio
async def test_adapter_close_is_async_and_idempotent() -> None:
    client = FakeClient([FakeAsyncChat([_response(_part("unused"))])])
    provider = _provider(client)

    await provider.aclose()
    await provider.aclose()

    assert client.aio.close_calls == 1


class AwaitableSend:
    """Tripwire that exposes its result only when actually awaited."""

    def __init__(self, outcome: object, owner: "AsyncOnlyThinkingChat") -> None:
        self._outcome = outcome
        self._owner = owner

    def __await__(self):  # type: ignore[no-untyped-def]
        async def resolve() -> object:
            self._owner.await_count += 1
            if isinstance(self._outcome, BaseException):
                raise self._outcome
            return self._outcome

        return resolve().__await__()

    @property
    def candidates(self) -> object:
        raise AssertionError("thinking chat result was inspected before await")


class AsyncOnlyThinkingChat:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = outcomes
        self.messages: list[object] = []
        self.await_count = 0

    def send_message(self, message: object) -> AwaitableSend:
        self.messages.append(message)
        return AwaitableSend(self._outcomes.pop(0), self)


@pytest.mark.asyncio
async def test_thinking_processor_awaits_send_and_never_exposes_raw_thoughts() -> None:
    from aura_backend.thinking_processor import ThinkingProcessor

    chat = AsyncOnlyThinkingChat(
        [_response(_part("hidden-thought-SENTINEL", thought=True), _part("safe answer"))]
    )
    result = await ThinkingProcessor(object()).process_message_with_thinking(
        chat,
        "private message",
        "private-user",
        include_thinking_in_response=True,
    )

    assert chat.await_count == 1
    assert result.answer == "safe answer"
    assert result.thoughts == "Internal reasoning was used."
    assert result.has_thinking is True
    assert "hidden-thought-SENTINEL" not in f"{result!r}"


@pytest.mark.asyncio
async def test_thinking_malformed_response_is_a_typed_failure() -> None:
    from aura_backend.thinking_processor import ThinkingProcessor

    chat = AsyncOnlyThinkingChat([SimpleNamespace(candidates=[])])
    with pytest.raises(ProviderFailure) as captured:
        await ThinkingProcessor(object()).process_message_with_thinking(
            chat,
            "private message",
            "private-user",
        )

    assert captured.value.code is ProviderErrorCode.MALFORMED_RESPONSE


@pytest.mark.asyncio
async def test_thinking_tool_follow_up_is_awaited_and_normalized() -> None:
    from aura_backend.thinking_processor import ThinkingProcessor

    call = SimpleNamespace(name="lookup", args={"query": "private"})
    chat = AsyncOnlyThinkingChat(
        [_response(_part(function_call=call)), _response(_part("tool answer"))]
    )

    class Bridge:
        async def execute_function_call(self, function_call: object, user_id: str) -> object:
            assert function_call is call
            assert user_id == "private-user"
            return SimpleNamespace(success=True, result={"found": True})

    result = await ThinkingProcessor(object()).process_with_function_calls_and_thinking(
        chat,
        "private message",
        "private-user",
        mcp_bridge=Bridge(),
    )

    assert chat.await_count == 2
    assert result.answer == "tool answer"
    assert result.thoughts == ""
    follow_up = chat.messages[1]
    assert isinstance(follow_up, list)
    assert follow_up[0]["function_response"]["name"] == "lookup"


@pytest.mark.asyncio
async def test_thinking_tool_failure_is_typed_and_redacted() -> None:
    from aura_backend.thinking_processor import ThinkingProcessor

    call = SimpleNamespace(name="lookup", args={})
    chat = AsyncOnlyThinkingChat([_response(_part(function_call=call))])

    class Bridge:
        async def execute_function_call(self, _call: object, _user_id: str) -> object:
            return SimpleNamespace(success=False, error="exception-SENTINEL")

    with pytest.raises(ProviderFailure) as captured:
        await ThinkingProcessor(object()).process_with_function_calls_and_thinking(
            chat,
            "private message",
            "private-user",
            mcp_bridge=Bridge(),
        )

    assert captured.value.code is ProviderErrorCode.UNAVAILABLE
    assert "SENTINEL" not in f"{captured.value!s} {captured.value!r}"


@pytest.mark.asyncio
async def test_thinking_cancellation_is_re_raised_without_fallback() -> None:
    from aura_backend.thinking_processor import ThinkingProcessor

    chat = AsyncOnlyThinkingChat([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await ThinkingProcessor(object()).process_message_with_thinking(
            chat,
            "private message",
            "private-user",
        )


def test_thinking_async_chat_factory_uses_only_client_aio() -> None:
    from aura_backend.thinking_processor import create_thinking_enabled_chat

    calls: list[dict[str, object]] = []
    async_chat = object()

    class AsyncChats:
        def create(self, **kwargs: object) -> object:
            calls.append(dict(kwargs))
            return async_chat

    class RootClient:
        aio = SimpleNamespace(chats=AsyncChats())

        @property
        def chats(self) -> object:
            raise AssertionError("synchronous client.chats was touched")

    created = create_thinking_enabled_chat(
        RootClient(),
        "synthetic-model",
        "private system instruction",
        thinking_budget=32,
    )

    assert created is async_chat
    assert calls[0]["model"] == "synthetic-model"
    assert calls[0]["config"]["thinking_config"]["thinking_budget"] == 32


def test_thinking_module_import_is_optional_sdk_safe() -> None:
    module = __import__("aura_backend.thinking_processor", fromlist=["*"])

    assert "genai" not in vars(module)
    assert "types" not in vars(module)
