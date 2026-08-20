"""Offline lifecycle proofs for Aura's explicit application runtime."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from aura_backend.providers.base import ProviderMessage, ProviderRequest, TextDelta
from aura_backend.providers.config import ProviderKind
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.runtime import ProviderRuntime
from aura_backend.runtime import (
    ApplicationRuntime,
    ResourceFactory,
    ResourceState,
    RuntimeSettings,
    RuntimeStartupError,
    StartedResource,
)
from tests.providers.fakes import ScriptedComplete, ScriptedDelta, ScriptedProvider

ProviderBuilder = Callable[[], Awaitable[ProviderRuntime]]


class _EventRecordingProvider(ScriptedProvider):
    def __init__(
        self,
        events: list[str],
        *,
        completion_gate: asyncio.Event | None = None,
    ) -> None:
        super().__init__(
            (ScriptedDelta("partial"), ScriptedComplete("private completion")),
            completion_gate=completion_gate,
        )
        self._events = events

    async def aclose(self) -> None:
        await super().aclose()
        self._events.append("close:provider")


def _provider_factory(
    events: list[str],
    *,
    fail: bool = False,
    provider: ScriptedProvider | None = None,
) -> ProviderBuilder:
    async def start() -> ProviderRuntime:
        events.append("start:provider")
        if fail:
            raise RuntimeError("private provider startup failure")
        selected = provider or _EventRecordingProvider(events)
        return ProviderRuntime(selected, timeout_seconds=1.0)

    return start


def _request() -> ProviderRequest:
    return ProviderRequest(
        messages=(ProviderMessage(role="user", content="private runtime prompt"),),
        session_id="runtime-session",
        correlation_id="runtime-correlation",
    )


def _recording_resource(
    name: str,
    events: list[str],
    *,
    fail: bool = False,
) -> ResourceFactory:
    async def start() -> StartedResource:
        events.append(f"start:{name}")
        if fail:
            raise RuntimeError(f"private failure from {name}")

        async def close() -> None:
            events.append(f"close:{name}")

        return StartedResource(value=object(), close=close)

    return ResourceFactory(name=name, start=start)


def test_settings_default_to_loopback_local_origins_and_ollama() -> None:
    settings = RuntimeSettings.from_mapping({})

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.allowed_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    assert settings.storage_root == Path("aura_data")
    assert settings.preflight_timeout_seconds == 10.0
    assert settings.provider.kind is ProviderKind.OLLAMA


def test_settings_preserve_explicit_lan_origins_provider_and_paths() -> None:
    settings = RuntimeSettings.from_mapping(
        {
            "AURA_HOST": " 192.168.1.25 ",
            "PORT": "8123",
            "ALLOWED_ORIGINS": (
                " http://192.168.1.25:5173,http://localhost:3000,"
                "http://192.168.1.25:5173 "
            ),
            "AURA_DATA_DIRECTORY": "./private-aura-data",
            "AURA_PREFLIGHT_TIMEOUT_SECONDS": "2.5",
            "AURA_DEFAULT_PROVIDER": "ollama",
            "OLLAMA_MODEL": "ornith:latest",
        }
    )

    assert settings.host == "192.168.1.25"
    assert settings.port == 8123
    assert settings.allowed_origins == (
        "http://192.168.1.25:5173",
        "http://localhost:3000",
    )
    assert settings.storage_root == Path("private-aura-data")
    assert settings.preflight_timeout_seconds == 2.5
    assert settings.provider.model == "ornith:latest"


@pytest.mark.parametrize(
    ("mapping", "setting_name"),
    (
        ({"AURA_HOST": "https://not-a-bind-host"}, "AURA_HOST"),
        ({"ALLOWED_ORIGINS": "*"}, "ALLOWED_ORIGINS"),
        ({"ALLOWED_ORIGINS": "javascript:alert(1)"}, "ALLOWED_ORIGINS"),
        ({"PORT": "0"}, "PORT"),
        ({"PORT": "65536"}, "PORT"),
        ({"AURA_DATA_DIRECTORY": "\x00private"}, "AURA_DATA_DIRECTORY"),
        (
            {"AURA_PREFLIGHT_TIMEOUT_SECONDS": "301"},
            "AURA_PREFLIGHT_TIMEOUT_SECONDS",
        ),
        ({"AURA_DEFAULT_PROVIDER": "unknown"}, "AURA_DEFAULT_PROVIDER"),
    ),
)
def test_invalid_settings_fail_before_any_factory_runs(
    mapping: dict[str, str],
    setting_name: str,
) -> None:
    factory_calls = 0

    async def forbidden_factory() -> StartedResource:
        nonlocal factory_calls
        factory_calls += 1
        raise AssertionError("resource construction must not run")

    with pytest.raises((ValueError, RuntimeStartupError)) as captured:
        settings = RuntimeSettings.from_mapping(mapping)
        ApplicationRuntime(
            settings=settings,
            resources=(),
            provider_factory=forbidden_factory,  # type: ignore[arg-type]
        )

    assert setting_name in str(captured.value)
    assert factory_calls == 0


@pytest.mark.asyncio
async def test_resources_start_in_order_and_close_once_in_reverse_order() -> None:
    events: list[str] = []
    resources = tuple(_recording_resource(name, events) for name in ("storage", "tools"))
    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}),
        resources=resources,
        provider_factory=_provider_factory(events),
    )

    await runtime.start()
    assert runtime.snapshot().ready is True
    assert events == ["start:storage", "start:tools", "start:provider"]

    await runtime.aclose()
    await runtime.aclose()

    assert events == [
        "start:storage",
        "start:tools",
        "start:provider",
        "close:provider",
        "close:tools",
        "close:storage",
    ]
    assert all(
        status.state is ResourceState.CLOSED
        for status in runtime.snapshot().resources
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_index", (0, 1, 2))
async def test_every_partial_start_boundary_unwinds_once_in_reverse_order(
    failure_index: int,
) -> None:
    events: list[str] = []
    names = ("storage", "tools", "provider")
    resources = tuple(
        _recording_resource(name, events, fail=index == failure_index)
        for index, name in enumerate(names[:2])
    )
    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}),
        resources=resources,
        provider_factory=_provider_factory(events, fail=failure_index == 2),
    )

    with pytest.raises(RuntimeStartupError) as captured:
        await runtime.start()

    expected_starts = [f"start:{name}" for name in names[: failure_index + 1]]
    expected_closes = [f"close:{name}" for name in reversed(names[:failure_index])]
    assert events == expected_starts + expected_closes
    assert captured.value.code == "required_resource_failed"
    expected_resource = names[failure_index] if failure_index < 2 else "selected_provider"
    assert captured.value.resource == expected_resource
    assert "private failure" not in str(captured.value)
    assert runtime.snapshot().ready is False

    await runtime.aclose()
    assert events == expected_starts + expected_closes


def test_runtime_modules_import_without_external_or_filesystem_initialization() -> None:
    script = """
import asyncio
import pathlib
import socket

def blocked(*args, **kwargs):
    raise AssertionError("runtime import attempted external initialization")

socket.create_connection = blocked
socket.socket.connect = blocked
asyncio.create_subprocess_exec = blocked
asyncio.create_subprocess_shell = blocked
pathlib.Path.mkdir = blocked
pathlib.Path.open = blocked

import aura_backend.runtime.config
import aura_backend.runtime.app
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr[-1000:]


@pytest.mark.asyncio
async def test_provider_runtime_is_required_before_readiness() -> None:
    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}),
        resources=(),
        provider_factory=None,
    )

    with pytest.raises(RuntimeStartupError) as captured:
        await runtime.start()

    assert captured.value.code == "required_provider_missing"
    assert runtime.snapshot().ready is False
    assert runtime.snapshot().resources[-1].name == "selected_provider"
    assert runtime.snapshot().resources[-1].state is ResourceState.FAILED


@pytest.mark.asyncio
async def test_optional_not_configured_is_visible_but_not_a_readiness_failure() -> None:
    events: list[str] = []

    async def optional_absent() -> None:
        events.append("start:optional_cloud")
        return None

    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}),
        resources=(
            ResourceFactory(
                name="optional_cloud",
                start=optional_absent,
                required=False,
            ),
        ),
        provider_factory=_provider_factory(events),
    )

    await runtime.start()

    snapshot = runtime.snapshot()
    assert snapshot.ready is True
    assert snapshot.resources[0].state is ResourceState.NOT_CONFIGURED
    assert snapshot.resources[-1].state is ResourceState.READY
    await runtime.aclose()


@pytest.mark.asyncio
async def test_shutdown_cancels_provider_before_remaining_resources_close() -> None:
    events: list[str] = []
    completion_gate = asyncio.Event()
    provider = _EventRecordingProvider(events, completion_gate=completion_gate)
    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}),
        resources=(_recording_resource("storage", events),),
        provider_factory=_provider_factory(events, provider=provider),
    )
    await runtime.start()
    selected_runtime = runtime.provider_runtime
    stream = selected_runtime.stream(_request())
    assert await anext(stream) == TextDelta(text="partial")
    pending_terminal = asyncio.create_task(anext(stream))
    await provider.completion_waiting.wait()

    await asyncio.wait_for(runtime.aclose(), timeout=0.5)

    with pytest.raises(asyncio.CancelledError):
        await pending_terminal
    assert pending_terminal.done()
    assert selected_runtime.snapshot().in_flight_count == 0
    assert (
        selected_runtime.snapshot().last_terminal_code
        == ProviderErrorCode.CANCELLED.value
    )
    assert provider.recorder.cleanup_count == 1
    assert provider.recorder.close_calls == 1
    assert "completed" not in provider.recorder.terminal_codes
    assert events[-2:] == ["close:provider", "close:storage"]

    with pytest.raises(ProviderFailure) as rejected:
        await selected_runtime.generate(_request())
    assert rejected.value.code is ProviderErrorCode.UNAVAILABLE
