"""Schema and epistemic-truth tests for Phase 2 runtime baselines."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest


EVIDENCE_PATH = (
    Path(__file__).resolve().parents[2]
    / ".planning"
    / "evidence"
    / "phase-02"
    / "runtime-baseline.json"
)
ALLOWED_OUTCOMES = {"pass", "not_run", "blocked", "failed"}
REQUIRED_MEASUREMENTS = {
    "cold_import_aura_backend_main",
    "warm_import_aura_backend_main",
    "provider_call_ornith",
}


def _load() -> dict[str, Any]:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_runtime_baseline_has_complete_content_free_schema() -> None:
    evidence = _load()

    assert evidence["schema_version"] == 1
    assert evidence["phase"] == "02-provider-and-runtime-core"
    assert evidence["status"] == "baseline_only"
    assert datetime.fromisoformat(evidence["captured_at"].replace("Z", "+00:00"))
    assert set(evidence["environment"]) == {
        "architecture",
        "platform",
        "python",
    }
    assert evidence["environment"]["platform"] == "linux"
    assert evidence["environment"]["architecture"] == "x86_64"

    measurements = evidence["measurements"]
    assert {measurement["name"] for measurement in measurements} == REQUIRED_MEASUREMENTS
    assert {measurement["kind"] for measurement in measurements} == {
        "cold_import",
        "warm_import",
        "provider_call",
    }
    for measurement in measurements:
        assert measurement["command"]
        assert measurement["outcome"] in ALLOWED_OUTCOMES
        if measurement["outcome"] == "pass":
            assert measurement["sample_count"] == len(measurement["samples_ms"])
            assert measurement["sample_count"] >= 3
            assert all(sample > 0 for sample in measurement["samples_ms"])
            assert "reason" not in measurement
        else:
            assert measurement["reason"]
            assert measurement["sample_count"] == 0
            assert measurement["samples_ms"] == []

    serialized = json.dumps(evidence, sort_keys=True).lower()
    for forbidden in (
        "prompt",
        "response_body",
        "api_key",
        "secret",
        "/home/",
        "hostname",
    ):
        assert forbidden not in serialized


def test_baseline_cannot_claim_optimization_without_comparable_samples() -> None:
    evidence = _load()
    comparison = evidence["comparison"]

    assert comparison == {
        "status": "not_run",
        "reason": "baseline_only_no_comparable_before_after_samples",
        "optimization_claim": None,
    }


@pytest.mark.parametrize("outcome", ("not_run", "blocked", "failed"))
def test_non_success_measurements_require_reason_and_no_samples(outcome: str) -> None:
    measurement = {
        "name": "provider_call_ornith",
        "kind": "provider_call",
        "command": "bounded optional command",
        "outcome": outcome,
        "reason": "explicit_non_success_reason",
        "sample_count": 0,
        "samples_ms": [],
    }

    assert measurement["outcome"] != "pass"
    assert measurement["reason"]
    assert measurement["samples_ms"] == []
