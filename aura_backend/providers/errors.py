"""Safe provider failure types for Aura's provider-neutral boundary.

Provider adapters may chain an original exception when raising
``ProviderFailure``, but the source exception is deliberately not stored on this
object.  Public diagnostics are always built from the explicit allowlist in
``to_public_dict``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ProviderErrorCode(str, Enum):
    """Normalized non-success outcomes from provider work."""

    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    UNAVAILABLE = "unavailable"
    MODEL_NOT_FOUND = "model_not_found"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    MALFORMED_RESPONSE = "malformed_response"
    RESOURCE_LIMIT = "resource_limit"
    STREAM_INTERRUPTED = "stream_interrupted"
    CANCELLED = "cancelled"


_SAFE_PROVIDER = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_SAFE_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_SETTING = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _validate_safe_metadata(value: str | None, pattern: re.Pattern[str], field: str) -> None:
    """Reject unsafe diagnostic metadata without echoing its value."""
    if value is not None and pattern.fullmatch(value) is None:
        raise ValueError(f"{field} is not safe diagnostic metadata")


@dataclass(frozen=True, slots=True)
class ProviderFailure(Exception):
    """A normalized provider failure containing only safe diagnostic metadata.

    The class is an exception rather than a result or stream event, so callers
    cannot accidentally persist or render it as a completed assistant answer.
    Cancellation remains ``asyncio.CancelledError`` at operation boundaries; the
    ``cancelled`` code exists for safe health and metrics records only.
    """

    code: ProviderErrorCode
    provider: str | None = None
    model: str | None = None
    retryable: bool = False
    correlation_id: str | None = None
    setting_name: str | None = None
    partial_event_count: int = 0

    def __post_init__(self) -> None:
        """Validate allowlisted metadata without accepting source error text."""
        if not isinstance(self.code, ProviderErrorCode):
            raise TypeError("code must be a ProviderErrorCode")
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be a bool")
        if not isinstance(self.partial_event_count, int) or self.partial_event_count < 0:
            raise ValueError("partial_event_count must be a non-negative integer")
        _validate_safe_metadata(self.provider, _SAFE_PROVIDER, "provider")
        _validate_safe_metadata(self.model, _SAFE_MODEL, "model")
        _validate_safe_metadata(
            self.correlation_id,
            _SAFE_CORRELATION,
            "correlation_id",
        )
        _validate_safe_metadata(self.setting_name, _SAFE_SETTING, "setting_name")

    def to_public_dict(self) -> dict[str, str | bool | None]:
        """Return the fixed public failure schema; never serialize ``self`` wholesale."""
        return {
            "code": self.code.value,
            "provider": self.provider,
            "model": self.model,
            "retryable": self.retryable,
            "correlation_id": self.correlation_id,
        }

    def __str__(self) -> str:
        """Render a content-free diagnostic suitable for default logs."""
        parts = [f"provider failure: code={self.code.value}"]
        if self.provider is not None:
            parts.append(f"provider={self.provider}")
        if self.model is not None:
            parts.append(f"model={self.model}")
        if self.setting_name is not None:
            parts.append(f"setting={self.setting_name}")
        if self.correlation_id is not None:
            parts.append(f"correlation_id={self.correlation_id}")
        parts.append(f"retryable={str(self.retryable).lower()}")
        return " ".join(parts)
