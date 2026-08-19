"""Offline contract tests for Aura's provider-domain boundary."""

from __future__ import annotations

import asyncio
import os
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
        assert is_dataclass(failure)
        assert type(failure).__dataclass_params__.frozen is True
        assert hasattr(type(failure), "__slots__")
        with pytest.raises(FrozenInstanceError):
            failure.code = ProviderErrorCode.UNAVAILABLE  # type: ignore[misc]
        with pytest.raises(TypeError):
            Completed(result=failure)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        ProviderFailure(  # type: ignore[call-arg]
            code=ProviderErrorCode.UNAVAILABLE,
            raw_exception=RuntimeError("source exception must remain chained only"),
        )


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


def test_settings_default_to_local_ollama_without_cloud_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pure settings parsing has a useful local default and no ambient env read."""
    from aura_backend.providers.config import ProviderKind, ProviderSettings

    def forbidden_getenv(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("ProviderSettings.from_mapping must remain pure")

    monkeypatch.setattr(os, "getenv", forbidden_getenv)
    settings = ProviderSettings.from_mapping({})

    assert settings.kind is ProviderKind.OLLAMA
    assert settings.model == "llama3.1"
    assert settings.base_url == "http://127.0.0.1:11434/v1"
    assert settings.api_key is None
    assert settings.max_retries == 0
    assert settings.max_tool_turns == 3


@pytest.mark.parametrize(
    ("provider", "credential_name", "model_name"),
    (
        ("gemini", "GEMINI_API_KEY", "gemini-test-model"),
        ("openrouter", "OPENROUTER_API_KEY", "openrouter/test-model"),
    ),
)
def test_cloud_settings_validate_only_the_selected_credential(
    provider: str,
    credential_name: str,
    model_name: str,
) -> None:
    """Explicit cloud selection checks its own key and ignores the other provider."""
    from aura_backend.providers.config import ProviderKind, ProviderSettings

    model_key = "AURA_MODEL" if provider == "gemini" else "OPENROUTER_MODEL"
    settings = ProviderSettings.from_mapping(
        {
            "AURA_DEFAULT_PROVIDER": provider,
            credential_name: "credential-SENTINEL-selected",
            model_key: model_name,
        }
    )

    assert settings.kind is ProviderKind(provider)
    assert settings.model == model_name
    assert settings.api_key == "credential-SENTINEL-selected"


@pytest.mark.parametrize(
    ("provider", "credential_name"),
    (("gemini", "GEMINI_API_KEY"), ("openrouter", "OPENROUTER_API_KEY")),
)
def test_selected_cloud_provider_requires_its_credential_safely(
    provider: str,
    credential_name: str,
) -> None:
    """A missing selected cloud key fails before an adapter can be constructed."""
    from aura_backend.providers.config import ProviderSettings
    from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure

    with pytest.raises(ProviderFailure) as captured:
        ProviderSettings.from_mapping({"AURA_DEFAULT_PROVIDER": provider})

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.provider == provider
    assert captured.value.setting_name == credential_name
    assert credential_name in str(captured.value)


def test_unknown_provider_fails_closed_without_echoing_the_value() -> None:
    """A typo can never silently select or construct a cloud provider."""
    from aura_backend.providers.config import ProviderSettings
    from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure

    unknown = "unknown-provider-credential-SENTINEL"
    with pytest.raises(ProviderFailure) as captured:
        ProviderSettings.from_mapping({"AURA_DEFAULT_PROVIDER": unknown})

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.provider is None
    assert captured.value.setting_name == "AURA_DEFAULT_PROVIDER"
    assert unknown not in str(captured.value)
    assert unknown not in repr(captured.value.to_public_dict())


@pytest.mark.parametrize(
    ("setting_name", "invalid_value"),
    (
        ("AURA_PROVIDER_REQUEST_TIMEOUT_SECONDS", "0"),
        ("AURA_PROVIDER_REQUEST_TIMEOUT_SECONDS", "nan"),
        ("AURA_PROVIDER_CONNECT_TIMEOUT_SECONDS", "inf"),
        ("AURA_PROVIDER_READ_TIMEOUT_SECONDS", "-1"),
        ("AURA_PROVIDER_WRITE_TIMEOUT_SECONDS", "3601"),
        ("AURA_PROVIDER_POOL_TIMEOUT_SECONDS", "not-a-number"),
        ("AURA_PROVIDER_MAX_RETRIES", "-1"),
        ("AURA_PROVIDER_MAX_RETRIES", "1.5"),
        ("AURA_PROVIDER_MAX_RETRIES", "11"),
        ("MAX_FUNCTION_CALL_ROUNDS", "0"),
        ("MAX_FUNCTION_CALL_ROUNDS", "101"),
    ),
)
def test_config_rejects_invalid_timeout_retry_and_tool_turn_bounds(
    setting_name: str,
    invalid_value: str,
) -> None:
    """Numeric provider policy is finite, positive where required, and bounded."""
    from aura_backend.providers.config import ProviderSettings
    from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure

    with pytest.raises(ProviderFailure) as captured:
        ProviderSettings.from_mapping({setting_name: invalid_value})

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.provider == "ollama"
    assert captured.value.setting_name == setting_name
    assert invalid_value not in str(captured.value)


@pytest.mark.parametrize(
    ("setting_name", "invalid_value"),
    (
        ("OLLAMA_MODEL", "   "),
        ("OLLAMA_BASE_URL", "https://user:password@example.invalid/v1"),
        ("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1?token=secret-SENTINEL"),
    ),
)
def test_config_diagnostics_name_setting_without_leaking_credential_or_url(
    setting_name: str,
    invalid_value: str,
) -> None:
    """Invalid model/URL input is identified only by safe metadata."""
    from aura_backend.providers.config import ProviderSettings
    from aura_backend.providers.errors import ProviderFailure

    with pytest.raises(ProviderFailure) as captured:
        ProviderSettings.from_mapping({setting_name: invalid_value})

    rendered = f"{captured.value!s} {captured.value!r}"
    assert captured.value.setting_name == setting_name
    assert invalid_value not in rendered
    assert "password" not in rendered
    assert "secret-SENTINEL" not in rendered


def test_settings_are_frozen_and_repr_redacts_credentials_and_base_url() -> None:
    """Secret-bearing settings cannot mutate or leak through routine diagnostics."""
    from aura_backend.providers.config import ProviderSettings

    api_key = "credential-SENTINEL-private"
    base_url = "https://openrouter.ai/api/v1"
    settings = ProviderSettings.from_mapping(
        {
            "AURA_DEFAULT_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": api_key,
            "OPENROUTER_BASE_URL": base_url,
        }
    )

    rendered = repr(settings)
    assert api_key not in rendered
    assert base_url not in rendered
    with pytest.raises(FrozenInstanceError):
        settings.max_retries = 2  # type: ignore[misc]
