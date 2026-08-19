"""Local runtime boundary configuration for Aura.

Aura is a private desktop-style application, not a hosted multi-user service. This
module keeps that trust model explicit and independently testable without importing
the heavyweight application module.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

LOCAL_BROWSER_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class StoragePathError(ValueError):
    """Base class for caller-controlled storage path validation failures."""


class InvalidStorageIdentifier(StoragePathError):
    """Raised when a caller identifier is not a single safe path component."""


class UnsupportedExportFormat(StoragePathError):
    """Raised when a caller asks Aura to write an unimplemented export format."""


class StorageContainmentError(StoragePathError):
    """Raised when a resolved storage candidate escapes Aura's configured root."""


def server_host(configured_host: str | None) -> str:
    """Return the explicit bind host, defaulting to the local machine only."""
    return (
        configured_host.strip()
        if configured_host and configured_host.strip()
        else "127.0.0.1"
    )


def safe_storage_component(value: str) -> str:
    """Validate a caller identifier before using it in a local filename."""
    has_control_character = any(
        unicodedata.category(character) == "Cc" for character in value
    )
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or has_control_character
    ):
        raise InvalidStorageIdentifier("Invalid storage identifier")
    return value


def safe_export_format(value: str) -> str:
    """Return a supported export format or reject the request."""
    normalized = value.strip().lower()
    if normalized != "json":
        raise UnsupportedExportFormat(
            "Unsupported export format; Aura currently supports JSON"
        )
    return normalized


def _contained_storage_path(
    base_path: str | Path,
    category: str,
    filename: str,
) -> Path:
    """Resolve a fixed-category candidate and prove it remains below ``base_path``."""
    resolved_base = Path(base_path).resolve(strict=False)
    resolved_category = (resolved_base / category).resolve(strict=False)
    candidate = (resolved_category / filename).resolve(strict=False)

    if (
        not resolved_category.is_relative_to(resolved_base)
        or not candidate.is_relative_to(resolved_category)
        or not candidate.parent.is_relative_to(resolved_category)
    ):
        raise StorageContainmentError(
            "Resolved storage path is outside configured Aura data root"
        )
    return candidate


def safe_profile_path(base_path: str | Path, user_id: str) -> Path:
    """Return the contained JSON profile path for an unchanged safe identifier."""
    safe_user_id = safe_storage_component(user_id)
    return _contained_storage_path(base_path, "users", f"{safe_user_id}.json")


def safe_export_path(
    base_path: str | Path,
    user_id: str,
    timestamp: str,
    output_format: str = "json",
) -> Path:
    """Return a contained conversation export path for the supported format."""
    safe_user_id = safe_storage_component(user_id)
    safe_format = safe_export_format(output_format)
    filename = f"conversation_export_{safe_user_id}_{timestamp}.{safe_format}"
    return _contained_storage_path(base_path, "exports", filename)


def allowed_browser_origins(configured_origins: str | None) -> tuple[str, ...]:
    """Return browser origins allowed to call Aura's local API."""
    if configured_origins is None:
        return LOCAL_BROWSER_ORIGINS

    origins = tuple(
        dict.fromkeys(
            origin.strip() for origin in configured_origins.split(",") if origin.strip()
        )
    )
    if "*" in origins:
        raise ValueError("CORS wildcard origins are unsafe for Aura's local API")
    return origins
