"""Provider-neutral contract tests for Aura's existing analysis behavior."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable

import pytest

from aura_backend.providers.base import ProviderRequest, ProviderResult
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure


Generate = Callable[[ProviderRequest], Awaitable[ProviderResult]]


class _RecordingGenerate:
    """Record typed requests while returning deterministic provider results."""

    def __init__(self, *outcomes: ProviderResult | BaseException) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[ProviderRequest] = []

    async def __call__(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.mark.asyncio
async def test_all_analyses_use_typed_requests_and_preserve_domain_mappings() -> None:
    from aura_backend.conversation.analysis import (
        AsekeComponent,
        EmotionalIntensity,
        detect_aura_cognitive_focus,
        detect_aura_emotion,
        detect_user_emotion,
    )

    generate: Generate = _RecordingGenerate(
        ProviderResult(content="Excited (High)"),
        ProviderResult(content="Curiosity (Low)"),
        ProviderResult(content="KI"),
    )

    user_state = await detect_user_emotion(
        "synthetic user message", "synthetic-user", generate=generate
    )
    aura_state = await detect_aura_emotion(
        "synthetic conversation", "synthetic-user", generate=generate
    )
    cognitive_state = await detect_aura_cognitive_focus(
        "synthetic conversation", "synthetic-user", generate=generate
    )

    assert user_state is not None
    assert user_state.name == "Excited"
    assert user_state.intensity is EmotionalIntensity.HIGH
    assert user_state.brainwave == "Beta"
    assert aura_state is not None
    assert aura_state.name == "Curiosity"
    assert aura_state.intensity is EmotionalIntensity.LOW
    assert cognitive_state is not None
    assert cognitive_state.focus is AsekeComponent.KI
    assert len(generate.requests) == 3  # type: ignore[attr-defined]
    assert all(isinstance(item, ProviderRequest) for item in generate.requests)  # type: ignore[attr-defined]
    assert all(len(item.messages) == 1 for item in generate.requests)  # type: ignore[attr-defined]
    assert all(item.messages[0].role == "user" for item in generate.requests)  # type: ignore[attr-defined]
    assert all(item.tools == () for item in generate.requests)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_malformed_analysis_content_keeps_existing_safe_defaults() -> None:
    from aura_backend.conversation.analysis import (
        AsekeComponent,
        EmotionalIntensity,
        detect_aura_cognitive_focus,
        detect_aura_emotion,
        detect_user_emotion,
    )

    generate: Generate = _RecordingGenerate(
        ProviderResult(content="not an allowed emotion"),
        ProviderResult(content="Unsupported (Extreme)"),
        ProviderResult(content="not-a-component"),
    )

    user_state = await detect_user_emotion("message", "user", generate=generate)
    aura_state = await detect_aura_emotion("conversation", "user", generate=generate)
    cognitive_state = await detect_aura_cognitive_focus(
        "conversation", "user", generate=generate
    )

    assert user_state is not None
    assert user_state.name == "Normal"
    assert user_state.intensity is EmotionalIntensity.MEDIUM
    assert aura_state is not None
    assert aura_state.name == "Normal"
    assert aura_state.intensity is EmotionalIntensity.MEDIUM
    assert cognitive_state is not None
    assert cognitive_state.focus is AsekeComponent.LEARNING
    assert cognitive_state.context == "Default cognitive focus"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysis_name",
    ("detect_user_emotion", "detect_aura_emotion", "detect_aura_cognitive_focus"),
)
async def test_analysis_failure_returns_none_without_source_content_in_logs(
    analysis_name: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from aura_backend.conversation import analysis

    source_sentinel = "raw-provider-error-SENTINEL"
    prompt_sentinel = "private-prompt-SENTINEL"
    failure = ProviderFailure(
        code=ProviderErrorCode.UNAVAILABLE,
        provider="fake",
        model="synthetic-model",
        correlation_id="safe-correlation",
    )
    failure.__cause__ = RuntimeError(source_sentinel)
    generate: Generate = _RecordingGenerate(failure)
    function = getattr(analysis, analysis_name)

    with caplog.at_level(logging.WARNING):
        result = await function(prompt_sentinel, "private-user", generate=generate)

    assert result is None
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert source_sentinel not in rendered_logs
    assert prompt_sentinel not in rendered_logs
    assert "private-user" not in rendered_logs


@pytest.mark.asyncio
async def test_analysis_cancellation_propagates() -> None:
    from aura_backend.conversation.analysis import detect_user_emotion

    generate: Generate = _RecordingGenerate(asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await detect_user_emotion("message", "user", generate=generate)


def test_analysis_module_has_no_provider_sdk_or_global_client_branch() -> None:
    from aura_backend.conversation import analysis

    source = inspect.getsource(analysis)

    assert "generate_content" not in source
    assert "client.models" not in source
    assert "google.genai" not in source
    assert "openai" not in source.lower()
