"""Explicit lifecycle contracts for Aura's four optional runtime stages."""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from typing import Any

import pytest

import aura_backend.main as main
from aura_backend.providers.config import ProviderKind
from aura_backend.providers.runtime import ProviderRuntime
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


def _started(
    name: str, events: list[str], value: object | None = None
) -> StartedResource:
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


def _spec_exists(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _real_extra_smoke(lane: str, modules: tuple[str, ...]) -> ExtraSmokeResult:
    if any(not _spec_exists(module) for module in modules):
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


class _NoIOClient:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.start_count = 0
        self.stop_count = 0
        self.connection_status: dict[str, bool] = {}
        self.tool_registry: dict[str, object] = {}

    async def start(self) -> None:
        self.start_count += 1

    async def stop(self) -> None:
        self.stop_count += 1

    async def list_all_tools(self) -> dict[str, dict[str, Any]]:
        return {
            "synthetic.tool": {
                "connected": True,
                "description": "Synthetic definition",
                "input_schema": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
                "server": "synthetic",
            }
        }

    async def call_tool(self, *_args: Any, **_kwargs: Any) -> object:
        raise AssertionError("smoke must not execute an MCP tool")


class _NoIOIntegration:
    def __init__(self, client: _NoIOClient) -> None:
        self.client = client

    async def get_available_capabilities(self) -> dict[str, Any]:
        return {
            "available_tools": 1,
            "connected_servers": 0,
            "tools_by_server": {},
            "total_servers": 0,
        }


class _NoIOInternalTools:
    def get_tool_list(self) -> list[dict[str, Any]]:
        return []

    def get_tool_definitions(self) -> dict[str, dict[str, Any]]:
        return {}

    async def execute_tool(self, *_args: Any, **_kwargs: Any) -> object:
        raise AssertionError("smoke must not execute an internal tool")


@pytest.mark.asyncio
async def test_real_mcp_and_gemini_seams_use_no_io_collaborators() -> None:
    if not _spec_exists("mcp") or not _spec_exists("fastmcp"):
        pytest.skip("not_run: declared_extra_not_installed")
    if not _spec_exists("google.genai.types"):
        pytest.skip("not_run: declared_extra_not_installed")

    importlib.import_module("mcp")
    importlib.import_module("fastmcp")
    types_module = importlib.import_module("google.genai.types")
    from aura_backend import mcp_system

    client = _NoIOClient()
    await mcp_system.shutdown_gemini_bridge()
    await mcp_system.shutdown_mcp_system()
    try:
        status = await mcp_system.initialize_mcp_system(
            _NoIOInternalTools(),
            client_factory=lambda **_kwargs: client,
            integration_factory=_NoIOIntegration,
        )
        bridge = await mcp_system.initialize_gemini_bridge()

        assert status["status"] == "success"
        assert client.start_count == 1
        assert len(bridge.get_available_functions()) == 1
        assert bridge._gemini_functions
        assert isinstance(bridge._gemini_functions[0], types_module.Tool)
    finally:
        await mcp_system.shutdown_gemini_bridge()
        await mcp_system.shutdown_mcp_system()
        await mcp_system.shutdown_mcp_system()
    assert client.stop_count == 1


@pytest.mark.asyncio
async def test_real_memvid_import_enters_injected_no_storage_facade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not _spec_exists("memvid_sdk"):
        pytest.skip("not_run: declared_extra_not_installed")
    importlib.import_module("memvid_sdk")
    module = importlib.import_module("aura_backend.memvid_archival_service")
    events: list[str] = []

    class NoStorageFacade:
        def __init__(self) -> None:
            events.append("start")

        async def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(module, "MemvidArchivalService", NoStorageFacade)
    started = await main._start_memvid_resource()
    await started.close()
    await started.close()

    assert events == ["start", "close"]


@pytest.mark.asyncio
async def test_real_autonomic_module_starts_and_closes_without_model_call() -> None:
    importlib.import_module("aura_backend.aura_autonomic_system")
    provider = ScriptedProvider((ScriptedComplete("must-not-be-called"),))
    provider_runtime = ProviderRuntime(provider, timeout_seconds=1.0)

    started = await main._start_autonomic_resource(provider_runtime)
    assert started.value._running is True
    await started.close()
    await started.close()
    await provider_runtime.aclose()

    assert provider.recorder.generate_calls == 0
    assert provider.recorder.close_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ("mcp", "gemini_bridge", "memvid", "autonomic"))
async def test_partial_optional_stage_start_runs_registered_cleanup_once(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    events: list[str] = []

    if stage == "mcp":
        if not _spec_exists("mcp") or not _spec_exists("fastmcp"):
            pytest.skip("not_run: declared_extra_not_installed")
        mcp_module = importlib.import_module("aura_backend.mcp_system")
        integration_module = importlib.import_module("aura_backend.mcp_integration")

        async def fail_mcp(*_args: Any, **_kwargs: Any) -> None:
            events.append("start")
            raise RuntimeError("private-SENTINEL")

        async def close_mcp() -> None:
            events.append("close:mcp")

        async def close_integration() -> None:
            events.append("close:integration")

        monkeypatch.setattr(mcp_module, "initialize_mcp_system", fail_mcp)
        monkeypatch.setattr(mcp_module, "shutdown_mcp_system", close_mcp)
        monkeypatch.setattr(
            integration_module, "shutdown_mcp_client", close_integration
        )
        operation = main._start_mcp_resource()
    elif stage == "gemini_bridge":
        if not _spec_exists("google.genai.types"):
            pytest.skip("not_run: declared_extra_not_installed")
        mcp_module = importlib.import_module("aura_backend.mcp_system")

        async def fail_bridge() -> None:
            events.append("start")
            raise RuntimeError("private-SENTINEL")

        async def close_bridge() -> None:
            events.append("close")

        monkeypatch.setattr(mcp_module, "initialize_gemini_bridge", fail_bridge)
        monkeypatch.setattr(mcp_module, "shutdown_gemini_bridge", close_bridge)
        operation = main._start_gemini_bridge_resource()
    elif stage == "memvid":
        if not _spec_exists("memvid_sdk"):
            pytest.skip("not_run: declared_extra_not_installed")
        module = importlib.import_module("aura_backend.memvid_archival_service")

        class PartialFacade:
            def __init__(self) -> None:
                events.append("start")
                raise RuntimeError("private-SENTINEL")

            async def close(self) -> None:
                events.append("close")

        monkeypatch.setattr(module, "MemvidArchivalService", PartialFacade)
        operation = main._start_memvid_resource()
    else:
        module = importlib.import_module("aura_backend.aura_autonomic_system")

        async def fail_autonomic(**_kwargs: Any) -> None:
            events.append("start")
            raise RuntimeError("private-SENTINEL")

        async def close_autonomic() -> None:
            events.append("close")

        monkeypatch.setattr(module, "initialize_autonomic_system", fail_autonomic)
        monkeypatch.setattr(module, "shutdown_autonomic_system", close_autonomic)
        operation = main._start_autonomic_resource(object())

    with pytest.raises(RuntimeError, match="private-SENTINEL"):
        await operation
    assert events.count("start") == 1
    assert sum(event.startswith("close") for event in events) == (
        2 if stage == "mcp" else 1
    )
