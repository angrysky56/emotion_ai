"""Pure, cached health aggregation and privacy-safe public serialization.

This module never probes a provider or constructs a runtime resource.  Callers
give it already-observed, content-free snapshots; the resulting frozen report is
safe to cache on the FastAPI application and serialize repeatedly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from aura_backend.providers.base import ProviderHealth, ProviderHealthStatus
from aura_backend.providers.config import ProviderKind

from .app import ApplicationRuntimeSnapshot, ResourceState

_SAFE_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_SAFE_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

_SAFE_RUNTIME_CODES = {
    "invalid_provider_runtime",
    "optional_resource_failed",
    "required_provider_missing",
    "required_resource_failed",
    "required_resource_missing",
    "runtime_closed",
    "runtime_unavailable",
    "shutdown_cancelled",
    "shutdown_failed",
    "startup_cancelled",
}


class HealthStatus(str, Enum):
    """Explicit evidence states; only ``READY`` means ready."""

    LIVE = "live"
    READY = "ready"
    NOT_READY = "not_ready"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    NOT_RUN = "not_run"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class ResourceHealthSnapshot:
    """Safe cached state for one application-owned resource."""

    name: str
    required: bool
    status: HealthStatus
    code: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderHealthSnapshot:
    """Safe cached state for one supported provider selection."""

    provider: str
    model: str | None
    selected: bool
    required: bool
    status: HealthStatus
    code: str | None = None
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    """One immutable health observation used by all public health routes."""

    ready: bool
    status: HealthStatus
    code: str | None
    checked_at: datetime
    resources: tuple[ResourceHealthSnapshot, ...]
    providers: tuple[ProviderHealthSnapshot, ...]

    def __post_init__(self) -> None:
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")
        if self.ready is not (self.status is HealthStatus.READY):
            raise ValueError("only the ready status may represent readiness")


def _resource_status(state: ResourceState) -> HealthStatus:
    return {
        ResourceState.NOT_STARTED: HealthStatus.NOT_RUN,
        ResourceState.NOT_CONFIGURED: HealthStatus.NOT_CONFIGURED,
        ResourceState.READY: HealthStatus.READY,
        ResourceState.FAILED: HealthStatus.FAILED,
        ResourceState.CLOSED: HealthStatus.CLOSED,
    }[state]


def _safe_resource_code(code: str | None, status: HealthStatus) -> str | None:
    if code in _SAFE_RUNTIME_CODES:
        return code
    if status in {HealthStatus.READY, HealthStatus.NOT_CONFIGURED}:
        return None
    return "resource_not_ready"


def _safe_resource_name(name: str) -> str:
    return name if _SAFE_NAME.fullmatch(name) is not None else "resource"


def _provider_status(
    observation: ProviderHealth | None,
    *,
    selected_provider: str,
    selected_model: str,
) -> tuple[HealthStatus, str | None, bool]:
    if observation is None:
        return HealthStatus.NOT_RUN, "provider_check_not_run", False
    if (
        observation.provider != selected_provider
        or observation.model != selected_model
    ):
        return HealthStatus.BLOCKED, "provider_identity_mismatch", False
    mapped = {
        ProviderHealthStatus.READY: HealthStatus.READY,
        ProviderHealthStatus.NOT_CONFIGURED: HealthStatus.NOT_CONFIGURED,
        ProviderHealthStatus.UNAVAILABLE: HealthStatus.UNAVAILABLE,
        ProviderHealthStatus.MODEL_NOT_FOUND: HealthStatus.MODEL_NOT_FOUND,
        ProviderHealthStatus.UNKNOWN: HealthStatus.UNKNOWN,
    }[observation.status]
    code = {
        HealthStatus.READY: None,
        HealthStatus.NOT_CONFIGURED: "provider_not_configured",
        HealthStatus.UNAVAILABLE: "provider_unavailable",
        HealthStatus.MODEL_NOT_FOUND: "model_not_found",
        HealthStatus.UNKNOWN: "provider_unknown",
    }[mapped]
    return mapped, code, observation.retryable


def aggregate_health(
    *,
    runtime_snapshot: ApplicationRuntimeSnapshot | None,
    selected_provider: str,
    selected_model: str,
    selected_health: ProviderHealth | None,
    checked_at: datetime | None = None,
) -> HealthSnapshot:
    """Derive readiness from complete cached evidence, never trusted booleans alone."""
    if selected_provider not in {kind.value for kind in ProviderKind}:
        raise ValueError("selected_provider must be a supported provider")
    if _SAFE_MODEL.fullmatch(selected_model) is None:
        raise ValueError("selected_model must be a safe model identifier")

    observed_at = checked_at or datetime.now(UTC)
    if observed_at.tzinfo is None:
        raise ValueError("checked_at must be timezone-aware")

    resources: tuple[ResourceHealthSnapshot, ...] = ()
    runtime_consistent = False
    required_ready = False
    runtime_status = HealthStatus.NOT_RUN
    runtime_code = "runtime_not_started"

    if runtime_snapshot is not None:
        resources = tuple(
            ResourceHealthSnapshot(
                name=_safe_resource_name(resource.name),
                required=resource.required,
                status=_resource_status(resource.state),
                code=_safe_resource_code(
                    resource.code,
                    _resource_status(resource.state),
                ),
            )
            for resource in runtime_snapshot.resources
        )
        required_resources = tuple(resource for resource in resources if resource.required)
        selected_resource_present = any(
            resource.name == "selected_provider" and resource.required
            for resource in resources
        )
        required_ready = bool(required_resources) and all(
            resource.status is HealthStatus.READY for resource in required_resources
        )
        runtime_consistent = (
            runtime_snapshot.ready
            and runtime_snapshot.accepting_work
            and not runtime_snapshot.closed
            and selected_resource_present
            and required_ready
        )
        if runtime_consistent:
            runtime_status = HealthStatus.READY
            runtime_code = None
        else:
            runtime_status = HealthStatus.BLOCKED
            runtime_code = (
                "runtime_closed"
                if runtime_snapshot.closed
                else "runtime_not_ready"
            )

    selected_status, selected_code, retryable = _provider_status(
        selected_health,
        selected_provider=selected_provider,
        selected_model=selected_model,
    )
    if not runtime_consistent and selected_status is HealthStatus.READY:
        selected_status = HealthStatus.BLOCKED
        selected_code = runtime_code
        retryable = False

    providers = tuple(
        ProviderHealthSnapshot(
            provider=kind.value,
            model=selected_model if kind.value == selected_provider else None,
            selected=kind.value == selected_provider,
            required=kind.value == selected_provider,
            status=(
                selected_status
                if kind.value == selected_provider
                else HealthStatus.NOT_CONFIGURED
            ),
            code=(
                selected_code
                if kind.value == selected_provider
                else "provider_not_configured"
            ),
            retryable=retryable if kind.value == selected_provider else False,
        )
        for kind in ProviderKind
    )

    is_ready = runtime_consistent and selected_status is HealthStatus.READY
    if is_ready:
        overall_status = HealthStatus.READY
        overall_code = None
    elif runtime_status is not HealthStatus.READY:
        overall_status = runtime_status
        overall_code = runtime_code
    else:
        overall_status = selected_status
        overall_code = selected_code

    return HealthSnapshot(
        ready=is_ready,
        status=overall_status,
        code=overall_code,
        checked_at=observed_at.astimezone(UTC),
        resources=resources,
        providers=providers,
    )


def _safe_correlation_id(correlation_id: str) -> str:
    if _SAFE_CORRELATION.fullmatch(correlation_id) is None:
        return "invalid-correlation-id"
    return correlation_id


def _age_seconds(checked_at: datetime, now: datetime | None) -> float:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    age = max(0.0, (current - checked_at.astimezone(UTC)).total_seconds())
    return round(age, 3)


def _public_resource(resource: ResourceHealthSnapshot) -> dict[str, Any]:
    return {
        "name": resource.name,
        "required": resource.required,
        "status": resource.status.value,
        "code": resource.code,
    }


def _public_provider(provider: ProviderHealthSnapshot) -> dict[str, Any]:
    return {
        "provider": provider.provider,
        "model": provider.model,
        "selected": provider.selected,
        "required": provider.required,
        "status": provider.status.value,
        "code": provider.code,
        "retryable": provider.retryable,
    }


def public_readiness(
    snapshot: HealthSnapshot,
    *,
    correlation_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Serialize readiness from an explicit allowlist of safe scalar fields."""
    return {
        "status": snapshot.status.value,
        "ready": snapshot.ready,
        "code": snapshot.code,
        "timestamp": snapshot.checked_at.isoformat().replace("+00:00", "Z"),
        "age_seconds": _age_seconds(snapshot.checked_at, now),
        "correlation_id": _safe_correlation_id(correlation_id),
        "resources": [_public_resource(resource) for resource in snapshot.resources],
        "providers": [_public_provider(provider) for provider in snapshot.providers],
    }
