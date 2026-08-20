"""Offline OpenRouter endpoint, envelope, and redaction policy tests."""

from __future__ import annotations

import inspect
import logging
from types import SimpleNamespace
from typing import Any

import pytest

from aura_backend.providers.base import (
    Completed,
    ProviderMessage,
    ProviderRequest,
    TextDelta,
)
from aura_backend.providers.config import ProviderSettings
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.openai_compatible import OpenAICompatibleProvider
from tests.providers.test_openai_compatible import FakeClient, FakeStream, _chunk, _response


API_KEY = "credential-SENTINEL-openrouter"


def _settings(**overrides: str) -> ProviderSettings:
    return ProviderSettings.from_mapping(
        {
            "AURA_DEFAULT_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": API_KEY,
            "OPENROUTER_MODEL": "synthetic/model",
            **overrides,
        }
    )


def _request() -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content="prompt-SENTINEL"),),
        correlation_id="openrouter-test",
    )


def test_openrouter_requires_explicit_credential_before_client_construction() -> None:
    from aura_backend.providers.openrouter import OpenRouterProvider

    constructed = False

    def forbidden_factory(**_kwargs: Any) -> object:
        nonlocal constructed
        constructed = True
        raise AssertionError("client construction must not occur")

    with pytest.raises(ProviderFailure) as captured:
        OpenRouterProvider(api_key=None, client_factory=forbidden_factory)

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.setting_name == "OPENROUTER_API_KEY"
    assert constructed is False


def test_openrouter_sets_supported_endpoint_headers_and_shared_transport() -> None:
    from aura_backend.providers.openrouter import OpenRouterProvider

    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeClient:
        captured.update(kwargs)
        return FakeClient([_response("done")])

    provider = OpenRouterProvider(settings=_settings(), client_factory=factory)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["api_key"] == API_KEY
    assert captured["max_retries"] == 0
    assert captured["default_headers"] == {
        "HTTP-Referer": "https://github.com/angrysky56/emotion_ai",
        "X-Title": "Aura",
    }
    source = inspect.getsource(OpenRouterProvider)
    assert "AsyncOpenAI" not in source
    assert ".chat.completions.create" not in source


@pytest.mark.asyncio
async def test_prestream_error_envelope_maps_exact_code_without_completion() -> None:
    from aura_backend.providers.openrouter import OpenRouterProvider

    envelope = SimpleNamespace(
        code=429,
        message="response-SENTINEL rate detail",
        metadata={"error_type": "rate_limit_exceeded"},
    )
    upstream = FakeStream([_chunk(error=envelope)])
    provider = OpenRouterProvider(settings=_settings(), client=FakeClient([upstream]))
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as captured:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert captured.value.code is ProviderErrorCode.RATE_LIMITED
    assert captured.value.partial_event_count == 0
    assert observed == []
    assert upstream.closed


@pytest.mark.asyncio
async def test_nonstream_choice_error_envelope_is_not_partial_success() -> None:
    from aura_backend.providers.openrouter import OpenRouterProvider

    response = _response("partial response-SENTINEL", finish_reason="error")
    response.choices[0].error = SimpleNamespace(
        code=502,
        message="exception-SENTINEL",
        metadata={"error_type": "provider_unavailable"},
    )
    provider = OpenRouterProvider(settings=_settings(), client=FakeClient([response]))

    with pytest.raises(ProviderFailure) as captured:
        await provider.generate(_request())

    assert captured.value.code is ProviderErrorCode.UNAVAILABLE
    assert "SENTINEL" not in f"{captured.value!s} {captured.value!r}"


@pytest.mark.asyncio
async def test_midstream_error_keeps_only_count_and_never_completes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from aura_backend.providers.openrouter import OpenRouterProvider

    envelope = SimpleNamespace(
        code=502,
        message="exception-SENTINEL upstream detail",
        metadata={"error_type": "provider_unavailable"},
    )
    upstream = FakeStream(
        [_chunk("response-SENTINEL partial"), _chunk(error=envelope)]
    )
    provider = OpenRouterProvider(settings=_settings(), client=FakeClient([upstream]))
    observed: list[object] = []

    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderFailure) as captured:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert observed == [TextDelta("response-SENTINEL partial")]
    assert captured.value.code is ProviderErrorCode.STREAM_INTERRUPTED
    assert captured.value.partial_event_count == 1
    assert not any(isinstance(event, Completed) for event in observed)
    diagnostics = (
        f"{captured.value!s} {captured.value!r} "
        f"{captured.value.to_public_dict()!r} {caplog.text} {provider!r}"
    )
    for sentinel in (
        API_KEY,
        "prompt-SENTINEL",
        "response-SENTINEL",
        "exception-SENTINEL",
        "Authorization",
        "https://openrouter.ai/api/v1",
    ):
        assert sentinel not in diagnostics
    assert upstream.closed


@pytest.mark.asyncio
async def test_openrouter_normal_success_still_uses_shared_result_contract() -> None:
    from aura_backend.providers.openrouter import OpenRouterProvider

    provider = OpenRouterProvider(
        settings=_settings(),
        client=FakeClient([_response("safe answer")]),
    )
    result = await provider.generate(_request())

    assert result.content == "safe answer"
    assert not hasattr(result, "raw_response")
