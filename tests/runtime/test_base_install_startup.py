"""Fail-closed proof that Aura's documented base lane can start alone."""

from __future__ import annotations

import subprocess
import sys

import pytest

from aura_backend.runtime import RuntimeConfigurationError, RuntimeSettings
from tests.support.main_subprocess_probe import ProbeFailure, run_probe


def test_optional_feature_flags_default_false() -> None:
    settings = RuntimeSettings.from_mapping({})

    assert settings.mcp_enabled is False
    assert settings.memvid_enabled is False
    assert settings.autonomic_enabled is False


@pytest.mark.parametrize(
    "setting",
    ("AURA_MCP_ENABLED", "AURA_MEMVID_ENABLED", "AUTONOMIC_ENABLED"),
)
@pytest.mark.parametrize("value", ("", "1", "yes", "on", "TRUE ", "false "))
def test_optional_feature_flags_are_strict_booleans(
    setting: str,
    value: str,
) -> None:
    with pytest.raises(RuntimeConfigurationError) as captured:
        RuntimeSettings.from_mapping({setting: value})

    assert captured.value.setting_name == setting


def test_base_only_child_proves_complete_runtime_path() -> None:
    evidence = run_probe("base_only_startup", timeout=12.0)

    assert evidence["blocked_optional_roots"] == [
        "fastmcp",
        "google",
        "mcp",
        "memvid_sdk",
    ]
    assert evidence["attempted_optional_imports"] == []
    assert evidence["selected_provider"] == "ollama"
    assert evidence["host"] == "127.0.0.1"
    assert evidence["preflight"] == {
        "check_count": 12,
        "exit_code": 0,
        "status": "pass",
    }
    assert evidence["serve"] == {
        "argv_contains_factory": True,
        "exit_code": 0,
        "host": "127.0.0.1",
        "status": "pass",
    }
    assert evidence["lifespan"] == {
        "cleanup_events": ["provider", "base_services"],
        "ready": True,
        "resource_states": {
            "autonomic": "not_configured",
            "base_services": "ready",
            "gemini_bridge": "not_configured",
            "mcp": "not_configured",
            "memvid": "not_configured",
            "selected_provider": "ready",
        },
    }
    assert evidence["forbidden_effects"] == []
    assert evidence["repository_data_roots_unchanged"] is True


@pytest.mark.parametrize("scenario", ("_partial", "_crash", "_hang"))
def test_base_only_probe_rejects_incomplete_or_unbounded_children(
    scenario: str,
) -> None:
    with pytest.raises(ProbeFailure):
        run_probe(scenario, timeout=0.1 if scenario == "_hang" else 2.0)


def test_public_main_imports_when_every_optional_distribution_is_blocked() -> None:
    script = r'''
import builtins

blocked = {"mcp", "fastmcp", "google", "memvid_sdk"}
attempted = []
original = builtins.__import__

def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".", 1)[0]
    if root in blocked:
        attempted.append(name)
        raise ModuleNotFoundError(f"blocked optional root: {root}")
    return original(name, globals, locals, fromlist, level)

builtins.__import__ = guarded
import aura_backend.main
import aura_backend.runtime
assert attempted == [], attempted
'''
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=8.0,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr[-2000:]
