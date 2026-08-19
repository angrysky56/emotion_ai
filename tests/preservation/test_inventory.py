"""Behavioral tests for the read-only preservation inventory."""

from __future__ import annotations

import hashlib
import os
import socket
import sqlite3
from pathlib import Path

import pytest

from aura_backend.preservation.inventory import inventory_roots
from aura_backend.preservation.manifest import CheckStatus, RootDeclaration, RootRole


def _root(path: str, *, required: bool = True) -> RootDeclaration:
    """Declare a synthetic active root beneath the test repository."""
    return RootDeclaration(
        alias="active-root",
        repository_relative_path=path,
        role=RootRole.ACTIVE,
        required=required,
    )


def test_regular_and_nested_files_are_inventoried_once_with_stable_totals(
    tmp_path: Path,
) -> None:
    """The manifest records metadata and digests, never duplicate file entries."""
    data_root = tmp_path / "data"
    nested = data_root / "nested"
    nested.mkdir(parents=True)
    (data_root / "one.txt").write_bytes(b"first private document")
    (nested / "two.bin").write_bytes(b"second private document")

    first = inventory_roots(tmp_path, [_root("data")], hmac_key=b"k" * 32)
    second = inventory_roots(tmp_path, [_root("data")], hmac_key=b"k" * 32)

    root = first.roots[0]
    assert root.status is CheckStatus.PASS
    assert root.file_count == 2
    assert root.byte_total == 45
    assert [record.relative_path for record in root.files] == [
        "nested/two.bin",
        "one.txt",
    ]
    assert all(record.file_type == "regular" for record in root.files)
    assert all(record.sha256 for record in root.files)
    assert root.aggregate_sha256 == second.roots[0].aggregate_sha256
    assert first.status is CheckStatus.PASS


def test_sqlite_integrity_and_foreign_key_results_are_separate(tmp_path: Path) -> None:
    """A structurally sound database cannot conceal foreign-key anomalies."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    database = data_root / "chroma.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            CREATE TABLE parent(id INTEGER PRIMARY KEY);
            CREATE TABLE child(
                id INTEGER PRIMARY KEY,
                parent_id INTEGER REFERENCES parent(id)
            );
            INSERT INTO child(id, parent_id) VALUES (1, 999);
            """
        )

    manifest = inventory_roots(tmp_path, [_root("data")], hmac_key=b"s" * 32)

    database_record = manifest.roots[0].databases[0]
    assert database_record.integrity_status is CheckStatus.PASS
    assert database_record.integrity_result == "ok"
    assert database_record.foreign_key_status is CheckStatus.PASS
    assert database_record.foreign_key_violation_count == 1
    assert len(database_record.foreign_key_fingerprint) == 64
    assert manifest.status is CheckStatus.PASS


def test_symlink_is_blocked_without_reading_its_target(tmp_path: Path) -> None:
    """A link is evidence of an anomaly, not permission to traverse its target."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = tmp_path / "outside-secret.txt"
    outside.write_bytes(b"must not be hashed through the link")
    (data_root / "linked.txt").symlink_to(outside)

    manifest = inventory_roots(tmp_path, [_root("data")], hmac_key=b"k" * 32)

    record = manifest.roots[0].files[0]
    assert record.relative_path == "linked.txt"
    assert record.file_type == "symlink"
    assert record.sha256 is None
    assert record.status is CheckStatus.BLOCKED
    assert manifest.status is CheckStatus.BLOCKED


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_fifo_is_blocked_without_opening_it(tmp_path: Path) -> None:
    """Inventorying a FIFO must finish without waiting for a writer."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    os.mkfifo(data_root / "pipe")

    manifest = inventory_roots(tmp_path, [_root("data")], hmac_key=b"k" * 32)

    record = manifest.roots[0].files[0]
    assert record.file_type == "fifo"
    assert record.status is CheckStatus.BLOCKED
    assert manifest.status is CheckStatus.BLOCKED


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="Unix sockets unavailable")
def test_socket_is_blocked_without_connecting_to_it(tmp_path: Path) -> None:
    """Inventorying a socket records its type without treating it as file data."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    socket_path = data_root / "service.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(socket_path))
        manifest = inventory_roots(tmp_path, [_root("data")], hmac_key=b"k" * 32)
    finally:
        server.close()

    record = manifest.roots[0].files[0]
    assert record.file_type == "socket"
    assert record.status is CheckStatus.BLOCKED
    assert manifest.status is CheckStatus.BLOCKED


def test_file_changed_while_hashing_is_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A digest is not licensed when the file changes during its own read."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    changing_file = data_root / "changing.bin"
    changing_file.write_bytes(b"before")
    real_file_digest = hashlib.file_digest

    def mutate_after_hash(stream: object, digest: str) -> object:
        result = real_file_digest(stream, digest)  # type: ignore[arg-type]
        changing_file.write_bytes(b"after and a different size")
        return result

    monkeypatch.setattr(hashlib, "file_digest", mutate_after_hash)

    manifest = inventory_roots(tmp_path, [_root("data")], hmac_key=b"k" * 32)

    record = manifest.roots[0].files[0]
    assert record.status is CheckStatus.FAIL
    assert record.sha256 is None
    assert manifest.status is CheckStatus.FAIL


def test_missing_roots_have_truthful_required_semantics(tmp_path: Path) -> None:
    """Optional absence is not_run; required absence blocks a passing claim."""
    optional = RootDeclaration(
        alias="optional-archive",
        repository_relative_path="optional-missing",
        role=RootRole.ARCHIVE,
        required=False,
    )
    required = RootDeclaration(
        alias="required-backup",
        repository_relative_path="required-missing",
        role=RootRole.BACKUP,
        required=True,
    )

    optional_only = inventory_roots(tmp_path, [optional], hmac_key=b"k" * 32)
    required_manifest = inventory_roots(tmp_path, [optional, required], hmac_key=b"k" * 32)

    assert optional_only.roots[0].status is CheckStatus.NOT_RUN
    assert optional_only.status is CheckStatus.PASS
    assert [root.status for root in required_manifest.roots] == [
        CheckStatus.NOT_RUN,
        CheckStatus.BLOCKED,
    ]
    assert required_manifest.status is CheckStatus.BLOCKED
