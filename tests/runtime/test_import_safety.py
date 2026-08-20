"""Fail-closed subprocess evidence for Aura import purity."""

from __future__ import annotations

import pytest

from tests.support.main_subprocess_probe import ProbeFailure, run_probe


def test_main_provider_and_runtime_imports_perform_no_runtime_work() -> None:
    """Importing public modules must not construct or contact owned resources."""
    result = run_probe("import_safety", timeout=8.0)

    assert result["imported_modules"] == [
        "aura_backend.providers.factory",
        "aura_backend.providers.openai_compatible",
        "aura_backend.providers.ollama",
        "aura_backend.providers.openrouter",
        "aura_backend.providers.gemini",
        "aura_backend.providers.runtime",
        "aura_backend.runtime.config",
        "aura_backend.runtime.app",
        "aura_backend.main",
    ]
    assert result["production_initializers_called"] == []
    assert result["effects"] == []
    assert result["repository_data_roots_unchanged"] is True


def test_unselected_optional_provider_sdk_is_not_required_for_import() -> None:
    """The default local composition imports even when Google's SDK is absent."""
    result = run_probe("import_without_optional_provider", timeout=8.0)

    assert result["optional_google_absent"] is True
    assert result["imported_modules"] == [
        "aura_backend.providers.factory",
        "aura_backend.runtime.app",
        "aura_backend.main",
    ]
    assert result["production_initializers_called"] == []
    assert result["effects"] == []


@pytest.mark.parametrize(
    ("scenario", "diagnostic"),
    (
        ("_hang", "timed out"),
        ("_crash", "exited with status"),
        ("_malformed", "invalid JSON"),
        ("_partial", "incomplete result"),
    ),
)
def test_import_evidence_rejects_non_evidence(
    scenario: str,
    diagnostic: str,
) -> None:
    """Timeout, crash, malformed, and partial child evidence are never passes."""
    with pytest.raises(ProbeFailure, match=diagnostic):
        run_probe(scenario, timeout=0.25 if scenario == "_hang" else 2.0)
