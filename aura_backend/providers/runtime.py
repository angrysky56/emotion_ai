"""Lifecycle and terminal-state ownership for one selected provider.

Aura guarantees cancellation and cleanup only for its local task, iterator,
provider client, and in-flight registry. Whether an upstream service stops model
compute or billing after local cancellation is deliberately reported as unknown.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

from .base import (
    Completed,
    Provider,
    ProviderHealth,
    ProviderRequest,
    ProviderResult,
    StreamEvent,
    TextDelta,
    ToolCallDelta,
)
from .errors import ProviderErrorCode, ProviderFailure


_T = TypeVar("_T")
_END = object()
_CANCELLED = object()


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Content-free runtime counters and the explicit upstream truth boundary."""

    in_flight_count: int
    completed_operations: int
    failed_operations: int
    cancelled_operations: int
    last_terminal_code: str | None
    partial_event_count: int
    upstream_compute_cancellation: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class _OperationKeys:
    session_id: str | None
    correlation_id: str | None

    def matches(self, key: str) -> bool:
        return key == self.session_id or key == self.correlation_id


@dataclass(frozen=True, slots=True)
class _FailureSignal:
    failure: ProviderFailure


QueueItem = StreamEvent | _FailureSignal | object


class ProviderRuntime:
    """Own deadlines, active operations, stream validation, and provider close."""

    def __init__(
        self,
        provider: Provider,
        *,
        timeout_seconds: float,
        max_in_flight: int = 128,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be finite and positive")
        if (
            not isinstance(max_in_flight, int)
            or isinstance(max_in_flight, bool)
            or max_in_flight <= 0
        ):
            raise ValueError("max_in_flight must be a positive integer")
        self._provider = provider
        self._timeout_seconds = float(timeout_seconds)
        self._max_in_flight = max_in_flight
        self._in_flight: dict[asyncio.Task[object], _OperationKeys] = {}
        self._closed = False
        self._close_lock = asyncio.Lock()
        self._completed_operations = 0
        self._failed_operations = 0
        self._cancelled_operations = 0
        self._last_terminal_code: str | None = None
        self._partial_event_count = 0

    def snapshot(self) -> RuntimeSnapshot:
        """Return safe counts only; operation keys and content remain private."""
        return RuntimeSnapshot(
            in_flight_count=len(self._in_flight),
            completed_operations=self._completed_operations,
            failed_operations=self._failed_operations,
            cancelled_operations=self._cancelled_operations,
            last_terminal_code=self._last_terminal_code,
            partial_event_count=self._partial_event_count,
        )

    def _record_completed(self) -> None:
        self._completed_operations += 1
        self._last_terminal_code = "completed"
        self._partial_event_count = 0

    def _record_failure(self, failure: ProviderFailure) -> None:
        self._failed_operations += 1
        self._last_terminal_code = failure.code.value
        self._partial_event_count = failure.partial_event_count

    def _record_cancelled(self, partial_event_count: int = 0) -> None:
        self._cancelled_operations += 1
        self._last_terminal_code = ProviderErrorCode.CANCELLED.value
        self._partial_event_count = partial_event_count

    @staticmethod
    def _keys(request: ProviderRequest) -> _OperationKeys:
        return _OperationKeys(
            session_id=request.session_id,
            correlation_id=request.correlation_id,
        )

    @staticmethod
    def _runtime_failure(
        code: ProviderErrorCode,
        *,
        partial_event_count: int = 0,
    ) -> ProviderFailure:
        return ProviderFailure(
            code=code,
            retryable=code in {ProviderErrorCode.TIMEOUT, ProviderErrorCode.UNAVAILABLE},
            partial_event_count=partial_event_count,
        )

    @staticmethod
    def _with_partial_count(
        failure: ProviderFailure,
        partial_event_count: int,
    ) -> ProviderFailure:
        if failure.partial_event_count >= partial_event_count:
            return failure
        return ProviderFailure(
            code=failure.code,
            provider=failure.provider,
            model=failure.model,
            retryable=failure.retryable,
            correlation_id=failure.correlation_id,
            setting_name=failure.setting_name,
            partial_event_count=partial_event_count,
        )

    def _start_operation(
        self,
        operation: Callable[[], Awaitable[_T]],
        keys: _OperationKeys,
    ) -> asyncio.Task[_T]:
        if self._closed:
            failure = self._runtime_failure(ProviderErrorCode.UNAVAILABLE)
            self._record_failure(failure)
            raise failure
        if len(self._in_flight) >= self._max_in_flight:
            failure = self._runtime_failure(ProviderErrorCode.RESOURCE_LIMIT)
            self._record_failure(failure)
            raise failure
        task = asyncio.create_task(operation())
        self._in_flight[task] = keys  # type: ignore[index]
        return task

    def _remove_current_operation(self) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._in_flight.pop(task, None)

    async def _run_generate(self, request: ProviderRequest) -> ProviderResult:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await self._provider.generate(request)
            if not isinstance(result, ProviderResult):
                raise self._runtime_failure(ProviderErrorCode.MALFORMED_RESPONSE)
        except asyncio.CancelledError:
            self._record_cancelled()
            raise
        except TimeoutError as error:
            failure = self._runtime_failure(ProviderErrorCode.TIMEOUT)
            self._record_failure(failure)
            raise failure from error
        except ProviderFailure as failure:
            self._record_failure(failure)
            raise
        except Exception as error:
            failure = self._runtime_failure(ProviderErrorCode.MALFORMED_RESPONSE)
            self._record_failure(failure)
            raise failure from error
        else:
            self._record_completed()
            return result
        finally:
            self._remove_current_operation()

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        """Generate under one absolute deadline and a bounded task registry."""
        task = self._start_operation(lambda: self._run_generate(request), self._keys(request))
        return await task

    async def _close_iterator(self, iterator: AsyncIterator[StreamEvent]) -> None:
        close = getattr(iterator, "aclose", None)
        if close is not None:
            await close()

    async def _produce_stream(
        self,
        request: ProviderRequest,
        queue: asyncio.Queue[QueueItem],
    ) -> None:
        iterator = self._provider.stream(request)
        partial_count = 0
        terminal: Completed | None = None
        failure: ProviderFailure | None = None
        cancelled = False
        try:
            try:
                async with asyncio.timeout(self._timeout_seconds):
                    async for event in iterator:
                        if terminal is not None:
                            raise self._runtime_failure(
                                ProviderErrorCode.MALFORMED_RESPONSE,
                                partial_event_count=partial_count,
                            )
                        if isinstance(event, Completed):
                            terminal = event
                        elif isinstance(event, (TextDelta, ToolCallDelta)):
                            partial_count += 1
                            queue.put_nowait(event)
                        else:
                            raise self._runtime_failure(
                                ProviderErrorCode.MALFORMED_RESPONSE,
                                partial_event_count=partial_count,
                            )
                if terminal is None:
                    raise self._runtime_failure(
                        ProviderErrorCode.MALFORMED_RESPONSE,
                        partial_event_count=partial_count,
                    )
            except asyncio.CancelledError:
                cancelled = True
            except TimeoutError:
                failure = self._runtime_failure(
                    ProviderErrorCode.TIMEOUT,
                    partial_event_count=partial_count,
                )
            except ProviderFailure as provider_failure:
                failure = self._with_partial_count(provider_failure, partial_count)
            except Exception:
                code = (
                    ProviderErrorCode.STREAM_INTERRUPTED
                    if partial_count
                    else ProviderErrorCode.MALFORMED_RESPONSE
                )
                failure = self._runtime_failure(code, partial_event_count=partial_count)
        finally:
            try:
                await self._close_iterator(iterator)
            except asyncio.CancelledError:
                cancelled = True
            except Exception:
                if failure is None and not cancelled:
                    failure = self._runtime_failure(
                        ProviderErrorCode.STREAM_INTERRUPTED,
                        partial_event_count=partial_count,
                    )
            finally:
                self._remove_current_operation()

        if cancelled:
            self._record_cancelled(partial_count)
            queue.put_nowait(_CANCELLED)
            raise asyncio.CancelledError
        if failure is not None:
            self._record_failure(failure)
            queue.put_nowait(_FailureSignal(failure))
            return
        if terminal is None:  # Defensive: all non-terminal paths set a failure above.
            failure = self._runtime_failure(
                ProviderErrorCode.MALFORMED_RESPONSE,
                partial_event_count=partial_count,
            )
            self._record_failure(failure)
            queue.put_nowait(_FailureSignal(failure))
            return
        self._record_completed()
        queue.put_nowait(terminal)
        queue.put_nowait(_END)

    @staticmethod
    async def _cancel_and_await(task: asyncio.Task[object]) -> None:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        """Yield validated deltas and only a proven final adapter completion."""
        queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        producer = self._start_operation(
            lambda: self._produce_stream(request, queue),
            self._keys(request),
        )
        try:
            while True:
                item = await queue.get()
                if item is _END:
                    return
                if item is _CANCELLED:
                    raise asyncio.CancelledError
                if isinstance(item, _FailureSignal):
                    raise item.failure
                if isinstance(item, (TextDelta, ToolCallDelta, Completed)):
                    yield item
                    continue
                raise self._runtime_failure(ProviderErrorCode.MALFORMED_RESPONSE)
        finally:
            await self._cancel_and_await(producer)

    async def clear_session(self, session_id: str) -> None:
        """Cancel matching local work before delegating provider-local cleanup."""
        matching = [
            task for task, keys in tuple(self._in_flight.items()) if keys.matches(session_id)
        ]
        for task in matching:
            task.cancel()
        if matching:
            await asyncio.gather(*matching, return_exceptions=True)
        async with asyncio.timeout(self._timeout_seconds):
            await self._provider.clear_session(session_id)

    async def health(self) -> ProviderHealth:
        """Delegate a bounded health read without generating model content."""
        try:
            async with asyncio.timeout(self._timeout_seconds):
                return await self._provider.health()
        except TimeoutError as error:
            raise self._runtime_failure(ProviderErrorCode.TIMEOUT) from error
        except ProviderFailure:
            raise
        except Exception as error:
            raise self._runtime_failure(ProviderErrorCode.UNAVAILABLE) from error

    async def aclose(self) -> None:
        """Cancel/await all local work and close the selected provider exactly once."""
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            active = tuple(self._in_flight)
            for task in active:
                task.cancel()
            if active:
                await asyncio.gather(*active, return_exceptions=True)
            try:
                await self._provider.aclose()
            except ProviderFailure:
                raise
            except Exception as error:
                raise self._runtime_failure(ProviderErrorCode.UNAVAILABLE) from error
