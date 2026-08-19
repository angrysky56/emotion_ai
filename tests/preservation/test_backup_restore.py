"""Synthetic preservation copy/restore contracts.

Every path in this module is created beneath pytest's ``tmp_path``.  The tests
must never inspect Aura's real persistence roots or the system backup mount.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aura_backend.preservation.backup import (
    BackupBlocked,
    copy_from_ticket,
    issue_quiescence_ticket,
)
from aura_backend.preservation.manifest import CheckStatus


def _synthetic_store(root: Path) -> dict[str, bytes]:
    """Create a closed SQLite plus Chroma-like sidecar persistence unit."""
    root.mkdir(parents=True)
    database = root / "chroma.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;
            CREATE TABLE parent(id INTEGER PRIMARY KEY);
            CREATE TABLE child(parent_id INTEGER REFERENCES parent(id));
            INSERT INTO child(parent_id) VALUES (99);
            """
        )
    segment = root / "11111111-1111-1111-1111-111111111111"
    segment.mkdir()
    payloads = {
        "11111111-1111-1111-1111-111111111111/header.bin": b"header",
        "11111111-1111-1111-1111-111111111111/data_level0.bin": b"vectors",
        "11111111-1111-1111-1111-111111111111/length.bin": b"length",
        "11111111-1111-1111-1111-111111111111/link_lists.bin": b"links",
        "chroma.sqlite3-wal": b"synthetic-wal-sidecar",
        "chroma.sqlite3-shm": b"synthetic-shm-sidecar",
    }
    for relative, content in payloads.items():
        path = root / relative
        path.write_bytes(content)
    payloads["chroma.sqlite3"] = database.read_bytes()
    return payloads


def _passing_ticket(source: Path, backup_root: Path):
    return issue_quiescence_ticket(
        {"active-01": source},
        backup_root,
        ttl_seconds=900,
    )


def test_copy_finalizes_complete_persistence_unit_only_after_exact_parity(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    expected = _synthetic_store(source)
    backup_root = tmp_path / "offline"
    backup_root.mkdir()

    result = copy_from_ticket(
        {"active-01": source},
        backup_root,
        "snapshot",
        _passing_ticket(source, backup_root),
    )

    assert result.status is CheckStatus.PASS
    assert result.destination == backup_root / "snapshot"
    assert result.destination.is_dir()
    assert not result.partial_destination.exists()
    assert result.source_before == result.source_after
    assert result.source_before == result.destination_manifest
    assert {
        path.relative_to(result.destination / "active-01").as_posix(): path.read_bytes()
        for path in (result.destination / "active-01").rglob("*")
        if path.is_file()
    } == expected


@pytest.mark.parametrize("relation", ["inside_source", "source_inside_backup"])
def test_copy_rejects_overlapping_source_and_backup_paths(
    tmp_path: Path, relation: str
) -> None:
    if relation == "inside_source":
        source = tmp_path / "source"
        _synthetic_store(source)
        backup_root = source / "backup"
        backup_root.mkdir()
    else:
        backup_root = tmp_path / "backup"
        source = backup_root / "source"
        _synthetic_store(source)

    with pytest.raises(BackupBlocked, match="disjoint"):
        issue_quiescence_ticket({"active-01": source}, backup_root)
    assert (source / "chroma.sqlite3").exists()


def test_copy_rejects_existing_destination_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _synthetic_store(source)
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    destination = backup_root / "snapshot"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(BackupBlocked, match="new"):
        copy_from_ticket(
            {"active-01": source},
            backup_root,
            "snapshot",
            _passing_ticket(source, backup_root),
        )
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_copy_rejects_symlinked_backup_parent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _synthetic_store(source)
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(BackupBlocked, match="symlink"):
        issue_quiescence_ticket({"active-01": source}, linked_parent)
    assert not any(real_parent.iterdir())


@pytest.mark.parametrize("entry_type", ["symlink", "fifo"])
def test_copy_rejects_source_links_and_special_files(
    tmp_path: Path, entry_type: str
) -> None:
    source = tmp_path / "source"
    _synthetic_store(source)
    unsafe = source / "unsafe"
    if entry_type == "symlink":
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        unsafe.symlink_to(outside)
    else:
        os.mkfifo(unsafe)
    backup_root = tmp_path / "offline"
    backup_root.mkdir()

    with pytest.raises(BackupBlocked, match="regular"):
        issue_quiescence_ticket({"active-01": source}, backup_root)
    assert not (backup_root / "snapshot").exists()


def test_copy_rejects_stale_or_failed_quiescence_ticket(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _synthetic_store(source)
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    ticket = _passing_ticket(source, backup_root)
    stale = replace(ticket, expires_at_utc=datetime.now(UTC) - timedelta(seconds=1))
    failed = replace(ticket, status=CheckStatus.BLOCKED)

    with pytest.raises(BackupBlocked, match="expired"):
        copy_from_ticket({"active-01": source}, backup_root, "stale", stale)
    with pytest.raises(BackupBlocked, match="passing"):
        copy_from_ticket({"active-01": source}, backup_root, "failed", failed)
    assert not (backup_root / "stale").exists()
    assert not (backup_root / "failed").exists()


def test_copy_detects_source_mutation_and_retains_partial_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _synthetic_store(source)
    mutable = source / "mutable.bin"
    mutable.write_bytes(b"before")
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    ticket = _passing_ticket(source, backup_root)

    import shutil

    original_copyfileobj = shutil.copyfileobj
    mutated = False

    def mutate_after_first_copy(source_stream, destination_stream, length=0):
        nonlocal mutated
        original_copyfileobj(source_stream, destination_stream, length)
        if not mutated:
            mutated = True
            mutable.write_bytes(b"after")

    monkeypatch.setattr(shutil, "copyfileobj", mutate_after_first_copy)

    with pytest.raises(BackupBlocked, match="changed"):
        copy_from_ticket(
            {"active-01": source},
            backup_root,
            "snapshot",
            ticket,
        )

    assert not (backup_root / "snapshot").exists()
    assert (backup_root / "snapshot.partial").is_dir()
    assert mutable.read_bytes() == b"after"


def test_quiescence_ticket_has_no_false_success_when_a_check_is_not_pass(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _synthetic_store(source)
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    ticket = _passing_ticket(source, backup_root)
    blocked_check = replace(
        ticket,
        checks=(*ticket.checks[:-1], replace(ticket.checks[-1], status=CheckStatus.NOT_RUN)),
    )

    with pytest.raises(BackupBlocked, match="required check"):
        copy_from_ticket(
            {"active-01": source},
            backup_root,
            "snapshot",
            blocked_check,
        )
    assert not (backup_root / "snapshot").exists()


def test_backup_test_module_contains_no_real_backup_or_aura_root_literal() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    forbidden = (chr(47) + "backup", "aura" + "_chroma" + "_db")
    assert not any(value in source for value in forbidden)
