"""Synthetic preservation copy/restore contracts.

Every path in this module is created beneath pytest's ``tmp_path``.  The tests
must never inspect Aura's real persistence roots or the system backup mount.
"""

from __future__ import annotations

import os
import sqlite3
import gc
import json
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
from aura_backend.preservation.cli import build_parser, main
from aura_backend.preservation.inventory import inventory_roots
from aura_backend.preservation.manifest import RootDeclaration, RootRole
from aura_backend.preservation.restore import verify_disposable_restore


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


def _inventory_for_store(repository: Path, source: Path, key: bytes):
    return inventory_roots(
        repository,
        (
            RootDeclaration(
                alias="active-01",
                repository_relative_path=source.relative_to(repository).as_posix(),
                role=RootRole.ACTIVE,
            ),
        ),
        hmac_key=key,
        run_id="synthetic-run",
        tool_commit="test",
    )


def _closed_chroma_store(root: Path, *, tied_embeddings: bool = False) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(root))
    collection = client.create_collection("synthetic_collection")
    if tied_embeddings:
        collection.add(
            ids=[f"opaque-{index}" for index in range(6)],
            embeddings=[[1.0, 0.0] for _ in range(6)],
            documents=[f"private {index}" for index in range(6)],
            metadatas=[{"private": index} for index in range(6)],
        )
    else:
        collection.add(
            ids=["opaque-a", "opaque-b", "opaque-c"],
            embeddings=[[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]],
            documents=["private one", "private two", "private three"],
            metadatas=[{"private": 1}, {"private": 2}, {"private": 3}],
        )
    del collection
    client.close()
    del client
    gc.collect()


def _backed_up_chroma(tmp_path: Path, *, tied_embeddings: bool = False):
    source = tmp_path / "repository" / "source"
    source.parent.mkdir()
    _closed_chroma_store(source, tied_embeddings=tied_embeddings)
    key = b"restore-fixture-key-material-32b"
    inventory = _inventory_for_store(source.parent, source, key)
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    ticket = issue_quiescence_ticket(
        {"active-01": source},
        backup_root,
        inventory_manifest=inventory,
    )
    backup = copy_from_ticket(
        {"active-01": source}, backup_root, "snapshot", ticket
    )
    return source, backup, inventory, key


def test_verify_accepts_deterministic_tied_nearest_neighbors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid tied neighbor need not be the lexicographically selected ID."""
    _, backup, inventory, key = _backed_up_chroma(
        tmp_path, tied_embeddings=True
    )
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()
    import chromadb

    real_client = chromadb.PersistentClient

    class TiedCollection:
        def __init__(self, wrapped):
            self._wrapped = wrapped
            self.name = wrapped.name

        def count(self):
            return self._wrapped.count()

        def get(self, *args, **kwargs):
            return self._wrapped.get(*args, **kwargs)

        @property
        def configuration(self):
            return self._wrapped.configuration

        def query(self, *args, **kwargs):
            identities = sorted(str(value) for value in self._wrapped.get(include=[])["ids"])
            selected = identities[0]
            tied_neighbors = [value for value in identities if value != selected][:5]
            return {
                "ids": [tied_neighbors],
                "distances": [[0.0 for _ in tied_neighbors]],
            }

    class TiedClient:
        def __init__(self, *args, **kwargs):
            self._wrapped = real_client(*args, **kwargs)

        def list_collections(self):
            return self._wrapped.list_collections()

        def get_collection(self, name):
            return TiedCollection(self._wrapped.get_collection(name))

        def close(self):
            self._wrapped.close()

    monkeypatch.setattr(chromadb, "PersistentClient", TiedClient)

    result = verify_disposable_restore(
        backup, restore_parent, inventory, hmac_key=key
    )

    assert result.status is CheckStatus.PASS
    assert result.check_status("retrieval_parity") is CheckStatus.PASS
    assert result.retrieval_fixture_count == 1


def test_verify_rejects_nondeterministic_ordered_query_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated identical queries must produce one stable opaque fixture."""
    _, backup, inventory, key = _backed_up_chroma(tmp_path)
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()
    import chromadb

    real_client = chromadb.PersistentClient

    class NondeterministicCollection:
        def __init__(self, wrapped):
            self._wrapped = wrapped
            self.name = wrapped.name
            self._query_count = 0

        def count(self):
            return self._wrapped.count()

        def get(self, *args, **kwargs):
            return self._wrapped.get(*args, **kwargs)

        @property
        def configuration(self):
            return self._wrapped.configuration

        def query(self, *args, **kwargs):
            result = self._wrapped.query(*args, **kwargs)
            self._query_count += 1
            if self._query_count % 2 == 0:
                result["ids"][0].reverse()
                result["distances"][0].reverse()
            return result

    class NondeterministicClient:
        def __init__(self, *args, **kwargs):
            self._wrapped = real_client(*args, **kwargs)

        def list_collections(self):
            return self._wrapped.list_collections()

        def get_collection(self, name):
            return NondeterministicCollection(self._wrapped.get_collection(name))

        def close(self):
            self._wrapped.close()

    monkeypatch.setattr(chromadb, "PersistentClient", NondeterministicClient)

    result = verify_disposable_restore(
        backup, restore_parent, inventory, hmac_key=key
    )

    assert result.status is not CheckStatus.PASS
    assert result.check_status("retrieval_parity") is CheckStatus.FAIL


def test_verify_preserves_archive_not_applicable_sqlite_parity(
    tmp_path: Path,
) -> None:
    """Disposable restore accepts the same classified archive anomaly only."""
    repository = tmp_path / "repository"
    active = repository / "active"
    archive = repository / "archive"
    repository.mkdir()
    _closed_chroma_store(active)
    archive.mkdir()
    (archive / "historical.sqlite3").write_bytes(b"retained non-database artifact")
    key = b"archive-restore-key-material-32"
    inventory = inventory_roots(
        repository,
        (
            RootDeclaration("active-01", "active", RootRole.ACTIVE),
            RootDeclaration("archive-01", "archive", RootRole.ARCHIVE),
        ),
        hmac_key=key,
        run_id="archive-parity",
        tool_commit="test",
    )
    sources = {"active-01": active, "archive-01": archive}
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    ticket = issue_quiescence_ticket(
        sources,
        backup_root,
        inventory_manifest=inventory,
    )
    backup = copy_from_ticket(sources, backup_root, "snapshot", ticket)
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()

    result = verify_disposable_restore(
        backup,
        restore_parent,
        inventory,
        hmac_key=key,
    )

    assert result.status is CheckStatus.PASS
    assert result.check_status("sqlite_integrity") is CheckStatus.PASS
    assert result.check_status("foreign_key_parity") is CheckStatus.PASS


def test_verify_never_licenses_not_applicable_on_an_active_root(
    tmp_path: Path,
) -> None:
    """Even forged active N/A evidence must fail disposable SQLite parity."""
    repository = tmp_path / "repository"
    active = repository / "active"
    active.mkdir(parents=True)
    (active / "broken.sqlite3").write_bytes(b"not a sqlite database")
    key = b"active-restore-key-material-32b"
    failed_inventory = inventory_roots(
        repository,
        (RootDeclaration("active-01", "active", RootRole.ACTIVE),),
        hmac_key=key,
        run_id="active-forgery",
        tool_commit="test",
    )
    database = replace(
        failed_inventory.roots[0].databases[0],
        integrity_status=CheckStatus.NOT_APPLICABLE,
        integrity_result="not_applicable",
        foreign_key_status=CheckStatus.NOT_APPLICABLE,
        reason_code="preserved_non_sqlite_archive",
    )
    root = replace(
        failed_inventory.roots[0],
        status=CheckStatus.PASS,
        databases=(database,),
    )
    forged_inventory = replace(
        failed_inventory,
        roots=(root,),
        status=CheckStatus.PASS,
    )
    sources = {"active-01": active}
    backup_root = tmp_path / "offline"
    backup_root.mkdir()
    ticket = issue_quiescence_ticket(
        sources,
        backup_root,
        inventory_manifest=forged_inventory,
    )
    backup = copy_from_ticket(sources, backup_root, "snapshot", ticket)
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()

    result = verify_disposable_restore(
        backup,
        restore_parent,
        forged_inventory,
        hmac_key=key,
    )

    assert result.status is CheckStatus.FAIL
    assert result.check_status("sqlite_integrity") is CheckStatus.FAIL


def test_verify_opens_chroma_only_on_disposable_restore_and_cleans_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, backup, inventory, key = _backed_up_chroma(tmp_path)
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()
    import chromadb

    real_client = chromadb.PersistentClient
    opened: list[Path] = []

    def recording_client(*args, **kwargs):
        raw_path = kwargs.get("path", args[0] if args else None)
        opened.append(Path(raw_path).resolve())
        return real_client(*args, **kwargs)

    monkeypatch.setattr(chromadb, "PersistentClient", recording_client)
    source_before = source.joinpath("chroma.sqlite3").read_bytes()

    result = verify_disposable_restore(
        backup,
        restore_parent,
        inventory,
        hmac_key=key,
    )

    assert result.status is CheckStatus.PASS
    assert opened
    assert all(path.is_relative_to(restore_parent.resolve()) for path in opened)
    assert all(path != source.resolve() for path in opened)
    assert all(not path.is_relative_to(backup.destination) for path in opened)
    assert not result.disposable_path.exists()
    assert source.joinpath("chroma.sqlite3").read_bytes() == source_before
    public_text = json.dumps(result.to_public_dict())
    assert "synthetic_collection" not in public_text
    assert "opaque-a" not in public_text
    assert "private one" not in public_text


def test_verify_rejects_changed_or_omitted_backup_sidecar(tmp_path: Path) -> None:
    _, backup, inventory, key = _backed_up_chroma(tmp_path)
    sidecar = next(backup.destination.rglob("data_level0.bin"))
    sidecar.unlink()
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()

    result = verify_disposable_restore(
        backup, restore_parent, inventory, hmac_key=key
    )

    assert result.status is CheckStatus.FAIL
    assert result.check_status("backup_hash_parity") is CheckStatus.FAIL
    assert result.check_status("chroma_counts") is CheckStatus.NOT_RUN


def test_verify_rejects_foreign_key_parity_mismatch(tmp_path: Path) -> None:
    _, backup, inventory, key = _backed_up_chroma(tmp_path)
    database = backup.destination / "active-01" / "chroma.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("CREATE TABLE extra_parent(id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE extra_child(parent_id INTEGER REFERENCES extra_parent(id))"
        )
        connection.execute("INSERT INTO extra_child(parent_id) VALUES (404)")
    current = __import__(
        "aura_backend.preservation.backup", fromlist=["snapshot_roots"]
    ).snapshot_roots({"active-01": backup.destination / "active-01"})
    forged = replace(backup, destination_manifest=current)
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()

    result = verify_disposable_restore(
        forged, restore_parent, inventory, hmac_key=key
    )

    assert result.status is CheckStatus.FAIL
    assert result.check_status("foreign_key_parity") is CheckStatus.FAIL


@pytest.mark.parametrize("fault", ["count", "retrieval", "resource"])
def test_verify_cannot_pass_count_retrieval_or_resource_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _, backup, inventory, key = _backed_up_chroma(tmp_path)
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()
    import chromadb

    real_client = chromadb.PersistentClient

    class FaultyCollection:
        def __init__(self, wrapped):
            self._wrapped = wrapped
            self.name = wrapped.name

        def count(self):
            count = self._wrapped.count()
            return count + 1 if fault == "count" else count

        def get(self, *args, **kwargs):
            return self._wrapped.get(*args, **kwargs)

        def query(self, *args, **kwargs):
            if fault == "resource":
                raise RuntimeError("synthetic resource limit")
            result = self._wrapped.query(*args, **kwargs)
            if fault == "retrieval":
                result["ids"][0][0] = "wrong-result"
            return result

    class FaultyClient:
        def __init__(self, *args, **kwargs):
            self._wrapped = real_client(*args, **kwargs)

        def list_collections(self):
            return self._wrapped.list_collections()

        def get_collection(self, name):
            return FaultyCollection(self._wrapped.get_collection(name))

        def close(self):
            self._wrapped.close()

    monkeypatch.setattr(chromadb, "PersistentClient", FaultyClient)

    result = verify_disposable_restore(
        backup, restore_parent, inventory, hmac_key=key
    )

    assert result.status is not CheckStatus.PASS
    assert result.check_status("chroma_counts") is not CheckStatus.PASS or result.check_status(
        "retrieval_parity"
    ) is not CheckStatus.PASS


def test_parser_exposes_every_normative_preservation_command(tmp_path: Path) -> None:
    parser = build_parser()
    commands = {
        "inventory": [
            "--repository-root", str(tmp_path), "--backup-root", str(tmp_path / "b"),
            "--run-id", "run", "--private-manifest", str(tmp_path / "p"),
            "--public-summary", str(tmp_path / "s"), "--root", "active=data",
        ],
        "validate-summary": ["--summary", str(tmp_path / "s")],
        "preflight": [
            "--inventory-summary", str(tmp_path / "i"), "--backup-root", str(tmp_path / "b"),
            "--public-summary", str(tmp_path / "q"), "--ticket-ttl-seconds", "900",
        ],
        "validate-quiescence": [
            "--summary", str(tmp_path / "q"), "--inventory", str(tmp_path / "i"),
            "--require-pass",
        ],
        "backup-from-ticket": [
            "--inventory-summary", str(tmp_path / "i"), "--quiescence-summary", str(tmp_path / "q"),
            "--backup-root", str(tmp_path / "b"), "--destination-name", "copy",
        ],
        "verify": [
            "--inventory-summary", str(tmp_path / "i"), "--quiescence-summary", str(tmp_path / "q"),
            "--backup-root", str(tmp_path / "b"), "--restore-parent", str(tmp_path / "r"),
            "--public-summary", str(tmp_path / "v"),
        ],
        "validate-restore-summary": [
            "--summary", str(tmp_path / "v"), "--inventory", str(tmp_path / "i"),
            "--quiescence", str(tmp_path / "q"), "--require-pass",
            "--require-source-unchanged", "--require-fk-parity", "--require-retrieval-parity",
        ],
    }
    assert {parser.parse_args([command, *arguments]).command for command, arguments in commands.items()} == set(commands)


def test_cli_rejects_cross_artifact_digest_substitution(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.json"
    quiescence = tmp_path / "quiescence.json"
    restore = tmp_path / "restore.json"
    common = {
        "schema_version": 1,
        "run_id": "run",
        "status": "pass",
        "source_set_sha256": "a" * 64,
        "checks": [{"name": "required", "status": "pass", "evidence_sha256": "b" * 64}],
        "created_at_utc": "2026-08-19T00:00:00Z",
        "tool_commit": "test",
    }
    inventory.write_text(json.dumps({**common, "command": "inventory"}), encoding="utf-8")
    quiescence.write_text(json.dumps({**common, "command": "preflight"}), encoding="utf-8")
    restore.write_text(
        json.dumps(
            {
                **common,
                "command": "verify",
                "inventory_summary_sha256": "c" * 64,
                "quiescence_summary_sha256": "d" * 64,
                "gates": {
                    "source_unchanged": True,
                    "foreign_key_parity": True,
                    "retrieval_parity": True,
                },
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "validate-restore-summary",
            "--summary", str(restore),
            "--inventory", str(inventory),
            "--quiescence", str(quiescence),
            "--require-pass",
            "--require-source-unchanged",
            "--require-fk-parity",
            "--require-retrieval-parity",
        ]
    ) == 4


def test_cli_runs_inventory_ticket_backup_restore_chain_on_synthetic_data(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    source = repository / "data"
    repository.mkdir()
    _closed_chroma_store(source)
    backup_root = tmp_path / "offline"
    restore_parent = tmp_path / "restore-parent"
    restore_parent.mkdir()
    inventory_private = backup_root / "run" / "inventory.private.json"
    inventory_public = repository / "inventory.json"
    quiescence_public = repository / "quiescence.json"
    restore_public = repository / "restore.json"

    assert main(
        [
            "inventory",
            "--repository-root", str(repository),
            "--backup-root", str(backup_root),
            "--run-id", "run",
            "--private-manifest", str(inventory_private),
            "--public-summary", str(inventory_public),
            "--root", "active=data",
            "--require-role", "active",
        ]
    ) == 0
    assert main(
        [
            "preflight",
            "--inventory-summary", str(inventory_public),
            "--backup-root", str(backup_root),
            "--public-summary", str(quiescence_public),
            "--ticket-ttl-seconds", "900",
        ]
    ) == 0
    assert main(
        [
            "validate-quiescence",
            "--summary", str(quiescence_public),
            "--inventory", str(inventory_public),
            "--require-pass",
        ]
    ) == 0
    assert main(
        [
            "backup-from-ticket",
            "--inventory-summary", str(inventory_public),
            "--quiescence-summary", str(quiescence_public),
            "--backup-root", str(backup_root),
            "--destination-name", "snapshot",
        ]
    ) == 0
    assert main(
        [
            "verify",
            "--inventory-summary", str(inventory_public),
            "--quiescence-summary", str(quiescence_public),
            "--backup-root", str(backup_root),
            "--restore-parent", str(restore_parent),
            "--public-summary", str(restore_public),
        ]
    ) == 0
    first_restore_summary = json.loads(restore_public.read_text(encoding="utf-8"))
    first_private_relpath = first_restore_summary["private_artifact_relpath"]
    assert (backup_root / first_private_relpath).is_file()
    assert main(
        [
            "verify",
            "--inventory-summary", str(inventory_public),
            "--quiescence-summary", str(quiescence_public),
            "--backup-root", str(backup_root),
            "--restore-parent", str(restore_parent),
            "--public-summary", str(restore_public),
        ]
    ) == 0
    assert main(
        [
            "validate-restore-summary",
            "--summary", str(restore_public),
            "--inventory", str(inventory_public),
            "--quiescence", str(quiescence_public),
            "--require-pass",
            "--require-source-unchanged",
            "--require-fk-parity",
            "--require-retrieval-parity",
        ]
    ) == 0
    restore_summary = json.loads(restore_public.read_text(encoding="utf-8"))
    assert restore_summary["private_artifact_relpath"] != first_private_relpath
    assert (backup_root / first_private_relpath).is_file()
    assert (backup_root / restore_summary["private_artifact_relpath"]).is_file()
    assert {
        "schema_version",
        "command",
        "run_id",
        "status",
        "source_set_sha256",
        "checks",
        "created_at_utc",
        "tool_commit",
    }.issubset(restore_summary)
    assert restore_summary["status"] == "pass"
