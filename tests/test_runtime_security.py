"""Behavioral tests for Aura's private, local-only runtime boundary."""

import pytest

from aura_backend.runtime_security import (
    allowed_browser_origins,
    safe_export_format,
    safe_storage_component,
    server_host,
)


def test_default_browser_origins_are_local_frontends_only() -> None:
    """An unconfigured Aura install trusts only its bundled local UI."""
    assert allowed_browser_origins(None) == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def test_configured_browser_origins_are_trimmed_and_deduplicated() -> None:
    """Explicit local alternatives remain predictable and order preserving."""
    configured = " http://localhost:3000, http://localhost:3000,http://127.0.0.1:5174 "

    assert allowed_browser_origins(configured) == (
        "http://localhost:3000",
        "http://127.0.0.1:5174",
    )


def test_wildcard_browser_origin_is_rejected() -> None:
    """A random website must not be allowed to drive the local companion API."""
    with pytest.raises(ValueError, match="wildcard"):
        allowed_browser_origins("*")


def test_server_binds_to_loopback_unless_explicitly_configured() -> None:
    """A default Aura install is reachable only from its own machine."""
    assert server_host(None) == "127.0.0.1"


def test_normal_user_identifier_remains_stable_for_existing_profiles() -> None:
    """Hardening must not rename ordinary profile and conversation identifiers."""
    assert safe_storage_component("ty-local_01") == "ty-local_01"


@pytest.mark.parametrize(
    "unsafe_identifier",
    ("", ".", "..", "../outside", "folder/name", r"folder\name", "nul\x00byte"),
)
def test_storage_identifiers_cannot_escape_their_data_directory(
    unsafe_identifier: str,
) -> None:
    """Profile and export identifiers cannot become filesystem paths."""
    with pytest.raises(ValueError, match="identifier"):
        safe_storage_component(unsafe_identifier)


def test_only_implemented_export_format_is_accepted() -> None:
    """Aura must not report success for formats it never writes."""
    assert safe_export_format("json") == "json"
    with pytest.raises(ValueError, match="format"):
        safe_export_format("../../script")
