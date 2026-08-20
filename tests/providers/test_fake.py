"""Deterministic contract tests for the event-controlled provider fake."""

from __future__ import annotations

import asyncio

import pytest

from aura_backend.providers.base import Completed, ProviderMessage, ProviderRequest, TextDelta
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from tests.providers.fakes import (
    ScriptedComplete,
    ScriptedDelta,
    ScriptedFailure,
    ScriptedProvider,
)


def _request() -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content="private synthetic prompt"),),
        session_id="session-1",
        correlation_id="correlation-1",
    )


@pytest.mark.asyncio
async def test_first_delta_is_observable_before_completion_is_released() -> None:
    first_delta_gate = asyncio.Event()
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (
            ScriptedDelta("first"),
            ScriptedDelta(" second"),
            ScriptedComplete("first second"),
        ),
        first_delta_gate=first_delta_gate,
        completion_gate=completion_gate,
    )
    stream = provider.stream(_request())

    pending_first = asyncio.create_task(anext(stream))
    await provider.first_delta_waiting.wait()
    assert not pending_first.done()

    first_delta_gate.set()
    assert await pending_first == TextDelta(text="first")
    assert not completion_gate.is_set()

    assert await anext(stream) == TextDelta(text=" second")
    pending_terminal = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()
    assert not pending_terminal.done()

    completion_gate.set()
    terminal = await pending_terminal
    assert isinstance(terminal, Completed)
    with pytest.raises(StopAsyncIteration):
        await anext(stream)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "expected_partial_count"),
    (
        (ProviderErrorCode.MALFORMED_RESPONSE, 0),
        (ProviderErrorCode.TIMEOUT, 0),
        (ProviderErrorCode.MODEL_NOT_FOUND, 0),
        (ProviderErrorCode.UNAVAILABLE, 0),
        (ProviderErrorCode.AUTHENTICATION, 0),
        (ProviderErrorCode.RESOURCE_LIMIT, 0),
        (ProviderErrorCode.STREAM_INTERRUPTED, 1),
    ),
)
async def test_named_failure_outcomes_are_distinct_and_never_complete(
    code: ProviderErrorCode,
    expected_partial_count: int,
) -> None:
    steps = (
        (ScriptedDelta("partial"), ScriptedFailure(code))
        if expected_partial_count
        else (ScriptedFailure(code),)
    )
    provider = ScriptedProvider(steps)
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as raised:
        async for event in provider.stream(_request()):
            observed.append(event)

    assert raised.value.code is code
    assert raised.value.partial_event_count == expected_partial_count
    assert not any(isinstance(event, Completed) for event in observed)
    assert provider.recorder.terminal_codes[-1] == code.value


@pytest.mark.asyncio
async def test_generate_uses_the_script_terminal_without_replaying_deltas() -> None:
    provider = ScriptedProvider(
        (ScriptedDelta("incremental"), ScriptedComplete("complete result"))
    )

    result = await provider.generate(_request())

    assert result.content == "complete result"
    assert provider.recorder.generate_calls == 1
    assert provider.recorder.emitted_event_counts == []


def test_invalid_scripts_with_missing_or_multiple_terminals_are_rejected() -> None:
    with pytest.raises(ValueError, match="exactly one terminal"):
        ScriptedProvider((ScriptedDelta("unterminated"),))
    with pytest.raises(ValueError, match="exactly one terminal"):
        ScriptedProvider(
            (ScriptedComplete("first"), ScriptedFailure(ProviderErrorCode.TIMEOUT))
        )


@pytest.mark.asyncio
async def test_cancellation_runs_generator_cleanup_and_reraises() -> None:
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedDelta("partial"), ScriptedComplete("never completed")),
        completion_gate=completion_gate,
    )
    stream = provider.stream(_request())
    assert await anext(stream) == TextDelta(text="partial")

    pending = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending
    await asyncio.wait_for(provider.cleanup_event.wait(), timeout=0.5)
    assert provider.recorder.terminal_codes[-1] == ProviderErrorCode.CANCELLED.value
    assert provider.recorder.cleanup_count == 1


def test_recorder_retains_only_safe_counts_and_codes() -> None:
    provider = ScriptedProvider((ScriptedComplete("private response"),))

    representation = repr(provider.recorder)

    assert "private response" not in representation
    assert "private synthetic prompt" not in representation
    assert not hasattr(provider.recorder, "requests")
    assert not hasattr(provider.recorder, "responses")
