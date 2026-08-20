"""Reusable offline provider fakes with event-controlled progress.

The fake deliberately records only operation counts and normalized terminal codes.
Requests, deltas, completed content, and session identifiers are never retained.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from aura_backend.providers.base import (
    Completed,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderRequest,
    ProviderResult,
    StreamEvent,
    TextDelta,
)
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure


@dataclass(frozen=True, slots=True)
class ScriptedDelta:
    """One incremental text instruction in a fake stream."""

    text: str

    def __post_init__(self) -> None:
        TextDelta(self.text)


@dataclass(frozen=True, slots=True)
class ScriptedComplete:
    """The sole successful terminal instruction in a fake script."""

    content: str

    def __post_init__(self) -> None:
        ProviderResult(content=self.content)


@dataclass(frozen=True, slots=True)
class ScriptedFailure:
    """A named normalized failure terminal in a fake script."""

    code: ProviderErrorCode
    retryable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.code, ProviderErrorCode):
            raise TypeError("code must be a ProviderErrorCode")


ScriptInstruction = ScriptedDelta | ScriptedComplete | ScriptedFailure


@dataclass(slots=True)
class SafeCallRecorder:
    """Content-free diagnostics for fake assertions."""

    generate_calls: int = 0
    stream_calls: int = 0
    clear_session_calls: int = 0
    health_calls: int = 0
    close_calls: int = 0
    cleanup_count: int = 0
    terminal_codes: list[str] = field(default_factory=list)
    emitted_event_counts: list[int] = field(default_factory=list)


def _open_gate() -> asyncio.Event:
    gate = asyncio.Event()
    gate.set()
    return gate


class ScriptedProvider:
    """Deterministic implementation of the production ``Provider`` protocol."""

    def __init__(
        self,
        steps: tuple[ScriptInstruction, ...],
        *,
        first_delta_gate: asyncio.Event | None = None,
        completion_gate: asyncio.Event | None = None,
    ) -> None:
        terminal_count = sum(
            isinstance(step, (ScriptedComplete, ScriptedFailure)) for step in steps
        )
        if terminal_count != 1:
            raise ValueError("script must contain exactly one terminal instruction")
        self._steps = steps
        self._first_delta_gate = first_delta_gate or _open_gate()
        self._completion_gate = completion_gate or _open_gate()
        self.recorder = SafeCallRecorder()
        self.first_delta_waiting = asyncio.Event()
        self.completion_waiting = asyncio.Event()
        self.cleanup_event = asyncio.Event()
        self.close_event = asyncio.Event()

    def _terminal(self) -> ScriptedComplete | ScriptedFailure:
        return next(
            step
            for step in self._steps
            if isinstance(step, (ScriptedComplete, ScriptedFailure))
        )

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        """Return or raise the script terminal without replaying stream deltas."""
        del request
        self.recorder.generate_calls += 1
        self.completion_waiting.set()
        await self._completion_gate.wait()
        terminal = self._terminal()
        if isinstance(terminal, ScriptedFailure):
            self.recorder.terminal_codes.append(terminal.code.value)
            raise ProviderFailure(
                code=terminal.code,
                provider="fake",
                model="synthetic-model",
                retryable=terminal.retryable,
            )
        self.recorder.terminal_codes.append("completed")
        return ProviderResult(content=terminal.content)

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        """Yield instructions incrementally and always expose iterator cleanup."""
        del request
        self.recorder.stream_calls += 1
        emitted_count = 0
        first_delta = True
        try:
            for step in self._steps:
                if isinstance(step, ScriptedDelta):
                    if first_delta:
                        self.first_delta_waiting.set()
                        await self._first_delta_gate.wait()
                        first_delta = False
                    emitted_count += 1
                    yield TextDelta(text=step.text)
                    continue
                if isinstance(step, ScriptedComplete):
                    self.completion_waiting.set()
                    await self._completion_gate.wait()
                    self.recorder.terminal_codes.append("completed")
                    emitted_count += 1
                    yield Completed(result=ProviderResult(content=step.content))
                    continue
                raise ProviderFailure(
                    code=step.code,
                    provider="fake",
                    model="synthetic-model",
                    retryable=step.retryable,
                    partial_event_count=emitted_count,
                )
        except asyncio.CancelledError:
            self.recorder.terminal_codes.append(ProviderErrorCode.CANCELLED.value)
            raise
        except ProviderFailure as failure:
            self.recorder.terminal_codes.append(failure.code.value)
            raise
        finally:
            self.recorder.emitted_event_counts.append(emitted_count)
            self.recorder.cleanup_count += 1
            self.cleanup_event.set()

    async def clear_session(self, session_id: str) -> None:
        """Record a clear without retaining its identifier."""
        del session_id
        self.recorder.clear_session_calls += 1

    async def health(self) -> ProviderHealth:
        """Return deterministic side-effect-free fake readiness."""
        self.recorder.health_calls += 1
        return ProviderHealth(
            provider="fake",
            model="synthetic-model",
            status=ProviderHealthStatus.READY,
        )

    async def aclose(self) -> None:
        """Expose adapter close calls without acquiring external resources."""
        self.recorder.close_calls += 1
        self.close_event.set()
