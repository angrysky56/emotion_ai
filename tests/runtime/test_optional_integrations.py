"""Explicit lifecycle contracts for Aura's four optional runtime stages."""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from typing import Any

import pytest

import aura_backend.main as main
from aura_backend.providers.config import ProviderKind
from aura_backend.runtime import ResourceState, StartedResource
from tests.providers.fakes import ScriptedComplete, ScriptedProvider


@dataclass(frozen=True, slots=True)
class ExtraSmokeResult:
    lane: str
    status: str
    reason: str | None = None


def _mapping(*, provider: str = "ollama", **features: str) -> dict[str, str]:
    values = {
        "ALLOWED_ORIGINS": "http://localhost:5173",
        "AURA_DEFAULT_PROVIDER": provider,
        **features,
    }
    if provider == "gemini":
        values["GEMINI_API_KEY"] = "synthetic-key"
    return values


def _started(name: str, events: list[str], value: object | None = None) -> StartedResource:
    events.append(f"start:{name}")

    async def close() -> None:
        events.append(f"close:{name}")

    return StartedResource(value=value or object(), close=close)


@pytest.mark.asyncio
async def test_all_four_optional_stages_start_only_when_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    provider = ScriptedProvider((ScriptedComplete("synthetic"),))

    async def base() -> StartedResource:
        return _started("base_services", events, main._LegacyRuntimeResources(None))

    async def optional(name: str) -> StartedResource:
        return _started(name, events)

    monkeypatch.setattr(main, "_start_base_resources", base)
    monkeypatch.setattr(main, "_start_mcp_resource", lambda: optional("mcp"))
    monkeypatch.setattr(
        main,
        "_start_gemini_bridge_resource",
        lambda: optional("gemini_bridge"),
    )
    monkeypatch.setattr(main, "_start_memvid_resource", lambda: optional("memvid"))
    monkeypatch.setattr(
        main,
        "_start_autonomic_resource",
        lambda _provider: optional("autonomic"),
    )
    monkeypatch.setattr(
        "aura_backend.providers.factory.ModelProviderFactory.create_provider",
        lambda *_args, **_kwargs: provider,
    )
    monkeypatch.setattr(main, "_composition_environment", lambda: _mapping())

    disabled = main._build_application_runtime()
    await disabled.start()
    assert [status.state for status in disabled.snapshot().resources[:-1]] == [
        ResourceState.READY,
        ResourceState.NOT_CONFIGURED,
        ResourceState.NOT_CONFIGURED,
        ResourceState.NOT_CONFIGURED,
        ResourceState.NOT_CONFIGURED,
    ]
    assert events == ["start:base_services"]
    await disabled.aclose()

    events.clear()
    monkeypatch.setattr(
        main,
        "_composition_environment",
        lambda: _mapping(
            provider="gemini",
            AURA_MCP_ENABLED="true",
            AURA_MEMVID_ENABLED="true",
            AUTONOMIC_ENABLED="true",
        ),
    )
    enabled = main._build_application_runtime()
    await enabled.start()
    assert events == [
        "start:base_services",
        "start:mcp",
        "start:gemini_bridge",
        "start:memvid",
        "start:autonomic",
    ]
    await enabled.aclose()
    assert events[-5:] == [
        "close:autonomic",
        "close:memvid",
        "close:gemini_bridge",
        "close:mcp",
        "close:base_services",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ("mcp", "gemini_bridge", "memvid", "autonomic"))
async def test_enabled_unavailable_optional_stage_is_safe_and_non_blocking(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    provider = ScriptedProvider((ScriptedComplete("synthetic"),))

    async def base() -> StartedResource:
        return _started("base_services", [], main._LegacyRuntimeResources(None))

    async def ok() -> StartedResource:
        return _started("optional", [])

    async def missing(*_args: Any) -> StartedResource:
        raise ModuleNotFoundError("private/module/path-SENTINEL")

    monkeypatch.setattr(main, "_start_base_resources", base)
    monkeypatch.setattr(main, "_start_mcp_resource", missing if stage == "mcp" else ok)
    monkeypatch.setattr(
        main,
        "_start_gemini_bridge_resource",
        missing if stage == "gemini_bridge" else ok,
    )
    monkeypatch.setattr(
        main,
        "_start_memvid_resource",
        missing if stage == "memvid" else ok,
    )
    monkeypatch.setattr(
        main,
        "_start_autonomic_resource",
        missing if stage == "autonomic" else lambda _provider: ok(),
    )
    monkeypatch.setattr(
        "aura_backend.providers.factory.ModelProviderFactory.create_provider",
        lambda *_args, **_kwargs: provider,
    )
    monkeypatch.setattr(
        main,
        "_composition_environment",
        lambda: _mapping(
            provider="gemini",
            AURA_MCP_ENABLED="true",
            AURA_MEMVID_ENABLED="true",
            AUTONOMIC_ENABLED="true",
        ),
    )

    runtime = main._build_application_runtime()
    await runtime.start()
    status = next(item for item in runtime.snapshot().resources if item.name == stage)
    assert runtime.snapshot().ready is True
    assert status.state is ResourceState.FAILED
    assert status.code == "optional_resource_failed"
    assert "SENTINEL" not in repr(runtime.snapshot())
    await runtime.aclose()


@pytest.mark.asyncio
async def test_mcp_with_ollama_never_constructs_gemini_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    provider = ScriptedProvider((ScriptedComplete("synthetic"),))

    async def base() -> StartedResource:
        return _started("base_services", events, main._LegacyRuntimeResources(None))

    async def mcp() -> StartedResource:
        return _started("mcp", events)

    async def forbidden_bridge() -> StartedResource:
        raise AssertionError("Ollama must not construct the Gemini bridge")

    monkeypatch.setattr(main, "_start_base_resources", base)
    monkeypatch.setattr(main, "_start_mcp_resource", mcp)
    monkeypatch.setattr(main, "_start_gemini_bridge_resource", forbidden_bridge)
    monkeypatch.setattr(
        "aura_backend.providers.factory.ModelProviderFactory.create_provider",
        lambda *_args, **_kwargs: provider,
    )
    monkeypatch.setattr(
        main,
        "_composition_environment",
        lambda: _mapping(AURA_MCP_ENABLED="true"),
    )

    runtime = main._build_application_runtime()
    assert runtime.settings.provider.kind is ProviderKind.OLLAMA
    await runtime.start()
    bridge = next(
        item for item in runtime.snapshot().resources if item.name == "gemini_bridge"
    )
    assert bridge.state is ResourceState.NOT_CONFIGURED
    await runtime.aclose()


def _real_extra_smoke(lane: str, modules: tuple[str, ...]) -> ExtraSmokeResult:
    if any(importlib.util.find_spec(module) is None for module in modules):
        return ExtraSmokeResult(
            lane=lane,
            status="not_run",
            reason="declared_extra_not_installed",
        )
    for module in modules:
        importlib.import_module(module)
    return ExtraSmokeResult(lane=lane, status="pass")


@pytest.mark.parametrize(
    ("lane", "modules"),
    (
        ("mcp", ("mcp", "fastmcp")),
        ("provider-gemini", ("google.genai.types",)),
        ("memvid", ("memvid_sdk",)),
        ("autonomic", ("aura_backend.aura_autonomic_system",)),
    ),
)
def test_real_declared_extra_import_smoke_is_truthfully_conditional(
    lane: str,
    modules: tuple[str, ...],
) -> None:
    outcome = _real_extra_smoke(lane, modules)

    assert outcome.status in {"pass", "not_run"}
    if outcome.status == "not_run":
        assert outcome.reason == "declared_extra_not_installed"
    else:
        assert outcome.reason is None
