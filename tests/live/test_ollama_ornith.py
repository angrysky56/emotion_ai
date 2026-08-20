"""Opt-in, bounded live evidence for Aura's local Ornith provider path.

The deterministic tests in this module exercise the gate with fakes.  Only the
test marked ``live`` and ``ollama`` can contact the loopback Ollama service.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Protocol

import pytest

from aura_backend.providers.base import (
    Completed,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderMessage,
    ProviderRequest,
    ProviderResult,
    StreamEvent,
    TextDelta,
)
from aura_backend.providers.config import ProviderSettings
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.ollama import OllamaProvider
from aura_backend.providers.runtime import ProviderRuntime


LIVE_TIMEOUT_SECONDS = 90.0
EXPECTED_MODEL = "ornith:latest"


class _ProviderFactory(Protocol):
    def __call__(self, settings: ProviderSettings) -> object: ...


def _live_settings(environment: Mapping[str, str]) -> ProviderSettings:
    """Fail closed before constructing a client unless all opt-ins are exact."""
    if environment.get("AURA_RUN_LIVE") != "1":
        pytest.skip("live Ollama disabled: set AURA_RUN_LIVE=1")
    if environment.get("AURA_DEFAULT_PROVIDER") != "ollama":
        pytest.skip("live Ollama disabled: set AURA_DEFAULT_PROVIDER=ollama")
    if environment.get("OLLAMA_MODEL") != EXPECTED_MODEL:
        pytest.skip("live Ollama model disabled: set OLLAMA_MODEL=ornith:latest")
    return ProviderSettings.from_mapping(environment)


def _safe_failure(failure: ProviderFailure) -> str:
    """Serialize only Aura's fixed safe provider metadata."""
    return json.dumps(failure.to_public_dict(), sort_keys=True)


def _request(session_id: str, *, max_tokens: int) -> ProviderRequest:
    """Build a content-free synthetic request with no tools or memory."""
    return ProviderRequest(
        messages=(
            ProviderMessage(
                role="user",
                content=(
                    "Synthetic runtime probe. Return the word READY followed by "
                    "the integers one through twelve. Do not use external tools."
                ),
            ),
        ),
        tools=(),
        temperature=0.0,
        max_tokens=max_tokens,
        session_id=session_id,
        correlation_id=f"live-{session_id}",
    )


async def _run_live_probe(
    environment: Mapping[str, str],
    *,
    provider_factory: Callable[[ProviderSettings], object] = OllamaProvider,
) -> None:
    """Run preflight, streaming, and local-cancellation evidence."""
    settings = _live_settings(environment)
    provider = provider_factory(settings)
    runtime = ProviderRuntime(  # type: ignore[arg-type]
        provider,
        timeout_seconds=min(settings.request_timeout_seconds, LIVE_TIMEOUT_SECONDS),
    )
    prerequisites_confirmed = False
    try:
        health = await runtime.health()
        if health.status is ProviderHealthStatus.UNAVAILABLE:
            pytest.skip("live Ollama unavailable: loopback service is unreachable")
        if health.status is ProviderHealthStatus.MODEL_NOT_FOUND:
            pytest.skip("live Ollama model missing: ornith:latest")
        if health.status is not ProviderHealthStatus.READY:
            pytest.fail(f"live Ollama preflight failed: status={health.status.value}")
        prerequisites_confirmed = True

        events: list[StreamEvent] = []
        async for event in runtime.stream(_request("stream", max_tokens=64)):
            events.append(event)
        assert events
        assert isinstance(events[0], TextDelta)
        assert events[0].text
        assert isinstance(events[-1], Completed)
        assert sum(isinstance(event, Completed) for event in events) == 1

        cancel_stream = runtime.stream(_request("cancel", max_tokens=512))
        first_cancel_event = await anext(cancel_stream)
        assert isinstance(first_cancel_event, TextDelta)
        await runtime.clear_session("cancel")
        with pytest.raises(asyncio.CancelledError):
            await anext(cancel_stream)
        await cancel_stream.aclose()

        snapshot = runtime.snapshot()
        assert snapshot.in_flight_count == 0
        assert snapshot.last_terminal_code == ProviderErrorCode.CANCELLED.value
        assert snapshot.upstream_compute_cancellation == "unknown"
    except pytest.skip.Exception:
        raise
    except ProviderFailure as failure:
        stage = "execution" if prerequisites_confirmed else "preflight"
        pytest.fail(f"live Ollama {stage} failed: {_safe_failure(failure)}")
    except TimeoutError:
        pytest.fail("live Ollama execution failed: category=timeout")
    finally:
        await runtime.aclose()


def test_live_gate_skips_before_constructing_a_provider() -> None:
    """Missing opt-in cannot instantiate a client or contact loopback."""
    constructed = False

    def forbidden_factory(_settings: ProviderSettings) -> object:
        nonlocal constructed
        constructed = True
        raise AssertionError("provider construction must happen after opt-in")

    with pytest.raises(
        pytest.skip.Exception,
        match="live Ollama disabled: set AURA_RUN_LIVE=1",
    ):
        asyncio.run(_run_live_probe({}, provider_factory=forbidden_factory))

    assert constructed is False


class _PreflightProvider:
    """Small fake used only to verify live-gate truth states offline."""

    def __init__(self, status: ProviderHealthStatus) -> None:
        self.status = status
        self.stream_calls = 0

    async def generate(self, _request: ProviderRequest) -> ProviderResult:
        raise AssertionError("live probe uses streaming")

    async def stream(self, _request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        self.stream_calls += 1
        yield Completed(ProviderResult(content="synthetic"))

    async def clear_session(self, _session_id: str) -> None:
        return None

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="ollama",
            model=EXPECTED_MODEL,
            status=self.status,
            retryable=self.status is ProviderHealthStatus.UNAVAILABLE,
        )

    async def aclose(self) -> None:
        return None


@pytest.mark.parametrize(
    ("status", "reason"),
    (
        (
            ProviderHealthStatus.UNAVAILABLE,
            "live Ollama unavailable: loopback service is unreachable",
        ),
        (
            ProviderHealthStatus.MODEL_NOT_FOUND,
            "live Ollama model missing: ornith:latest",
        ),
    ),
)
def test_live_preflight_has_exact_environment_skip_reasons(
    status: ProviderHealthStatus,
    reason: str,
) -> None:
    """Only unreachable service and absent model are environment skips."""
    provider = _PreflightProvider(status)
    environment = {
        "AURA_RUN_LIVE": "1",
        "AURA_DEFAULT_PROVIDER": "ollama",
        "OLLAMA_MODEL": EXPECTED_MODEL,
    }

    with pytest.raises(pytest.skip.Exception, match=reason):
        asyncio.run(_run_live_probe(environment, provider_factory=lambda _settings: provider))

    assert provider.stream_calls == 0


@pytest.mark.live
@pytest.mark.ollama
@pytest.mark.asyncio
async def test_ornith_streaming_and_local_cancellation() -> None:
    """Exercise the public Aura runtime only after exact explicit opt-in."""
    async with asyncio.timeout(LIVE_TIMEOUT_SECONDS):
        await _run_live_probe(os.environ)

