"""Offline contract tests for Aura's provider-domain boundary."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import Any, get_type_hints

import pytest


def test_result_request_health_and_stream_values_are_frozen_and_slotted() -> None:
    """Stable provider-domain values reject mutation and dynamic attributes."""
    from aura_backend.providers.base import (
        Completed,
        ProviderHealth,
        ProviderHealthStatus,
        ProviderMessage,
        ProviderRequest,
        ProviderResult,
        ProviderUsage,
        TextDelta,
        ToolCallDelta,
        ToolDefinition,
    )

    tool = ToolDefinition(
        name="lookup_memory",
        description="Look up a synthetic record.",
        input_schema={"type": "object", "properties": {}},
    )
    usage = ProviderUsage(input_tokens=2, output_tokens=3, total_tokens=5)
    result = ProviderResult(content="Synthetic answer.", usage=usage)
    values = (
        ProviderRequest(
            messages=(ProviderMessage(role="user", content="Synthetic request."),),
            tools=(tool,),
        ),
        result,
        usage,
        ProviderHealth(
            provider="ollama",
            model="synthetic-model",
            status=ProviderHealthStatus.READY,
        ),
        tool,
        TextDelta(text="Synthetic"),
        ToolCallDelta(index=0, call_id="call-1", name="lookup_memory"),
        Completed(result=result),
    )

    for value in values:
        assert is_dataclass(value)
        assert type(value).__dataclass_params__.frozen is True
        assert hasattr(type(value), "__slots__")
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            value.unplanned_field = "mutation"  # type: ignore[attr-defined]

    with pytest.raises(TypeError):
        tool.input_schema["secret"] = "mutation"  # type: ignore[index]


def test_result_and_stream_types_have_no_raw_sdk_or_any_escape_hatch() -> None:
    """The stable contract contains normalized values, never opaque SDK payloads."""
    from aura_backend.providers.base import (
        Completed,
        ProviderResult,
        TextDelta,
        ToolCallDelta,
    )

    forbidden_names = {"raw_response", "exception", "traceback", "headers"}
    for value_type in (ProviderResult, TextDelta, ToolCallDelta, Completed):
        field_names = {field.name for field in fields(value_type)}
        assert field_names.isdisjoint(forbidden_names)
        assert Any not in get_type_hints(value_type).values()


def test_failure_codes_are_exact_and_never_success_values() -> None:
    """Every required unsuccessful state has a distinct stable code."""
    from aura_backend.providers.base import Completed, ProviderResult
    from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure

    assert {code.value for code in ProviderErrorCode} == {
        "authentication",
        "cancelled",
        "configuration",
        "malformed_response",
        "model_not_found",
        "rate_limited",
        "resource_limit",
        "stream_interrupted",
        "timeout",
        "unavailable",
    }

    for code in ProviderErrorCode:
        failure = ProviderFailure(code=code, provider="ollama", model="model-1")
        assert isinstance(failure, Exception)
        assert not isinstance(failure, ProviderResult)
        with pytest.raises(TypeError):
            Completed(result=failure)  # type: ignore[arg-type]


def test_stream_partial_failure_resource_limit_and_cancel_cannot_complete() -> None:
    """Only a validated ProviderResult can license stream completion."""
    from aura_backend.providers.base import Completed, TextDelta
    from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure

    partial = TextDelta(text="partial")
    resource_failure = ProviderFailure(code=ProviderErrorCode.RESOURCE_LIMIT)
    cancellation = asyncio.CancelledError()

    for non_result in (partial, resource_failure, cancellation):
        with pytest.raises(TypeError):
            Completed(result=non_result)  # type: ignore[arg-type]

    assert not isinstance(cancellation, ProviderFailure)
    assert isinstance(cancellation, BaseException)


def test_failure_public_serialization_and_text_redact_source_material() -> None:
    """Public failures are constructed from a fixed safe-field allowlist."""
    from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure

    sentinels = (
        "credential-SENTINEL-7f6f",
        "prompt-SENTINEL-1b29",
        "response-SENTINEL-a315",
        "exception-SENTINEL-ffee",
        "https://user:password@example.invalid/private",
        "Authorization: Bearer header-SENTINEL",
        "Traceback-SENTINEL",
    )
    failure = ProviderFailure(
        code=ProviderErrorCode.AUTHENTICATION,
        provider="openrouter",
        model="safe-model",
        retryable=False,
        correlation_id="corr-123",
        setting_name="OPENROUTER_API_KEY",
    )

    public = failure.to_public_dict()
    assert set(public) == {
        "code",
        "provider",
        "model",
        "retryable",
        "correlation_id",
    }
    rendered = f"{public!r} {failure!s} {failure!r}"
    assert failure.setting_name == "OPENROUTER_API_KEY"
    assert all(sentinel not in rendered for sentinel in sentinels)


def test_legacy_provider_exports_still_construct_and_resolve() -> None:
    """The characterized route keeps its temporary provider compatibility seam."""
    from aura_backend.providers.base import BaseProvider, Message, ProviderResponse

    message = Message(role="user", content="Synthetic request.")
    response = ProviderResponse(content="Synthetic response.")

    assert message.role == "user"
    assert response.content == "Synthetic response."
    assert BaseProvider.__name__ == "BaseProvider"
