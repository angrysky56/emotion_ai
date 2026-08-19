"""Privacy and CLI tests for preservation evidence lanes."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from aura_backend.preservation.cli import main
from aura_backend.preservation.inventory import inventory_roots
from aura_backend.preservation.manifest import RootDeclaration, RootRole

SENTINEL = "TY_PRIVATE_SENTINEL_8f42c1"


def _active_root(path: str = "data") -> RootDeclaration:
    return RootDeclaration(
        alias="active-01",
        repository_relative_path=path,
        role=RootRole.ACTIVE,
        required=True,
    )


def _all_mapping_keys(value: object) -> set[str]:
    """Collect keys recursively so forbidden private fields cannot hide deeply."""
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for nested in value.values():
            keys.update(_all_mapping_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_all_mapping_keys(nested))
    return keys


def test_public_summary_uses_an_allowlist_and_leaks_no_private_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Documents, metadata, IDs, schema names, and errors stay private."""
    data_root = tmp_path / "data"
    private_user_directory = data_root / f"user-{SENTINEL}"
    private_user_directory.mkdir(parents=True)
    sensitive_file = private_user_directory / "conversation.txt"
    sensitive_file.write_text(
        "\n".join(
            (
                f"document={SENTINEL}",
                f"message={SENTINEL}",
                f"metadata={SENTINEL}",
                f"query={SENTINEL}",
            )
        )
    )
    database = data_root / "private.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(f'CREATE TABLE "collection_{SENTINEL}" (metadata TEXT)')
        connection.execute(
            f'INSERT INTO "collection_{SENTINEL}" VALUES (?)', (SENTINEL,)
        )

    real_open = os.open

    def refuse_sensitive_file(path: os.PathLike[str] | str, flags: int) -> int:
        if Path(path) == sensitive_file:
            raise PermissionError(f"private exception {SENTINEL}")
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", refuse_sensitive_file)
    manifest = inventory_roots(tmp_path, [_active_root()], hmac_key=b"h" * 32)

    private = manifest.to_private_dict()
    public = manifest.to_public_summary(
        private_artifact_relpath="test-run/inventory.private.json",
        private_artifact_sha256="a" * 64,
    )
    private_json = json.dumps(private, sort_keys=True)
    public_json = json.dumps(public, sort_keys=True)

    assert SENTINEL in private_json
    assert SENTINEL not in public_json
    assert private["hmac_key_hex"] == (b"h" * 32).hex()
    assert "files" in private["roots"][0]
    assert set(public) == {
        "schema_version",
        "tool_version",
        "command",
        "run_id",
        "status",
        "source_set_sha256",
        "checks",
        "created_at_utc",
        "tool_commit",
        "root_roles",
        "roots",
        "totals",
        "private_artifact_relpath",
        "private_artifact_sha256",
    }
    assert set(public["roots"][0]) == {
        "alias",
        "repository_relative_path",
        "role",
        "required",
        "status",
        "file_count",
        "byte_total",
        "aggregate_sha256",
        "database_checks",
    }
    forbidden = {
        "hmac_key_hex",
        "files",
        "databases",
        "relative_path",
        "sha256",
        "mtime_ns",
        "private_error",
        "private_error_code",
        "private_integrity_results",
        "documents",
        "messages",
        "metadata",
        "collection_names",
        "user_ids",
        "queries",
    }
    assert _all_mapping_keys(public).isdisjoint(forbidden)


def test_inventory_cli_creates_both_lanes_and_refuses_overwrite(tmp_path: Path) -> None:
    """A repeated run cannot replace either an existing private or public artifact."""
    repository = tmp_path / "repository"
    data_root = repository / "data"
    data_root.mkdir(parents=True)
    (data_root / "record.txt").write_text("private record")
    backup_root = tmp_path / "backup"
    private_manifest = backup_root / "test-run" / "inventory.private.json"
    public_summary = repository / "inventory-summary.json"
    arguments = [
        "inventory",
        "--repository-root",
        str(repository),
        "--backup-root",
        str(backup_root),
        "--run-id",
        "test-run",
        "--private-manifest",
        str(private_manifest),
        "--public-summary",
        str(public_summary),
        "--root",
        "active=data",
        "--require-role",
        "active",
    ]

    assert main(arguments) == 0
    private_before = private_manifest.read_bytes()
    public_before = public_summary.read_bytes()
    (data_root / "record.txt").write_text("changed after evidence")

    assert main(arguments) != 0
    assert private_manifest.read_bytes() == private_before
    assert public_summary.read_bytes() == public_before
    assert main(
        [
            "validate-summary",
            "--summary",
            str(public_summary),
            "--require-role",
            "active",
        ]
    ) == 0


def test_inventory_cli_returns_nonzero_for_a_blocked_required_root(
    tmp_path: Path,
) -> None:
    """Writing evidence does not turn an unrun required check into success."""
    repository = tmp_path / "repository"
    repository.mkdir()
    backup_root = tmp_path / "backup"
    private_manifest = backup_root / "blocked" / "inventory.private.json"
    public_summary = repository / "inventory-summary.json"

    exit_code = main(
        [
            "inventory",
            "--repository-root",
            str(repository),
            "--backup-root",
            str(backup_root),
            "--run-id",
            "blocked",
            "--private-manifest",
            str(private_manifest),
            "--public-summary",
            str(public_summary),
            "--root",
            "active=missing",
            "--require-role",
            "active",
        ]
    )

    assert exit_code != 0
    assert json.loads(public_summary.read_text())["status"] == "blocked"
    assert main(
        [
            "validate-summary",
            "--summary",
            str(public_summary),
            "--require-role",
            "active",
        ]
    ) != 0
