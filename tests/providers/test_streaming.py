"""Adversarial offline tests for provider runtime ownership and streaming truth."""

from __future__ import annotations

import asyncio

import pytest

from aura_backend.providers.base import Completed, ProviderMessage, ProviderRequest, TextDelta
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.runtime import ProviderRuntime
from tests.providers.fakes import (
    ScriptedComplete,
    ScriptedDelta,
    ScriptedFailure,
    ScriptedProvider,
)


def _request(*, session_id: str = "session-1") -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content="private runtime prompt"),),
        session_id=session_id,
        correlation_id=f"correlation-{session_id}",
    )


@pytest.mark.asyncio
async def test_runtime_delivers_first_delta_before_adapter_can_complete() -> None:
    first_delta_gate = asyncio.Event()
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedDelta("first"), ScriptedComplete("first done")),
        first_delta_gate=first_delta_gate,
        completion_gate=completion_gate,
    )
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    stream = runtime.stream(_request())

    pending_first = asyncio.create_task(anext(stream))
    await provider.first_delta_waiting.wait()
    assert runtime.snapshot().in_flight_count == 1
    assert not pending_first.done()

    first_delta_gate.set()
    assert await pending_first == TextDelta(text="first")
    assert not completion_gate.is_set()

    pending_terminal = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()
    assert not pending_terminal.done()
    completion_gate.set()

    terminal = await pending_terminal
    assert isinstance(terminal, Completed)
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert runtime.snapshot().in_flight_count == 0


@pytest.mark.asyncio
async def test_midstream_failure_keeps_partial_count_but_no_content_or_completed() -> None:
    provider = ScriptedProvider(
        (
            ScriptedDelta("private partial response"),
            ScriptedFailure(ProviderErrorCode.STREAM_INTERRUPTED),
        )
    )
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as raised:
        async for event in runtime.stream(_request()):
            observed.append(event)

    assert observed == [TextDelta(text="private partial response")]
    assert raised.value.code is ProviderErrorCode.STREAM_INTERRUPTED
    assert raised.value.partial_event_count == 1
    assert not any(isinstance(event, Completed) for event in observed)
    snapshot = runtime.snapshot()
    assert snapshot.in_flight_count == 0
    assert snapshot.partial_event_count == 1
    assert snapshot.upstream_compute_cancellation == "unknown"
    assert "private partial response" not in repr(snapshot)


@pytest.mark.asyncio
async def test_terminal_followed_by_delta_is_malformed_and_never_exposed_as_complete() -> None:
    provider = ScriptedProvider(
        (ScriptedComplete("private false success"), ScriptedDelta("late delta"))
    )
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as raised:
        async for event in runtime.stream(_request()):
            observed.append(event)

    assert raised.value.code is ProviderErrorCode.MALFORMED_RESPONSE
    assert observed == []
    assert runtime.snapshot().in_flight_count == 0


@pytest.mark.asyncio
async def test_absolute_deadline_closes_stream_without_completion() -> None:
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedDelta("partial"), ScriptedComplete("never released")),
        completion_gate=completion_gate,
    )
    runtime = ProviderRuntime(provider, timeout_seconds=0.02)
    observed: list[object] = []

    with pytest.raises(ProviderFailure) as raised:
        async for event in runtime.stream(_request()):
            observed.append(event)

    assert raised.value.code is ProviderErrorCode.TIMEOUT
    assert raised.value.partial_event_count == 1
    assert observed == [TextDelta(text="partial")]
    await asyncio.wait_for(provider.cleanup_event.wait(), timeout=0.5)
    assert runtime.snapshot().in_flight_count == 0


@pytest.mark.asyncio
async def test_caller_cancellation_closes_iterator_reraises_and_clears_registry() -> None:
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedDelta("partial"), ScriptedComplete("never completed")),
        completion_gate=completion_gate,
    )
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    stream = runtime.stream(_request())
    assert await anext(stream) == TextDelta(text="partial")

    pending = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending
    await asyncio.wait_for(provider.cleanup_event.wait(), timeout=0.5)
    assert runtime.snapshot().in_flight_count == 0
    assert runtime.snapshot().last_terminal_code == ProviderErrorCode.CANCELLED.value
    assert "completed" not in provider.recorder.terminal_codes


@pytest.mark.asyncio
async def test_clear_session_cancels_matching_work_and_delegates_after_cleanup() -> None:
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedDelta("partial"), ScriptedComplete("never completed")),
        completion_gate=completion_gate,
    )
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    stream = runtime.stream(_request(session_id="session-clear"))
    assert await anext(stream) == TextDelta(text="partial")

    pending = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()
    await runtime.clear_session("session-clear")

    with pytest.raises(asyncio.CancelledError):
        await pending
    assert provider.recorder.clear_session_calls == 1
    assert runtime.snapshot().in_flight_count == 0


@pytest.mark.asyncio
async def test_shutdown_cancels_active_work_closes_once_and_wakes_consumer() -> None:
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedDelta("partial"), ScriptedComplete("never completed")),
        completion_gate=completion_gate,
    )
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    stream = runtime.stream(_request())
    assert await anext(stream) == TextDelta(text="partial")
    pending = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()

    await asyncio.wait_for(runtime.aclose(), timeout=0.5)
    with pytest.raises(asyncio.CancelledError):
        await pending
    await runtime.aclose()

    assert runtime.snapshot().in_flight_count == 0
    assert provider.recorder.close_calls == 1
    assert provider.recorder.cleanup_count == 1
    assert "completed" not in provider.recorder.terminal_codes


@pytest.mark.asyncio
async def test_generate_deadline_and_provider_failure_always_leave_empty_registry() -> None:
    blocked_gate = asyncio.Event()
    blocked_provider = ScriptedProvider(
        (ScriptedComplete("never released"),), completion_gate=blocked_gate
    )
    blocked_runtime = ProviderRuntime(blocked_provider, timeout_seconds=0.02)

    with pytest.raises(ProviderFailure) as timeout:
        await blocked_runtime.generate(_request())
    assert timeout.value.code is ProviderErrorCode.TIMEOUT
    assert blocked_runtime.snapshot().in_flight_count == 0

    failing_provider = ScriptedProvider(
        (ScriptedFailure(ProviderErrorCode.AUTHENTICATION),)
    )
    failing_runtime = ProviderRuntime(failing_provider, timeout_seconds=1.0)
    with pytest.raises(ProviderFailure) as failure:
        await failing_runtime.generate(_request())
    assert failure.value.code is ProviderErrorCode.AUTHENTICATION
    assert failing_runtime.snapshot().in_flight_count == 0

    await failing_runtime.aclose()
    await failing_runtime.aclose()
    assert failing_provider.recorder.close_calls == 1


@pytest.mark.asyncio
async def test_registry_bound_rejects_excess_work_without_starting_provider() -> None:
    first_gate = asyncio.Event()
    first_provider = ScriptedProvider(
        (ScriptedComplete("held"),), completion_gate=first_gate
    )
    runtime = ProviderRuntime(first_provider, timeout_seconds=1.0, max_in_flight=1)
    first = asyncio.create_task(runtime.generate(_request(session_id="first")))
    await first_provider.completion_waiting.wait()

    with pytest.raises(ProviderFailure) as raised:
        await runtime.generate(_request(session_id="second"))
    assert raised.value.code is ProviderErrorCode.RESOURCE_LIMIT
    assert first_provider.recorder.generate_calls == 1

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert runtime.snapshot().in_flight_count == 0


@pytest.mark.asyncio
async def test_health_delegates_without_generation_and_snapshot_is_content_free() -> None:
    provider = ScriptedProvider((ScriptedComplete("private response"),))
    runtime = ProviderRuntime(provider, timeout_seconds=1.0)

    health = await runtime.health()
    snapshot = runtime.snapshot()

    assert health.ready
    assert provider.recorder.health_calls == 1
    assert provider.recorder.generate_calls == 0
    assert snapshot.upstream_compute_cancellation == "unknown"
    assert "private response" not in repr(snapshot)
    assert "private runtime prompt" not in repr(snapshot)
