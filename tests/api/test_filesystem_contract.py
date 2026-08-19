"""Filesystem boundary tests for Aura profiles and conversation exports.

The pure path-construction tests remain import-light.  Production ``main`` is
exercised only in a disposable child process later in this module so importing
the test suite cannot initialize Aura's stateful services.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aura_backend.runtime_security import (
    StoragePathError,
    safe_export_format,
    safe_export_path,
    safe_profile_path,
    safe_storage_component,
)


@pytest.mark.parametrize(
    "identifier",
    (
        "ty-local_01",
        "Aura User 2",
        "profile.name+tag@example",
        "José",
    ),
)
def test_safe_storage_component_preserves_ordinary_identifiers(identifier: str) -> None:
    """Existing non-path identifiers retain byte-for-byte filename behavior."""
    assert safe_storage_component(identifier) == identifier


@pytest.mark.parametrize(
    "identifier",
    (
        "",
        ".",
        "..",
        "../outside",
        "folder/name",
        r"folder\name",
        "/absolute",
        r"C:\absolute",
        "decoded/encoded-separator",
        "decoded\\encoded-separator",
        "nul\x00byte",
        "delete\x7fbyte",
    ),
)
def test_unsafe_storage_components_are_rejected(identifier: str) -> None:
    """Decoded traversal, separators, absolute paths, and controls are invalid."""
    with pytest.raises(StoragePathError, match="Invalid storage identifier"):
        safe_storage_component(identifier)


@pytest.mark.parametrize("output_format", ("csv", "xml", "yaml", "../json"))
def test_unsupported_export_formats_are_rejected(output_format: str) -> None:
    """Phase 1 implements JSON export only."""
    with pytest.raises(StoragePathError, match="supports JSON"):
        safe_export_format(output_format)


def test_contained_profile_and_export_paths_preserve_current_filenames(
    tmp_path: Path,
) -> None:
    """Canonical constructors combine fixed categories with unchanged IDs."""
    profile_path = safe_profile_path(tmp_path, "ty-local_01")
    export_path = safe_export_path(
        tmp_path,
        "ty-local_01",
        "20260819_120000",
        "json",
    )

    assert profile_path == tmp_path.resolve() / "users" / "ty-local_01.json"
    assert export_path == (
        tmp_path.resolve()
        / "exports"
        / "conversation_export_ty-local_01_20260819_120000.json"
    )
    assert not profile_path.exists()
    assert not export_path.exists()


@pytest.mark.parametrize(
    ("category", "constructor"),
    (
        ("users", lambda base: safe_profile_path(base, "ty-local_01")),
        (
            "exports",
            lambda base: safe_export_path(
                base,
                "ty-local_01",
                "20260819_120000",
                "json",
            ),
        ),
    ),
)
def test_symlinked_storage_parent_cannot_escape_resolved_base(
    tmp_path: Path,
    category: str,
    constructor: object,
) -> None:
    """A redirected fixed category is rejected before any outside write."""
    base_path = tmp_path / "aura-data"
    outside_path = tmp_path / "outside"
    base_path.mkdir()
    outside_path.mkdir()
    os.symlink(outside_path, base_path / category, target_is_directory=True)

    with pytest.raises(StoragePathError, match="outside configured Aura data root"):
        constructor(base_path)  # type: ignore[operator]

    assert list(outside_path.iterdir()) == []


def test_path_constructors_reject_traversal_without_creating_directories(
    tmp_path: Path,
) -> None:
    """Rejected candidates have no filesystem side effects."""
    base_path = tmp_path / "missing-data-root"

    with pytest.raises(StoragePathError, match="Invalid storage identifier"):
        safe_profile_path(base_path, "../outside")
    with pytest.raises(StoragePathError, match="Invalid storage identifier"):
        safe_export_path(base_path, "../outside", "20260819_120000", "json")

    assert not base_path.exists()
    assert not (tmp_path / "outside.json").exists()
