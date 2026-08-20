"""Offline lifecycle proofs for Aura's explicit application runtime."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aura_backend.providers.config import ProviderKind
from aura_backend.runtime import (
    ApplicationRuntime,
    ResourceFactory,
    ResourceState,
    RuntimeSettings,
    RuntimeStartupError,
    StartedResource,
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
            resources=(ResourceFactory(name="forbidden", start=forbidden_factory),),
        )

    assert setting_name in str(captured.value)
    assert factory_calls == 0


@pytest.mark.asyncio
async def test_resources_start_in_order_and_close_once_in_reverse_order() -> None:
    events: list[str] = []
    resources = tuple(
        _recording_resource(name, events) for name in ("storage", "tools", "provider")
    )
    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}), resources=resources
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
        for index, name in enumerate(names)
    )
    runtime = ApplicationRuntime(
        settings=RuntimeSettings.from_mapping({}), resources=resources
    )

    with pytest.raises(RuntimeStartupError) as captured:
        await runtime.start()

    expected_starts = [f"start:{name}" for name in names[: failure_index + 1]]
    expected_closes = [f"close:{name}" for name in reversed(names[:failure_index])]
    assert events == expected_starts + expected_closes
    assert captured.value.code == "required_resource_failed"
    assert captured.value.resource == names[failure_index]
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
