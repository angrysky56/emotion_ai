"""Offline truth-table and HTTP contract tests for Aura health reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aura_backend.providers.base import ProviderHealth, ProviderHealthStatus
from aura_backend.runtime.app import (
    ApplicationRuntimeSnapshot,
    ResourceState,
    ResourceStatus,
)
from aura_backend.runtime.health import (
    HealthStatus,
    aggregate_health,
    public_readiness,
)


CHECKED_AT = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _runtime_snapshot(
    *,
    ready: bool = True,
    resources: tuple[ResourceStatus, ...] | None = None,
) -> ApplicationRuntimeSnapshot:
    """Build a content-free application snapshot for health aggregation."""
    return ApplicationRuntimeSnapshot(
        ready=ready,
        accepting_work=ready,
        closed=False,
        code=None,
        resources=resources
        or (
            ResourceStatus(
                name="legacy_services",
                required=True,
                state=ResourceState.READY,
            ),
            ResourceStatus(
                name="selected_provider",
                required=True,
                state=ResourceState.READY,
            ),
        ),
    )


def _selected_health(
    status: ProviderHealthStatus = ProviderHealthStatus.READY,
) -> ProviderHealth:
    return ProviderHealth(
        provider="ollama",
        model="ornith:latest",
        status=status,
        retryable=status is ProviderHealthStatus.UNAVAILABLE,
    )


def test_health_model_preserves_distinct_non_success_states() -> None:
    """Unknown evidence must never collapse into a successful health state."""
    states = {
        HealthStatus.BLOCKED,
        HealthStatus.UNKNOWN,
        HealthStatus.PARTIAL,
        HealthStatus.UNAVAILABLE,
        HealthStatus.NOT_RUN,
        HealthStatus.READY,
    }

    assert len({state.value for state in states}) == len(states)
    assert all(state is not HealthStatus.READY for state in states - {HealthStatus.READY})


@pytest.mark.parametrize(
    ("runtime_ready", "provider_status", "expected_ready", "expected_status"),
    (
        (True, ProviderHealthStatus.READY, True, HealthStatus.READY),
        (True, ProviderHealthStatus.UNAVAILABLE, False, HealthStatus.UNAVAILABLE),
        (
            True,
            ProviderHealthStatus.MODEL_NOT_FOUND,
            False,
            HealthStatus.MODEL_NOT_FOUND,
        ),
        (True, ProviderHealthStatus.UNKNOWN, False, HealthStatus.UNKNOWN),
        (False, ProviderHealthStatus.READY, False, HealthStatus.BLOCKED),
    ),
)
def test_aggregate_health_truth_table(
    runtime_ready: bool,
    provider_status: ProviderHealthStatus,
    expected_ready: bool,
    expected_status: HealthStatus,
) -> None:
    report = aggregate_health(
        runtime_snapshot=_runtime_snapshot(ready=runtime_ready),
        selected_provider="ollama",
        selected_model="ornith:latest",
        selected_health=_selected_health(provider_status),
        checked_at=CHECKED_AT,
    )

    selected = next(provider for provider in report.providers if provider.selected)
    assert report.ready is expected_ready
    assert selected.status is expected_status


def test_aggregate_snapshot_rejects_vacuous_and_contradictory_ready_claims() -> None:
    failed_required = ResourceStatus(
        name="storage",
        required=True,
        state=ResourceState.FAILED,
        code="required_resource_failed",
    )
    optional_absent = ResourceStatus(
        name="optional_cloud",
        required=False,
        state=ResourceState.NOT_CONFIGURED,
    )

    contradictory = aggregate_health(
        runtime_snapshot=_runtime_snapshot(resources=(failed_required, optional_absent)),
        selected_provider="ollama",
        selected_model="ornith:latest",
        selected_health=_selected_health(),
        checked_at=CHECKED_AT,
    )
    vacuous = aggregate_health(
        runtime_snapshot=ApplicationRuntimeSnapshot(
            ready=True,
            accepting_work=True,
            closed=False,
            code=None,
            resources=(),
        ),
        selected_provider="ollama",
        selected_model="ornith:latest",
        selected_health=_selected_health(),
        checked_at=CHECKED_AT,
    )

    assert contradictory.ready is False
    assert contradictory.status is HealthStatus.BLOCKED
    assert vacuous.ready is False
    assert vacuous.status is HealthStatus.BLOCKED


def test_aggregate_marks_unselected_clouds_not_configured_without_failing_local() -> None:
    report = aggregate_health(
        runtime_snapshot=_runtime_snapshot(),
        selected_provider="ollama",
        selected_model="ornith:latest",
        selected_health=_selected_health(),
        checked_at=CHECKED_AT,
    )

    assert report.ready is True
    assert {
        provider.provider: provider.status for provider in report.providers
    } == {
        "ollama": HealthStatus.READY,
        "gemini": HealthStatus.NOT_CONFIGURED,
        "openrouter": HealthStatus.NOT_CONFIGURED,
    }


def test_redacted_public_snapshot_uses_an_allowlist_recursively() -> None:
    sentinels = (
        "SECRET-API-KEY",
        "https://user:password@example.invalid/private",
        "private prompt",
        "private response",
        "private tool result",
        "Traceback (most recent call last)",
    )
    report = aggregate_health(
        runtime_snapshot=ApplicationRuntimeSnapshot(
            ready=True,
            accepting_work=True,
            closed=False,
            code=sentinels[0],
            resources=(
                ResourceStatus(
                    name=sentinels[2],
                    required=True,
                    state=ResourceState.FAILED,
                    code=sentinels[5],
                ),
            ),
        ),
        selected_provider="ollama",
        selected_model="ornith:latest",
        selected_health=ProviderHealth(
            provider=sentinels[1],
            model=sentinels[3],
            status=ProviderHealthStatus.UNAVAILABLE,
            retryable=True,
            correlation_id=sentinels[4],
        ),
        checked_at=CHECKED_AT,
    )

    payload = public_readiness(
        report,
        now=CHECKED_AT + timedelta(seconds=2),
        correlation_id="health-request-1",
    )
    serialized = json.dumps(payload, sort_keys=True)

    assert set(payload) == {
        "age_seconds",
        "code",
        "correlation_id",
        "providers",
        "ready",
        "resources",
        "status",
        "timestamp",
    }
    assert payload["age_seconds"] == 2.0
    assert payload["correlation_id"] == "health-request-1"
    assert all(sentinel not in serialized for sentinel in sentinels)


def test_health_import_performs_no_resource_or_network_work() -> None:
    script = """
import asyncio
import pathlib
import socket

def blocked(*args, **kwargs):
    raise AssertionError("health import attempted runtime work")

socket.create_connection = blocked
socket.socket.connect = blocked
asyncio.create_subprocess_exec = blocked
asyncio.create_subprocess_shell = blocked
pathlib.Path.mkdir = blocked
pathlib.Path.open = blocked

import aura_backend.runtime.health
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
