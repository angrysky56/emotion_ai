"""Offline Ollama policy tests; no local service or model is contacted."""

from __future__ import annotations

import asyncio
import inspect
import socket
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIConnectionError, NotFoundError

from aura_backend.providers.base import (
    Completed,
    ProviderHealthStatus,
    ProviderMessage,
    ProviderRequest,
    TextDelta,
)
from aura_backend.providers.config import ProviderSettings
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.openai_compatible import OpenAICompatibleProvider
from tests.providers.test_openai_compatible import FakeClient, FakeStream, _chunk, _response


def _settings(**overrides: str) -> ProviderSettings:
    return ProviderSettings.from_mapping(
        {"OLLAMA_MODEL": "ornith-synthetic", **overrides}
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content="synthetic request"),),
        correlation_id="ollama-test",
    )


class FakeModels:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls = 0

    async def list(self) -> object:
        self.calls += 1
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        if callable(self.outcome):
            return await self.outcome()
        return self.outcome


def _client(models: object, outcomes: list[object] | None = None) -> FakeClient:
    client = FakeClient(outcomes or [_response("done")])
    client.models = FakeModels(models)  # type: ignore[attr-defined]
    return client


def test_ollama_normalizes_loopback_v1_and_uses_only_syntactic_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_backend.providers.ollama import OllamaProvider

    def forbidden_connect(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("deterministic Ollama tests must not use sockets")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeClient:
        captured.update(kwargs)
        return _client(SimpleNamespace(data=[]))

    provider = OllamaProvider(
        settings=_settings(OLLAMA_BASE_URL="http://127.0.0.1:11434/"),
        client_factory=factory,
    )

    assert isinstance(provider, OpenAICompatibleProvider)
    assert captured["base_url"] == "http://127.0.0.1:11434/v1"
    assert captured["api_key"] == "ollama"
    assert captured["max_retries"] == 0
    assert "AsyncOpenAI" not in inspect.getsource(OllamaProvider)
    assert ".chat.completions.create" not in inspect.getsource(OllamaProvider)


@pytest.mark.asyncio
async def test_model_list_readiness_distinguishes_ready_and_missing_model() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    ready_client = _client(
        SimpleNamespace(data=[SimpleNamespace(id="ornith-synthetic")])
    )
    ready = await OllamaProvider(settings=_settings(), client=ready_client).health()
    assert ready.status is ProviderHealthStatus.READY
    assert ready_client.models.calls == 1  # type: ignore[attr-defined]
    assert ready_client.completions.calls == []

    missing = await OllamaProvider(
        settings=_settings(),
        client=_client(SimpleNamespace(data=[SimpleNamespace(id="other-model")])),
    ).health()
    assert missing.status is ProviderHealthStatus.MODEL_NOT_FOUND
    assert missing.retryable is False


@pytest.mark.asyncio
async def test_model_list_unavailable_and_timeout_are_safe_and_bounded() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    request = httpx.Request("GET", "http://credential-SENTINEL.invalid/v1/models")
    unavailable = await OllamaProvider(
        settings=_settings(),
        client=_client(APIConnectionError(request=request)),
    ).health()
    assert unavailable.status is ProviderHealthStatus.UNAVAILABLE
    assert unavailable.retryable is True
    assert "SENTINEL" not in repr(unavailable)

    async def blocked() -> object:
        await asyncio.Event().wait()
        return SimpleNamespace(data=[])

    timed = await OllamaProvider(
        settings=_settings(AURA_PROVIDER_CONNECT_TIMEOUT_SECONDS="0.01"),
        client=_client(blocked),
    ).health()
    assert timed.status is ProviderHealthStatus.UNAVAILABLE
    assert timed.retryable is True


@pytest.mark.asyncio
async def test_malformed_model_list_is_a_typed_failure_not_ready() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    provider = OllamaProvider(settings=_settings(), client=_client(object()))
    with pytest.raises(ProviderFailure) as captured:
        await provider.health()
    assert captured.value.code is ProviderErrorCode.MALFORMED_RESPONSE


@pytest.mark.asyncio
async def test_missing_model_generation_maps_404_without_raw_detail() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    request = httpx.Request("POST", "http://127.0.0.1:11434/v1/chat/completions")
    error = NotFoundError(
        "private missing model response SENTINEL",
        response=httpx.Response(404, request=request),
        body=None,
    )
    provider = OllamaProvider(
        settings=_settings(),
        client=_client(SimpleNamespace(data=[]), [error]),
    )

    with pytest.raises(ProviderFailure) as captured:
        await provider.generate(_request())
    assert captured.value.code is ProviderErrorCode.MODEL_NOT_FOUND
    assert "SENTINEL" not in f"{captured.value!s} {captured.value!r}"


@pytest.mark.asyncio
async def test_ollama_stream_is_incremental_and_partial_failure_never_completes() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    upstream = FakeStream(
        [_chunk("first")],
        RuntimeError("private upstream SENTINEL"),
    )
    provider = OllamaProvider(
        settings=_settings(),
        client=_client(SimpleNamespace(data=[]), [upstream]),
    )
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as captured:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert observed == [TextDelta("first")]
    assert captured.value.code is ProviderErrorCode.STREAM_INTERRUPTED
    assert not any(isinstance(event, Completed) for event in observed)
    assert upstream.closed


@pytest.mark.asyncio
async def test_ollama_resource_finish_is_typed_and_never_completed() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    upstream = FakeStream([_chunk("bounded partial", finish_reason="length")])
    provider = OllamaProvider(
        settings=_settings(),
        client=_client(SimpleNamespace(data=[]), [upstream]),
    )
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as captured:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert captured.value.code is ProviderErrorCode.RESOURCE_LIMIT
    assert observed == [TextDelta("bounded partial")]
    assert not any(isinstance(event, Completed) for event in observed)


@pytest.mark.asyncio
async def test_ollama_cancellation_closes_local_stream_without_remote_claim() -> None:
    from aura_backend.providers.ollama import OllamaProvider

    entered = asyncio.Event()

    class BlockingStream(FakeStream):
        async def __aiter__(self):
            entered.set()
            await asyncio.Event().wait()
            yield _chunk("never")

    upstream = BlockingStream([])
    provider = OllamaProvider(
        settings=_settings(),
        client=_client(SimpleNamespace(data=[]), [upstream]),
    )
    stream = provider.stream(_request())
    pending = asyncio.create_task(anext(stream))
    await entered.wait()
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending
    assert upstream.closed
    assert "upstream" not in repr(provider).lower()
