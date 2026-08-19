"""Local runtime boundary configuration for Aura.

Aura is a private desktop-style application, not a hosted multi-user service. This
module keeps that trust model explicit and independently testable without importing
the heavyweight application module.
"""

LOCAL_BROWSER_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def server_host(configured_host: str | None) -> str:
    """Return the explicit bind host, defaulting to the local machine only."""
    return (
        configured_host.strip()
        if configured_host and configured_host.strip()
        else "127.0.0.1"
    )


def safe_storage_component(value: str) -> str:
    """Validate a caller identifier before using it in a local filename."""
    has_control_character = any(ord(character) < 32 for character in value)
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or has_control_character
    ):
        raise ValueError("Invalid storage identifier")
    return value


def safe_export_format(value: str) -> str:
    """Return a supported export format or reject the request."""
    normalized = value.strip().lower()
    if normalized != "json":
        raise ValueError("Unsupported export format; Aura currently supports JSON")
    return normalized


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
