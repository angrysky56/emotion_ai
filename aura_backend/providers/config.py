"""Pure, local-first provider settings parsing for Aura.

This module accepts an explicit mapping so imports and tests never read ambient
environment state, construct an SDK client, inspect installed models, or contact a
service.  Callers may pass ``os.environ`` at the application composition root.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit, urlunsplit

from .errors import ProviderErrorCode, ProviderFailure


class ProviderKind(str, Enum):
    """Provider adapters supported by Aura's stable provider boundary."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_MAX_TIMEOUT_SECONDS = 3600.0
_MAX_RETRIES = 10
_MAX_TOOL_TURNS = 100


def _configuration_failure(
    *,
    kind: ProviderKind | None,
    setting_name: str,
) -> ProviderFailure:
    """Create a safe configuration failure without retaining the rejected value."""
    return ProviderFailure(
        code=ProviderErrorCode.CONFIGURATION,
        provider=kind.value if kind is not None else None,
        retryable=False,
        setting_name=setting_name,
    )


def _optional_text(mapping: Mapping[str, str | None], key: str) -> str | None:
    """Return one trimmed non-empty mapping value without consulting the process."""
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _configuration_failure(kind=None, setting_name=key)
    normalized = value.strip()
    return normalized or None


def _model_name(
    mapping: Mapping[str, str | None],
    key: str,
    default: str,
    kind: ProviderKind,
) -> str:
    """Parse a bounded provider model identifier without exposing invalid input."""
    if key in mapping:
        value = _optional_text(mapping, key)
        if value is None or _MODEL_NAME.fullmatch(value) is None:
            raise _configuration_failure(kind=kind, setting_name=key)
        return value
    return default


def _base_url(
    mapping: Mapping[str, str | None],
    key: str,
    default: str,
    kind: ProviderKind,
) -> str:
    """Parse a credential-free HTTP(S) base URL and return a normalized value."""
    raw_value = _optional_text(mapping, key) if key in mapping else default
    if raw_value is None:
        raise _configuration_failure(kind=kind, setting_name=key)
    try:
        parsed = urlsplit(raw_value)
        # Accessing ``port`` also validates malformed/non-numeric port syntax.
        parsed.port
    except ValueError as exc:
        raise _configuration_failure(kind=kind, setting_name=key) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise _configuration_failure(kind=kind, setting_name=key)
    normalized_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))


def _positive_float(
    mapping: Mapping[str, str | None],
    key: str,
    default: float,
    kind: ProviderKind,
) -> float:
    """Parse one finite positive timeout with an explicit denial-of-service cap."""
    raw_value = _optional_text(mapping, key)
    if raw_value is None:
        return default
    try:
        parsed = float(raw_value)
    except ValueError as exc:
        raise _configuration_failure(kind=kind, setting_name=key) from exc
    if not math.isfinite(parsed) or not 0.0 < parsed <= _MAX_TIMEOUT_SECONDS:
        raise _configuration_failure(kind=kind, setting_name=key)
    return parsed


def _bounded_integer(
    mapping: Mapping[str, str | None],
    key: str,
    default: int,
    kind: ProviderKind,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Parse one base-ten integer within a fixed inclusive resource bound."""
    raw_value = _optional_text(mapping, key)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value, 10)
    except ValueError as exc:
        raise _configuration_failure(kind=kind, setting_name=key) from exc
    if not minimum <= parsed <= maximum:
        raise _configuration_failure(kind=kind, setting_name=key)
    return parsed


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """Validated settings for exactly one explicitly selected provider adapter."""

    kind: ProviderKind
    model: str
    base_url: str | None = field(repr=False)
    api_key: str | None = field(default=None, repr=False)
    credential_setting: str | None = None
    request_timeout_seconds: float = 120.0
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 120.0
    write_timeout_seconds: float = 30.0
    pool_timeout_seconds: float = 5.0
    max_retries: int = 0
    max_tool_turns: int = 3
    thinking_budget: int = -1

    @property
    def provider(self) -> ProviderKind:
        """Return the selected provider kind using the domain-facing name."""
        return self.kind

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[str, str | None],
    ) -> ProviderSettings:
        """Parse an explicit mapping without imports, I/O, service calls, or env reads."""
        raw_kind = _optional_text(mapping, "AURA_DEFAULT_PROVIDER") or "ollama"
        try:
            kind = ProviderKind(raw_kind.lower())
        except ValueError as exc:
            raise _configuration_failure(
                kind=None,
                setting_name="AURA_DEFAULT_PROVIDER",
            ) from exc

        credential_setting: str | None = None
        api_key: str | None = None
        base_url: str | None
        thinking_budget = -1

        if kind is ProviderKind.OLLAMA:
            model = _model_name(mapping, "OLLAMA_MODEL", "llama3.1", kind)
            base_url = _base_url(
                mapping,
                "OLLAMA_BASE_URL",
                "http://127.0.0.1:11434/v1",
                kind,
            )
        elif kind is ProviderKind.GEMINI:
            model = _model_name(
                mapping,
                "AURA_MODEL",
                "gemini-2.0-flash-thinking-exp-01-21",
                kind,
            )
            base_url = None
            credential_setting = "GEMINI_API_KEY"
            api_key = _optional_text(mapping, credential_setting)
            if api_key is None:
                raise _configuration_failure(
                    kind=kind,
                    setting_name=credential_setting,
                )
            thinking_budget = _bounded_integer(
                mapping,
                "THINKING_BUDGET",
                -1,
                kind,
                minimum=-1,
                maximum=1_000_000,
            )
        else:
            model = _model_name(
                mapping,
                "OPENROUTER_MODEL",
                "deepseek/deepseek-r1",
                kind,
            )
            base_url = _base_url(
                mapping,
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
                kind,
            )
            credential_setting = "OPENROUTER_API_KEY"
            api_key = _optional_text(mapping, credential_setting)
            if api_key is None:
                raise _configuration_failure(
                    kind=kind,
                    setting_name=credential_setting,
                )

        return cls(
            kind=kind,
            model=model,
            base_url=base_url,
            api_key=api_key,
            credential_setting=credential_setting,
            request_timeout_seconds=_positive_float(
                mapping,
                "AURA_PROVIDER_REQUEST_TIMEOUT_SECONDS",
                120.0,
                kind,
            ),
            connect_timeout_seconds=_positive_float(
                mapping,
                "AURA_PROVIDER_CONNECT_TIMEOUT_SECONDS",
                5.0,
                kind,
            ),
            read_timeout_seconds=_positive_float(
                mapping,
                "AURA_PROVIDER_READ_TIMEOUT_SECONDS",
                120.0,
                kind,
            ),
            write_timeout_seconds=_positive_float(
                mapping,
                "AURA_PROVIDER_WRITE_TIMEOUT_SECONDS",
                30.0,
                kind,
            ),
            pool_timeout_seconds=_positive_float(
                mapping,
                "AURA_PROVIDER_POOL_TIMEOUT_SECONDS",
                5.0,
                kind,
            ),
            max_retries=_bounded_integer(
                mapping,
                "AURA_PROVIDER_MAX_RETRIES",
                0,
                kind,
                minimum=0,
                maximum=_MAX_RETRIES,
            ),
            max_tool_turns=_bounded_integer(
                mapping,
                "MAX_FUNCTION_CALL_ROUNDS",
                3,
                kind,
                minimum=1,
                maximum=_MAX_TOOL_TURNS,
            ),
            thinking_budget=thinking_budget,
        )
