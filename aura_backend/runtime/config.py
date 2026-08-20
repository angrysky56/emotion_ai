"""Pure, typed settings for Aura's local application runtime.

Parsing accepts an explicit mapping so importing or validating configuration never
reads ``.env``, opens storage, constructs a provider, or contacts a service.
"""

from __future__ import annotations

import ipaddress
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from aura_backend.providers.config import ProviderSettings
from aura_backend.providers.errors import ProviderFailure
from aura_backend.runtime_security import allowed_browser_origins, server_host

_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_MAX_PREFLIGHT_TIMEOUT_SECONDS = 300.0


class RuntimeConfigurationError(ValueError):
    """A content-free failure naming only the rejected setting."""

    def __init__(self, setting_name: str) -> None:
        self.setting_name = setting_name
        super().__init__(f"runtime configuration: setting={setting_name}")


def _configured_text(
    mapping: Mapping[str, str | None],
    key: str,
    default: str,
) -> str:
    if key not in mapping:
        return default
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        raise RuntimeConfigurationError(key)
    return value.strip()


def _valid_bind_host(host: str) -> bool:
    if any(character.isspace() or ord(character) < 32 for character in host):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if len(host) > 253:
            return False
        labels = host.rstrip(".").split(".")
        return bool(labels) and all(_HOST_LABEL.fullmatch(label) for label in labels)
    return True


def _validate_origins(origins: tuple[str, ...]) -> tuple[str, ...]:
    if not origins:
        raise RuntimeConfigurationError("ALLOWED_ORIGINS")
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            parsed.port
        except ValueError as error:
            raise RuntimeConfigurationError("ALLOWED_ORIGINS") from error
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeConfigurationError("ALLOWED_ORIGINS")
    return origins


def _bounded_integer(
    mapping: Mapping[str, str | None],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = _configured_text(mapping, key, str(default))
    try:
        value = int(raw_value, 10)
    except ValueError as error:
        raise RuntimeConfigurationError(key) from error
    if not minimum <= value <= maximum:
        raise RuntimeConfigurationError(key)
    return value


def _bounded_float(
    mapping: Mapping[str, str | None],
    key: str,
    default: float,
    *,
    maximum: float,
) -> float:
    raw_value = _configured_text(mapping, key, str(default))
    try:
        value = float(raw_value)
    except ValueError as error:
        raise RuntimeConfigurationError(key) from error
    if not math.isfinite(value) or value <= 0 or value > maximum:
        raise RuntimeConfigurationError(key)
    return value


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Validated application settings with local-only defaults."""

    host: str
    port: int
    allowed_origins: tuple[str, ...]
    storage_root: Path
    preflight_timeout_seconds: float
    provider: ProviderSettings

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[str, str | None],
    ) -> RuntimeSettings:
        """Parse known settings without reading or mutating external state."""
        configured_host = mapping.get("AURA_HOST")
        if configured_host is not None and not isinstance(configured_host, str):
            raise RuntimeConfigurationError("AURA_HOST")
        host = server_host(configured_host)
        if not _valid_bind_host(host):
            raise RuntimeConfigurationError("AURA_HOST")

        configured_origins = mapping.get("ALLOWED_ORIGINS")
        if configured_origins is not None and not isinstance(configured_origins, str):
            raise RuntimeConfigurationError("ALLOWED_ORIGINS")
        try:
            origins = allowed_browser_origins(configured_origins)
        except ValueError as error:
            raise RuntimeConfigurationError("ALLOWED_ORIGINS") from error

        storage_value = _configured_text(
            mapping,
            "AURA_DATA_DIRECTORY",
            "./aura_data",
        )
        if "\x00" in storage_value:
            raise RuntimeConfigurationError("AURA_DATA_DIRECTORY")

        try:
            provider = ProviderSettings.from_mapping(mapping)
        except ProviderFailure as error:
            raise RuntimeConfigurationError(
                error.setting_name or "AURA_DEFAULT_PROVIDER"
            ) from error

        return cls(
            host=host,
            port=_bounded_integer(
                mapping,
                "PORT",
                8000,
                minimum=1,
                maximum=65535,
            ),
            allowed_origins=_validate_origins(origins),
            storage_root=Path(storage_value),
            preflight_timeout_seconds=_bounded_float(
                mapping,
                "AURA_PREFLIGHT_TIMEOUT_SECONDS",
                10.0,
                maximum=_MAX_PREFLIGHT_TIMEOUT_SECONDS,
            ),
            provider=provider,
        )
