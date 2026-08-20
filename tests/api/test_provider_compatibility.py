"""Real-route compatibility tests for Aura's selected typed provider runtime."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import aura_backend.main as main
from aura_backend.providers.base import (
    ProviderHealth,
    ProviderHealthStatus,
    ProviderRequest,
    ProviderResult,
    StreamEvent,
    ToolDefinition,
)
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure
from aura_backend.providers.runtime import ProviderRuntime
from aura_backend.providers.tools import (
    ToolCatalog,
    ToolRegistration,
    ToolSource,
)


EXPECTED_RESPONSE_KEYS = {
    "cognitive_state",
    "emotional_state",
    "has_thinking",
    "response",
    "session_id",
    "thinking_content",
    "thinking_metrics",
}
SOURCE_SENTINEL = "raw-provider-source-SENTINEL"
PROMPT_SENTINEL = "private-conversation-SENTINEL"
ANSWER_SENTINEL = "private-answer-SENTINEL"


class _ForbiddenLegacySurface:
    """Fail if orchestration reaches a legacy provider, bridge, or SDK object."""

    def __bool__(self) -> bool:
        raise AssertionError("legacy provider surface was inspected")

    def __getattr__(self, _name: str) -> Any:
        raise AssertionError("legacy provider surface was inspected")


class _SequenceProvider:
    """Selected provider fake that records requests and scripted terminal outcomes."""

    def __init__(self, *outcomes: ProviderResult | ProviderErrorCode | object) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[ProviderRequest] = []
        self.clear_session_calls = 0
        self.close_calls = 0

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ProviderErrorCode):
            try:
                raise RuntimeError(SOURCE_SENTINEL)
            except RuntimeError as error:
                raise ProviderFailure(
                    code=outcome,
                    provider="fake",
                    model="synthetic-model",
                    correlation_id="safe-correlation",
                ) from error
        return outcome  # type: ignore[return-value]

    async def stream(self, _request: ProviderRequest) -> AsyncIterator[StreamEvent]:
        if False:
            yield  # pragma: no cover
        raise AssertionError("non-streaming route must not call stream")

    async def clear_session(self, _session_id: str) -> None:
        self.clear_session_calls += 1

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="fake",
            model="synthetic-model",
            status=ProviderHealthStatus.READY,
        )

    async def aclose(self) -> None:
        self.close_calls += 1


class _BlockingProvider(_SequenceProvider):
    """Selected provider fake whose primary answer waits for cancellation."""

    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("cancelled provider unexpectedly resumed")


@dataclass
class _RouteApplicationRuntime:
    """Small application-runtime fake exposing only the production public seam."""

    provider_runtime: ProviderRuntime
    tool_catalog: ToolCatalog

    async def start(self) -> _RouteApplicationRuntime:
        return self

    async def aclose(self) -> None:
        await self.provider_runtime.aclose()

    def resource(self, name: str) -> object:
        if name != "legacy_services":
            raise LookupError(name)
        return SimpleNamespace(mcp_router=None, tool_catalog=self.tool_catalog)


class _FakeFileSystem:
    async def load_user_profile(self, _user_id: str) -> dict[str, str]:
        return {"name": "Local User"}


class _FakePersistence:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.immediate_calls: list[dict[str, Any]] = []
        self.background_calls = 0

    async def safe_search_conversations(self, **_kwargs: Any) -> list[Any]:
        return []

    async def persist_conversation_exchange_immediate(
        self,
        exchange: Any,
        *,
        update_profile: bool,
        timeout: float,
    ) -> dict[str, Any]:
        self.immediate_calls.append(
            {
                "aura_message": exchange.ai_memory.message,
                "session_ids": (
                    exchange.session_id,
                    exchange.user_memory.session_id,
                    exchange.ai_memory.session_id,
                ),
                "update_profile": update_profile,
                "timeout": timeout,
            }
        )
        return {
            "duration_ms": 0.0,
            "errors": ["synthetic persistence failure"] if self.fail else [],
            "method": "fake_immediate",
            "stored_components": [] if self.fail else ["synthetic"],
            "success": not self.fail,
        }

    async def persist_conversation_exchange(
        self,
        _exchange: Any,
        update_profile: bool = True,
    ) -> dict[str, Any]:
        del update_profile
        self.background_calls += 1
        return {"errors": [], "stored_components": ["synthetic"], "success": True}


def _catalog() -> ToolCatalog:
    return ToolCatalog(
        (
            ToolRegistration(
                definition=ToolDefinition(
                    name="memory.search",
                    description="Search synthetic memory",
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                ),
                source=ToolSource.MCP,
                server="synthetic-server",
            ),
        )
    )


def _runtime(
    provider: _SequenceProvider,
) -> tuple[_RouteApplicationRuntime, ProviderRuntime]:
    selected_runtime = ProviderRuntime(provider, timeout_seconds=1.0)
    return (
        _RouteApplicationRuntime(selected_runtime, _catalog()),
        selected_runtime,
    )


def _install_route_collaborators(
    monkeypatch: pytest.MonkeyPatch,
    persistence: _FakePersistence,
) -> None:
    monkeypatch.setenv("IMMEDIATE_PERSISTENCE_ENABLED", "true")
    monkeypatch.setenv("PERSISTENCE_TIMEOUT", "4.25")
    monkeypatch.setenv("SESSION_RECOVERY_ENABLED", "true")
    monkeypatch.setattr(main, "provider", _ForbiddenLegacySurface())
    monkeypatch.setattr(main, "client", _ForbiddenLegacySurface())
    monkeypatch.setattr(main, "mcp_gemini_bridge", _ForbiddenLegacySurface())
    monkeypatch.setattr(main, "aura_file_system", _FakeFileSystem())
    monkeypatch.setattr(main, "conversation_persistence", persistence)
    monkeypatch.setattr(main, "vector_db", None)
    monkeypatch.setattr(main, "state_manager", None)
    monkeypatch.setattr(main, "aura_internal_tools", None)
    monkeypatch.setattr(main, "memvid_archival", None)
    monkeypatch.setattr(main, "autonomic_system", None)
    monkeypatch.setattr(main, "db_protection_service", None)
    main.active_chat_sessions.clear()


def _payload() -> dict[str, str]:
    return {
        "message": PROMPT_SENTINEL,
        "session_id": "synthetic-session",
        "user_id": "synthetic-user",
    }


def _success_provider() -> _SequenceProvider:
    return _SequenceProvider(
        ProviderResult(content=ANSWER_SENTINEL),
        ProviderResult(content="Normal (Medium)"),
        ProviderResult(content="Curiosity (Low)"),
        ProviderResult(content="Learning"),
    )


def test_selected_runtime_preserves_success_schema_tools_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    persistence = _FakePersistence()
    _install_route_collaborators(monkeypatch, persistence)
    provider = _success_provider()
    application_runtime, selected_runtime = _runtime(provider)
    app = main.create_app(runtime_builder=lambda: application_runtime)

    with caplog.at_level(logging.DEBUG), TestClient(app) as client:
        response = client.post("/conversation", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == EXPECTED_RESPONSE_KEYS
    assert body == {
        "cognitive_state": {
            "description": "General learning and information processing",
            "focus": "Learning",
        },
        "emotional_state": {
            "brainwave": "Beta",
            "intensity": "Low",
            "name": "Curiosity",
            "neurotransmitter": "Dopamine",
        },
        "has_thinking": False,
        "response": ANSWER_SENTINEL,
        "session_id": "synthetic-session",
        "thinking_content": None,
        "thinking_metrics": None,
    }
    assert len(provider.requests) == 4
    primary, *analyses = provider.requests
    assert primary.messages[0].content == PROMPT_SENTINEL
    assert primary.system_instruction
    assert primary.session_id == "synthetic-user_synthetic-session"
    assert primary.tools == _catalog().definitions
    assert all(request.tools == () for request in analyses)
    assert persistence.immediate_calls == [
        {
            "aura_message": ANSWER_SENTINEL,
            "session_ids": (
                "synthetic-session",
                "synthetic-session",
                "synthetic-session",
            ),
            "update_profile": True,
            "timeout": 4.25,
        }
    ]
    assert selected_runtime.snapshot().in_flight_count == 0
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert PROMPT_SENTINEL not in rendered_logs
    assert ANSWER_SENTINEL not in rendered_logs
    assert SOURCE_SENTINEL not in rendered_logs


@pytest.mark.parametrize("code", tuple(ProviderErrorCode))
def test_every_typed_provider_failure_has_identical_safe_fallback(
    code: ProviderErrorCode,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    persistence = _FakePersistence()
    _install_route_collaborators(monkeypatch, persistence)
    provider = _SequenceProvider(code)
    application_runtime, selected_runtime = _runtime(provider)
    app = main.create_app(runtime_builder=lambda: application_runtime)

    with caplog.at_level(logging.DEBUG), TestClient(app) as client:
        response = client.post("/conversation", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == EXPECTED_RESPONSE_KEYS
    assert body["response"]
    assert PROMPT_SENTINEL not in body["response"]
    assert SOURCE_SENTINEL not in response.text
    assert provider.clear_session_calls == 1
    assert persistence.immediate_calls == []
    assert persistence.background_calls == 0
    assert selected_runtime.snapshot().in_flight_count == 0
    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert PROMPT_SENTINEL not in rendered_logs
    assert SOURCE_SENTINEL not in rendered_logs


def test_invalid_provider_success_uses_the_same_safe_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persistence = _FakePersistence()
    _install_route_collaborators(monkeypatch, persistence)
    provider = _SequenceProvider(object())
    application_runtime, selected_runtime = _runtime(provider)
    app = main.create_app(runtime_builder=lambda: application_runtime)

    with TestClient(app) as client:
        response = client.post("/conversation", json=_payload())

    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_RESPONSE_KEYS
    assert provider.clear_session_calls == 1
    assert persistence.immediate_calls == []
    assert selected_runtime.snapshot().in_flight_count == 0


@pytest.mark.asyncio
async def test_request_cancellation_propagates_and_cleans_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persistence = _FakePersistence()
    _install_route_collaborators(monkeypatch, persistence)
    provider = _BlockingProvider()
    application_runtime, selected_runtime = _runtime(provider)
    app = main.create_app(runtime_builder=lambda: application_runtime)
    app.state.runtime = application_runtime
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        pending = asyncio.create_task(client.post("/conversation", json=_payload()))
        await asyncio.wait_for(provider.started.wait(), timeout=0.5)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending

    assert selected_runtime.snapshot().in_flight_count == 0
    assert selected_runtime.snapshot().last_terminal_code == "cancelled"
    assert main.active_chat_sessions == {}
    assert provider.clear_session_calls == 0
    assert persistence.immediate_calls == []
    await application_runtime.aclose()


def test_persistence_degradation_preserves_answer_and_one_background_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persistence = _FakePersistence(fail=True)
    _install_route_collaborators(monkeypatch, persistence)
    provider = _success_provider()
    application_runtime, _selected_runtime = _runtime(provider)
    app = main.create_app(runtime_builder=lambda: application_runtime)

    with TestClient(app) as client:
        response = client.post("/conversation", json=_payload())

    assert response.status_code == 200
    assert response.json()["response"] == ANSWER_SENTINEL
    assert len(persistence.immediate_calls) == 1
    assert persistence.background_calls == 1


def test_route_source_has_no_legacy_provider_or_private_tool_branch() -> None:
    source = inspect.getsource(main.process_conversation)

    assert "app.state.runtime" in source
    assert "generate_response" not in source
    assert "raw_response" not in source
    assert "_tool_mapping" not in source
    assert "mcp_gemini_bridge" not in source
    assert "global provider" not in source
