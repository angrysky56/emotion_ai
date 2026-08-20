"""Integration tests for Aura's import-safe FastAPI lifespan ownership."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aura_backend.main import app as compatibility_app
from aura_backend.main import create_app


class _RecordingRuntime:
    """Small structural fake with exact lifecycle evidence."""

    def __init__(self, *, fail_start: bool = False) -> None:
        self.fail_start = fail_start
        self.events: list[str] = []
        self.start_count = 0
        self.close_count = 0

    async def start(self) -> _RecordingRuntime:
        self.start_count += 1
        self.events.append("start")
        if self.fail_start:
            self.events.extend(("start:storage", "start:tools", "fail:provider"))
            raise RuntimeError("private startup detail")
        return self

    async def aclose(self) -> None:
        self.close_count += 1
        if self.fail_start:
            self.events.extend(("close:tools", "close:storage"))
        self.events.append("close")


def _builder(runtime: _RecordingRuntime, calls: list[str]) -> Callable[[], Any]:
    def build() -> _RecordingRuntime:
        calls.append("build")
        return runtime

    return build


def test_create_app_and_plain_test_client_do_not_construct_runtime() -> None:
    """Factory creation and non-context requests intentionally skip lifespan."""
    runtime = _RecordingRuntime()
    builder_calls: list[str] = []
    created = create_app(runtime_builder=_builder(runtime, builder_calls))

    assert builder_calls == []
    assert created.state.runtime is None
    assert created.state.runtime_builder is not None

    client = TestClient(created)
    assert client.get("/").status_code == 200
    assert builder_calls == []
    assert runtime.start_count == 0
    assert runtime.close_count == 0


def test_context_managed_client_owns_exactly_one_runtime() -> None:
    """Lifespan builds, starts, publishes, and closes one runtime exactly once."""
    runtime = _RecordingRuntime()
    builder_calls: list[str] = []
    created = create_app(runtime_builder=_builder(runtime, builder_calls))

    with TestClient(created) as client:
        assert client.get("/").status_code == 200
        assert builder_calls == ["build"]
        assert runtime.start_count == 1
        assert runtime.close_count == 0
        assert created.state.runtime is runtime

    assert runtime.events == ["start", "close"]
    assert runtime.close_count == 1
    assert created.state.runtime is None


def test_failed_startup_is_not_published_and_unwinds_once_in_reverse_order() -> None:
    """A partial startup remains unready while lifespan guarantees one close."""
    runtime = _RecordingRuntime(fail_start=True)
    created = create_app(runtime_builder=lambda: runtime)

    with pytest.raises(RuntimeError, match="private startup detail"):
        with TestClient(created):
            raise AssertionError("failed startup must not yield a client")

    assert runtime.events == [
        "start",
        "start:storage",
        "start:tools",
        "fail:provider",
        "close:tools",
        "close:storage",
        "close",
    ]
    assert runtime.close_count == 1
    assert created.state.runtime is None


def test_factory_keeps_explicit_local_cors_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local browser boundary remains explicit and credential-free."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")
    created = create_app(runtime_builder=lambda: _RecordingRuntime())
    client = TestClient(created)

    response = client.options(
        "/conversation",
        headers={
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Method": "POST",
            "Origin": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert "access-control-allow-credentials" not in response.headers


def test_module_level_app_remains_factory_compatible_and_routes_are_unique() -> None:
    """Existing import strings retain one copy of each main route."""
    assert compatibility_app.state.runtime is None
    route_keys = [
        (route.path, tuple(sorted(getattr(route, "methods", ()) or ())))
        for route in compatibility_app.routes
    ]
    assert len(route_keys) == len(set(route_keys))
    assert ("/conversation", ("POST",)) in route_keys
