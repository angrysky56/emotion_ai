"""Bounded child-process probe for Aura's production FastAPI application.

The parent-side :func:`run_probe` function is safe to import in pytest.  The
heavy ``aura_backend.main`` module is imported only after this file is invoked
as a child process, from a disposable working directory with fake production
collaborators installed.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROBE_PATH = Path(__file__).resolve()
DEFAULT_ORIGIN = "http://localhost:5173"
UNTRUSTED_ORIGIN = "https://attacker.invalid"

_DATA_ROOTS = (
    "aura_chroma_db",
    "aura_data",
    "auto_backups",
    "aura_backend/aura_chroma_db",
    "aura_backend/aura_data",
    "aura_backend/auto_backups",
    "aura_backend/chromadb_backups",
    "aura_backend/test_chroma_db",
)
_REQUIRED_RESULT_KEYS = {"complete", "scenario", "status"}
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class ProbeFailure(AssertionError):
    """A child probe failed to produce complete, trustworthy evidence."""


def _data_root_snapshot() -> tuple[tuple[str, int, int], ...]:
    """Capture non-content metadata that changes if known data roots are written."""
    snapshot: list[tuple[str, int, int]] = []
    for relative_root in _DATA_ROOTS:
        root = REPOSITORY_ROOT / relative_root
        if not root.exists():
            continue
        for path in (root, *sorted(root.rglob("*"))):
            stat = path.lstat()
            snapshot.append(
                (str(path.relative_to(REPOSITORY_ROOT)), stat.st_size, stat.st_mtime_ns)
            )
    return tuple(snapshot)


def _sanitized_environment() -> dict[str, str]:
    """Return only deterministic variables required to start the child Python."""
    return {
        "ALLOWED_ORIGINS": DEFAULT_ORIGIN,
        "AUTONOMIC_ENABLED": "false",
        "EMERGENCY_PERSISTENCE_RETRIES": "0",
        "IMMEDIATE_PERSISTENCE_ENABLED": "true",
        "PATH": os.environ.get("PATH", ""),
        "PERSISTENCE_TIMEOUT": "4.25",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(REPOSITORY_ROOT),
    }


def _failure_detail(completed: subprocess.CompletedProcess[str]) -> str:
    """Keep child diagnostics bounded and visible only when the probe fails."""
    stderr = completed.stderr.strip()
    return f"; child stderr: {stderr[-2000:]}" if stderr else ""


def run_probe(scenario: str, *, timeout: float = 8.0) -> dict[str, Any]:
    """Run one child scenario or raise a distinct failure for invalid evidence."""
    before = _data_root_snapshot()
    with tempfile.TemporaryDirectory(prefix="aura-main-probe-") as temporary_cwd:
        try:
            completed = subprocess.run(
                [sys.executable, str(PROBE_PATH), "--child", scenario],
                cwd=temporary_cwd,
                env=_sanitized_environment(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ProbeFailure(
                f"Probe scenario {scenario!r} timed out after {timeout:.2f}s"
            ) from error

    if completed.returncode != 0:
        raise ProbeFailure(
            f"Probe scenario {scenario!r} exited with status {completed.returncode}"
            f"{_failure_detail(completed)}"
        )

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ProbeFailure(
            f"Probe scenario {scenario!r} returned invalid JSON"
            f"{_failure_detail(completed)}"
        ) from error

    if not isinstance(result, dict) or not _REQUIRED_RESULT_KEYS.issubset(result):
        raise ProbeFailure(f"Probe scenario {scenario!r} returned an incomplete result")
    if result["complete"] is not True or result["status"] != "ok":
        raise ProbeFailure(f"Probe scenario {scenario!r} reported failure: {result!r}")

    result["repository_data_roots_unchanged"] = before == _data_root_snapshot()
    if not result["repository_data_roots_unchanged"]:
        raise ProbeFailure(f"Probe scenario {scenario!r} modified repository data roots")
    return result


def _fake_module(name: str, **attributes: Any) -> None:
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module


def _install_import_fakes(initializer_calls: list[str]) -> None:
    """Replace stateful composition-root dependencies before importing main."""
    from fastapi import APIRouter

    class PassiveObject:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class FakeEmbedding:
        def encode_single(self, _text: str) -> list[float]:
            return [0.0]

    class FakeFactory:
        @staticmethod
        def get_provider(*_args: Any, **_kwargs: Any) -> Any:
            initializer_calls.append("provider")
            raise AssertionError("production provider initialization is forbidden")

    def forbidden_protection_service() -> Any:
        initializer_calls.append("database_protection")
        raise AssertionError("production database protection is forbidden")

    async def forbidden_autonomic_start(*_args: Any, **_kwargs: Any) -> Any:
        initializer_calls.append("autonomic")
        raise AssertionError("production autonomic startup is forbidden")

    async def no_op_async(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def fake_mcp_execute(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"status": "unused"}

    _fake_module(
        "aura_backend.aura_autonomic_system",
        AutonomicNervousSystem=PassiveObject,
        initialize_autonomic_system=forbidden_autonomic_start,
        shutdown_autonomic_system=no_op_async,
    )
    _fake_module("aura_backend.aura_internal_tools", AuraInternalTools=PassiveObject)
    _fake_module(
        "aura_backend.conversation_persistence_service",
        ConversationExchange=PassiveObject,
        ConversationPersistenceService=PassiveObject,
        PersistenceHealthCheck=PassiveObject,
    )
    _fake_module(
        "aura_backend.database_protection",
        DatabaseProtectionService=PassiveObject,
        get_protection_service=forbidden_protection_service,
    )
    _fake_module(
        "aura_backend.mcp_integration",
        execute_mcp_tool=fake_mcp_execute,
        mcp_router=APIRouter(),
    )
    _fake_module(
        "aura_backend.mcp_system",
        get_all_available_tools=lambda: [],
        get_mcp_bridge=lambda: None,
        get_mcp_client=lambda: None,
        get_mcp_status=lambda: {"status": "disabled"},
        initialize_mcp_system=forbidden_autonomic_start,
        shutdown_mcp_system=no_op_async,
    )
    _fake_module("aura_backend.mcp_to_gemini_bridge", MCPGeminiBridge=PassiveObject)
    _fake_module("aura_backend.memvid_archival_service", MemvidArchivalService=PassiveObject)
    _fake_module("aura_backend.providers.factory", ModelProviderFactory=FakeFactory)
    _fake_module("aura_backend.robust_vector_db", RobustAuraVectorDB=PassiveObject)
    _fake_module(
        "aura_backend.shared_embedding_service",
        get_embedding_service=lambda: FakeEmbedding(),
    )
    _fake_module("aura_backend.thinking_processor", ThinkingProcessor=PassiveObject)


def _normalize(value: Any) -> Any:
    """Remove volatile UUID and timestamp values from committed expectations."""
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str) and _UUID.fullmatch(value):
        return "<uuid>"
    if isinstance(value, str) and _TIMESTAMP.match(value):
        return "<timestamp>"
    return value


def _install_route_fakes(main: Any, scenario: str) -> dict[str, Any]:
    calls: dict[str, Any] = {
        "background": 0,
        "filesystem_writes": 0,
        "persistence": 0,
        "persistence_evidence": None,
        "provider": 0,
    }

    class FakeProvider:
        async def generate_response(self, *_args: Any, **_kwargs: Any) -> Any:
            from aura_backend.providers.base import ProviderResponse

            calls["provider"] += 1
            return ProviderResponse(content="Synthetic local reply.")

        async def clear_session(self, _session_id: str) -> None:
            return None

    class FakeFileSystem:
        async def load_user_profile(self, _user_id: str) -> dict[str, str]:
            return {"name": "Local Probe"}

        async def save_user_profile(self, *_args: Any, **_kwargs: Any) -> None:
            calls["filesystem_writes"] += 1
            raise AssertionError("conversation probe must not write a profile file")

        async def export_conversation_history(
            self, *_args: Any, **_kwargs: Any
        ) -> None:
            calls["filesystem_writes"] += 1
            raise AssertionError("conversation probe must not write an export file")

    class FakePersistence:
        async def safe_search_conversations(self, **_kwargs: Any) -> list[Any]:
            return []

        async def persist_conversation_exchange_immediate(
            self,
            exchange: Any,
            *,
            update_profile: bool,
            timeout: float,
        ) -> dict[str, Any]:
            calls["persistence"] += 1
            failed = scenario == "persistence_failure"
            result = {
                "duration_ms": 0.0,
                "errors": ["synthetic persistence failure"] if failed else [],
                "method": (
                    "fake_immediate_failure" if failed else "fake_immediate"
                ),
                "stored_components": [] if failed else ["synthetic"],
                "success": not failed,
            }
            session_values = (
                exchange.session_id,
                exchange.user_memory.session_id,
                exchange.ai_memory.session_id,
            )
            calls["persistence_evidence"] = {
                "exchange": {
                    "aura_message_nonempty": bool(exchange.ai_memory.message),
                    "aura_sender": exchange.ai_memory.sender,
                    "aura_user_matches": exchange.ai_memory.user_id == "probe-user",
                    "session_ids": [
                        "<session>"
                        if value == "probe-session"
                        else "<unexpected-session>"
                        for value in session_values
                    ],
                    "user_message_matches": (
                        exchange.user_memory.message
                        == "A deterministic local boundary probe"
                    ),
                    "user_sender": exchange.user_memory.sender,
                    "user_user_matches": exchange.user_memory.user_id == "probe-user",
                },
                "method": "persist_conversation_exchange_immediate",
                "result": {
                    "error_count": len(result["errors"]),
                    "method": result["method"],
                    "stored_component_count": len(result["stored_components"]),
                    "success": result["success"],
                },
                "timeout": timeout,
                "update_profile": update_profile,
            }
            return result

        async def persist_conversation_exchange(
            self, _exchange: Any, update_profile: bool = True
        ) -> dict[str, Any]:
            calls["background"] += 1
            return {
                "errors": ["synthetic background persistence failure"],
                "stored_components": [],
                "success": False,
                "update_profile": update_profile,
            }

    async def fake_user_emotion(**_kwargs: Any) -> Any:
        return main.EmotionalStateData(
            name="Calm",
            formula="synthetic",
            components={"ESA": "Medium"},
            ntk_layer="synthetic",
            brainwave="Alpha",
            neurotransmitter="Serotonin",
            description="Synthetic probe state",
        )

    async def fake_aura_emotion(**_kwargs: Any) -> Any:
        return await fake_user_emotion()

    async def fake_cognitive_focus(**_kwargs: Any) -> Any:
        return main.CognitiveState(
            focus=main.AsekeComponent.LEARNING,
            description="Synthetic local processing",
            context="ASGI probe",
        )

    main.provider = FakeProvider()
    main.aura_file_system = FakeFileSystem()
    main.conversation_persistence = FakePersistence()
    main.vector_db = None
    main.state_manager = None
    main.aura_internal_tools = None
    main.memvid_archival = None
    main.mcp_gemini_bridge = None
    main.autonomic_system = None
    main.db_protection_service = None
    main.active_chat_sessions.clear()
    main.detect_user_emotion = fake_user_emotion
    main.detect_aura_emotion = fake_aura_emotion
    main.detect_aura_cognitive_focus = fake_cognitive_focus
    return calls


def _request_result(response: Any, calls: dict[str, Any]) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    body = response.json() if content_type.startswith("application/json") else response.text
    return {
        "body": _normalize(body),
        "headers": {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower().startswith("access-control-")
        },
        "provider_calls": calls["provider"],
        "persistence_calls": calls["persistence"],
        "status_code": response.status_code,
    }


def _execute_scenario(scenario: str) -> dict[str, Any]:
    if scenario == "_hang":
        time.sleep(60.0)
    if scenario == "_crash":
        raise RuntimeError("deliberate probe crash")
    if scenario == "_malformed":
        return {"raw_output": "not-json"}
    if scenario == "_partial":
        return {"scenario": scenario, "status": "ok"}

    initializer_calls: list[str] = []
    if scenario == "wildcard_origin":
        os.environ["ALLOWED_ORIGINS"] = "*"
    _install_import_fakes(initializer_calls)

    if scenario == "wildcard_origin":
        try:
            import aura_backend.main  # noqa: F401
        except ValueError as error:
            return {
                "complete": True,
                "error": str(error),
                "production_initializers_called": initializer_calls,
                "scenario": scenario,
                "status": "ok",
                "wildcard_rejected": True,
            }
        raise AssertionError("wildcard origin unexpectedly imported the app")

    import aura_backend.main as main
    from fastapi.testclient import TestClient

    calls = _install_route_fakes(main, scenario)
    client = TestClient(main.app, raise_server_exceptions=True)

    if scenario == "probe":
        response = client.get("/")
        scenario_result: dict[str, Any] = {
            "app_module": main.__name__,
            "lifespan_started": False,
            "production_initializers_called": initializer_calls,
            "root_status_code": response.status_code,
        }
    elif scenario in {"preflight_allowed", "preflight_denied"}:
        origin = DEFAULT_ORIGIN if scenario == "preflight_allowed" else UNTRUSTED_ORIGIN
        response = client.options(
            "/conversation",
            headers={
                "Access-Control-Request-Headers": "content-type",
                "Access-Control-Request-Method": "POST",
                "Origin": origin,
            },
        )
        scenario_result = _request_result(response, calls)
    else:
        payload = {
            "message": "A deterministic local boundary probe",
            "session_id": "probe-session",
            "user_id": "probe-user",
        }
        origin = (
            DEFAULT_ORIGIN
            if scenario
            in {"conversation_json", "persistence_failure", "persistence_success"}
            else UNTRUSTED_ORIGIN
        )
        headers = {"Origin": origin}
        if scenario in {
            "conversation_json",
            "persistence_failure",
            "persistence_success",
        }:
            response = client.post("/conversation", json=payload, headers=headers)
        elif scenario == "conversation_missing_content_type":
            response = client.post(
                "/conversation", content=json.dumps(payload), headers=headers
            )
        elif scenario == "conversation_text_plain":
            response = client.post(
                "/conversation",
                content=json.dumps(payload),
                headers={**headers, "Content-Type": "text/plain"},
            )
        else:
            raise ValueError(f"Unknown probe scenario: {scenario}")
        scenario_result = _request_result(response, calls)
        scenario_result["credential_headers_sent"] = []
        if scenario in {"persistence_failure", "persistence_success"}:
            response_body = scenario_result.pop("body")
            persistence_evidence = calls["persistence_evidence"]
            if persistence_evidence is None:
                raise AssertionError("persistence scenario did not reach the fake service")
            scenario_result["filesystem_write_attempts"] = calls[
                "filesystem_writes"
            ]
            scenario_result["persistence"] = {
                "background_calls": calls["background"],
                "immediate_calls": calls["persistence"],
                **persistence_evidence,
            }
            scenario_result["visible_provider_answer_preserved"] = (
                isinstance(response_body, dict)
                and response_body.get("response") == "Synthetic local reply."
            )

    return {
        "complete": True,
        "lifespan_started": False,
        "production_initializers_called": initializer_calls,
        "scenario": scenario,
        "status": "ok",
        **scenario_result,
    }


def _child_main(scenario: str) -> None:
    if scenario == "_malformed":
        print("not-json")
        return
    if scenario == "_partial":
        print(json.dumps({"scenario": scenario, "status": "ok"}))
        return

    swallowed_stdout = io.StringIO()
    with contextlib.redirect_stdout(swallowed_stdout):
        result = _execute_scenario(scenario)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--child":
        raise SystemExit("usage: main_subprocess_probe.py --child SCENARIO")
    _child_main(sys.argv[2])
