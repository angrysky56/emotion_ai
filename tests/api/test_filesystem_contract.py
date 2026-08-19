"""Filesystem boundary tests for Aura profiles and conversation exports.

The pure path-construction tests remain import-light.  Production ``main`` is
exercised only in a disposable child process later in this module so importing
the test suite cannot initialize Aura's stateful services.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aura_backend.runtime_security import (
    StoragePathError,
    safe_export_format,
    safe_export_path,
    safe_profile_path,
    safe_storage_component,
)
from tests.support.main_subprocess_probe import (
    _install_import_fakes,
    _sanitized_environment,
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


def _run_filesystem_probe(scenario: str, tmp_path: Path) -> dict[str, Any]:
    """Run production filesystem behavior in a bounded disposable child."""
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", scenario, str(tmp_path)],
        cwd=tmp_path,
        env=_sanitized_environment(),
        capture_output=True,
        text=True,
        timeout=8.0,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout)


def test_aura_filesystem_uses_contained_paths_and_writes_real_json(
    tmp_path: Path,
) -> None:
    """Direct production calls remain functional while rejected paths write nothing."""
    result = _run_filesystem_probe("direct", tmp_path)

    assert result["profile"] == {
        "exists": True,
        "loaded_name": "Ty",
        "under_users": True,
    }
    assert result["export"] == {
        "empty_phase_1_baseline": {
            "cognitive_patterns": [],
            "conversations": [],
            "emotional_patterns": [],
        },
        "exists": True,
        "json_parseable": True,
        "under_exports": True,
    }
    assert result["invalid_errors"] == [
        "Invalid storage identifier",
        "Invalid storage identifier",
        "Invalid storage identifier",
        "Unsupported export format; Aura currently supports JSON",
    ]
    assert result["symlink_escape_blocked"] is True
    assert result["outside_files"] == []


def test_export_endpoint_returns_client_errors_and_only_claims_written_files(
    tmp_path: Path,
) -> None:
    """The request contract rejects bad input and ties success to a real JSON file."""
    result = _run_filesystem_probe("endpoint", tmp_path)

    assert result["invalid_identifier"] == {
        "body": {"detail": "Invalid export request"},
        "status_code": 400,
    }
    assert result["unsupported_format"] == {
        "body": {"detail": "Invalid export request"},
        "status_code": 400,
    }
    assert result["rejected_request_files_created"] == []
    assert result["success"]["status_code"] == 200
    assert result["success"]["path_exists"] is True
    assert result["success"]["path_under_exports"] is True
    assert result["success"]["json_parseable"] is True
    assert result["success"]["conversations"] == []


async def _direct_child(main: Any, root: Path) -> dict[str, Any]:
    base_path = root / "direct-data"
    filesystem = main.AuraFileSystem(str(base_path))
    profile_path = Path(
        await filesystem.save_user_profile("ty-local_01", {"name": "Ty"})
    )
    loaded_profile = await filesystem.load_user_profile("ty-local_01")
    export_path = Path(
        await filesystem.export_conversation_history("ty-local_01", "json")
    )
    export_data = json.loads(export_path.read_text(encoding="utf-8"))

    invalid_errors: list[str] = []
    invalid_operations = (
        filesystem.save_user_profile("../outside", {"name": "No"}),
        filesystem.load_user_profile("../outside"),
        filesystem.export_conversation_history("../outside", "json"),
        filesystem.export_conversation_history("ty-local_01", "csv"),
    )
    for operation in invalid_operations:
        try:
            await operation
        except StoragePathError as error:
            invalid_errors.append(str(error))

    symlink_base = root / "symlink-data"
    outside_path = root / "outside"
    symlink_base.mkdir()
    outside_path.mkdir()
    os.symlink(outside_path, symlink_base / "users", target_is_directory=True)
    symlink_filesystem = main.AuraFileSystem(str(symlink_base))
    try:
        await symlink_filesystem.save_user_profile("ty-local_01", {"name": "No"})
    except StoragePathError:
        symlink_escape_blocked = True
    else:
        symlink_escape_blocked = False

    return {
        "export": {
            "empty_phase_1_baseline": {
                "cognitive_patterns": export_data["cognitive_patterns"],
                "conversations": export_data["conversations"],
                "emotional_patterns": export_data["emotional_patterns"],
            },
            "exists": export_path.is_file(),
            "json_parseable": isinstance(export_data, dict),
            "under_exports": export_path.parent == (base_path / "exports").resolve(),
        },
        "invalid_errors": invalid_errors,
        "outside_files": sorted(path.name for path in outside_path.iterdir()),
        "profile": {
            "exists": profile_path.is_file(),
            "loaded_name": loaded_profile["name"] if loaded_profile else None,
            "under_users": profile_path.parent == (base_path / "users").resolve(),
        },
        "symlink_escape_blocked": symlink_escape_blocked,
    }


def _endpoint_child(main: Any, root: Path) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    base_path = root / "endpoint-data"
    main.aura_file_system = main.AuraFileSystem(str(base_path))
    client = TestClient(main.app, raise_server_exceptions=False)
    exports_path = base_path / "exports"

    before = set(exports_path.iterdir())
    invalid_identifier = client.post("/export/..%5Coutside")
    unsupported_format = client.post(
        "/export/ty-local_01", params={"format_type": "csv"}
    )
    after_rejections = set(exports_path.iterdir())

    success = client.post("/export/ty-local_01", params={"format_type": "json"})
    success_body = success.json()
    export_path = Path(success_body["export_path"])
    export_data = json.loads(export_path.read_text(encoding="utf-8"))
    return {
        "invalid_identifier": {
            "body": invalid_identifier.json(),
            "status_code": invalid_identifier.status_code,
        },
        "rejected_request_files_created": sorted(
            str(path.relative_to(base_path)) for path in after_rejections - before
        ),
        "success": {
            "conversations": export_data["conversations"],
            "json_parseable": isinstance(export_data, dict),
            "path_exists": export_path.is_file(),
            "path_under_exports": export_path.parent == exports_path.resolve(),
            "status_code": success.status_code,
        },
        "unsupported_format": {
            "body": unsupported_format.json(),
            "status_code": unsupported_format.status_code,
        },
    }


def _child_main(scenario: str, root: Path) -> None:
    initializer_calls: list[str] = []
    swallowed_stdout = io.StringIO()
    with contextlib.redirect_stdout(swallowed_stdout):
        _install_import_fakes(initializer_calls)
        import aura_backend.main as main

        if scenario == "direct":
            result = asyncio.run(_direct_child(main, root))
        elif scenario == "endpoint":
            result = _endpoint_child(main, root)
        else:
            raise ValueError(f"Unknown filesystem scenario: {scenario}")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "--child":
        raise SystemExit("usage: test_filesystem_contract.py --child SCENARIO ROOT")
    _child_main(sys.argv[2], Path(sys.argv[3]))
