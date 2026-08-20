"""Offline autonomic tests for provider injection and truthful disablement."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys

import pytest

from aura_backend.aura_autonomic_system import (
    AutonomicProcessor,
    AutonomicState,
    AutonomicTask,
    TaskPriority,
    TaskStatus,
    TaskType,
    initialize_autonomic_system,
    shutdown_autonomic_system,
)
from aura_backend.providers.errors import ProviderErrorCode
from aura_backend.providers.runtime import ProviderRuntime
from tests.providers.fakes import (
    ScriptedComplete,
    ScriptedFailure,
    ScriptedProvider,
)


def _task() -> AutonomicTask:
    return AutonomicTask(
        task_id="safe-task-id",
        task_type=TaskType.BACKGROUND_PROCESSING,
        priority=TaskPriority.MEDIUM,
        description="prompt-SENTINEL autonomic work",
        payload={"private": "payload-SENTINEL"},
        user_id="user-SENTINEL",
        session_id="session-SENTINEL",
    )


def _runtime(*steps: object, timeout: float = 1.0) -> tuple[ProviderRuntime, ScriptedProvider]:
    provider = ScriptedProvider(steps)  # type: ignore[arg-type]
    return ProviderRuntime(provider, timeout_seconds=timeout), provider


def test_autonomic_module_import_does_not_import_google() -> None:
    probe = """
import sys
import aura_backend.aura_autonomic_system

loaded = sorted(name for name in sys.modules if name == 'google' or name.startswith('google.'))
if loaded:
    raise SystemExit(f'google modules loaded: {loaded}')
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


@pytest.mark.asyncio
async def test_initialization_without_runtime_is_disabled_and_starts_no_worker() -> None:
    system = await initialize_autonomic_system(provider_runtime=None)
    try:
        status = system.get_system_status()
        assert status["status"] == AutonomicState.DISABLED.value
        assert status["disabled_reason"] == "not_configured"
        assert status["running"] is False
        assert system._worker_task is None
    finally:
        await shutdown_autonomic_system()


@pytest.mark.asyncio
async def test_injected_runtime_generates_typed_success_without_provider_branching() -> None:
    runtime, provider = _runtime(ScriptedComplete("result-SENTINEL"))
    processor = AutonomicProcessor(provider_runtime=runtime)

    completed = await processor.execute_task(_task())

    assert completed.status is TaskStatus.COMPLETED
    assert completed.result == {
        "general_result": "result-SENTINEL",
        "task_type": "general_processing",
    }
    assert completed.error is None
    assert provider.recorder.generate_calls == 1
    assert runtime.snapshot().completed_operations == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        (ProviderErrorCode.UNAVAILABLE, TaskStatus.FAILED),
        (ProviderErrorCode.RESOURCE_LIMIT, TaskStatus.FAILED),
        (ProviderErrorCode.TIMEOUT, TaskStatus.TIMEOUT),
    ],
)
async def test_typed_provider_failures_remain_non_successful(
    code: ProviderErrorCode,
    expected_status: TaskStatus,
) -> None:
    runtime, _ = _runtime(ScriptedFailure(code))
    processor = AutonomicProcessor(provider_runtime=runtime)

    completed = await processor.execute_task(_task())

    assert completed.status is expected_status
    assert completed.result is None
    assert completed.error == code.value
    assert processor.get_stats()["tasks_failed"] == 1
    assert runtime.snapshot().completed_operations == 0


@pytest.mark.asyncio
async def test_cancellation_is_recorded_as_failure_and_propagates() -> None:
    completion_gate = asyncio.Event()
    provider = ScriptedProvider(
        (ScriptedComplete("never"),),
        completion_gate=completion_gate,
    )
    runtime = ProviderRuntime(provider, timeout_seconds=10.0)
    processor = AutonomicProcessor(provider_runtime=runtime)
    autonomic_task = _task()
    operation = asyncio.create_task(processor.execute_task(autonomic_task))
    await provider.completion_waiting.wait()

    operation.cancel()
    with pytest.raises(asyncio.CancelledError):
        await operation

    assert autonomic_task.status is TaskStatus.FAILED
    assert autonomic_task.error == ProviderErrorCode.CANCELLED.value
    assert processor.get_stats()["tasks_failed"] == 1
    assert runtime.snapshot().cancelled_operations == 1


@pytest.mark.asyncio
async def test_default_logs_and_status_exclude_content_and_source_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runtime, _ = _runtime(ScriptedComplete("result-SENTINEL"))
    system = await initialize_autonomic_system(provider_runtime=runtime)
    try:
        with caplog.at_level(logging.DEBUG):
            completed = await system.processor.execute_task(_task())
            status = system.get_system_status()

        assert completed.status is TaskStatus.COMPLETED
        diagnostics = f"{caplog.text} {status!r}"
        for sentinel in (
            "prompt-SENTINEL",
            "payload-SENTINEL",
            "result-SENTINEL",
            "user-SENTINEL",
            "session-SENTINEL",
            "credential-SENTINEL",
        ):
            assert sentinel not in diagnostics
    finally:
        await shutdown_autonomic_system()
