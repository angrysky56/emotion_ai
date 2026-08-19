"""Disposable restore verification for immutable Aura backups.

Chroma is imported only inside :func:`verify_disposable_restore`, after the
durable backup has been copied into a fresh temporary directory.  Neither the
source nor the durable backup is ever passed to ``PersistentClient``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from aura_backend.preservation.backup import (
    BackupBlocked,
    BackupResult,
    _copy_directory,
    _reject_symlink_components,
    snapshot_roots,
)
from aura_backend.preservation.inventory import inventory_roots
from aura_backend.preservation.manifest import (
    CheckStatus,
    EvidenceCheck,
    InventoryManifest,
    RootDeclaration,
)


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """Private verification result with an explicitly allowlisted public view."""

    status: CheckStatus
    checks: tuple[EvidenceCheck, ...]
    disposable_path: Path
    run_id: str
    source_set_sha256: str
    created_at_utc: str
    tool_commit: str
    source_unchanged: bool
    foreign_key_parity: bool
    retrieval_parity: bool
    collection_count: int = 0
    record_count: int = 0
    retrieval_fixture_count: int = 0
    retrieval_fingerprint: str = ""

    def check_status(self, name: str) -> CheckStatus:
        """Return one required check state by its stable name."""
        for check in self.checks:
            if check.name == name:
                return check.status
        raise KeyError(name)

    def to_public_dict(self) -> dict[str, Any]:
        """Return aggregate-only evidence safe for a committable summary."""
        return {
            "schema_version": 1,
            "command": "verify",
            "run_id": self.run_id,
            "status": self.status.value,
            "source_set_sha256": self.source_set_sha256,
            "checks": [
                {
                    "name": item.name,
                    "status": item.status.value,
                    "evidence_sha256": item.evidence_sha256,
                }
                for item in self.checks
            ],
            "created_at_utc": self.created_at_utc,
            "tool_commit": self.tool_commit,
            "gates": {
                "source_unchanged": self.source_unchanged,
                "foreign_key_parity": self.foreign_key_parity,
                "retrieval_parity": self.retrieval_parity,
            },
            "totals": {
                "collection_count": self.collection_count,
                "record_count": self.record_count,
                "retrieval_fixture_count": self.retrieval_fixture_count,
            },
            "retrieval_fingerprint": self.retrieval_fingerprint,
        }

    def to_private_dict(self) -> dict[str, Any]:
        """Return complete gate evidence without personal Chroma values."""
        return self.to_public_dict()


def verify_disposable_restore(
    backup: BackupResult,
    restore_parent: Path,
    inventory_manifest: InventoryManifest,
    *,
    hmac_key: bytes,
) -> RestoreResult:
    """Verify hashes, SQLite/FK evidence, counts, and opaque retrieval parity."""
    if len(hmac_key) < 16:
        raise ValueError("restore HMAC key must contain at least 16 bytes")
    _reject_symlink_components(restore_parent)
    restore_root = restore_parent.resolve(strict=True)
    if not restore_root.is_dir():
        raise ValueError("restore parent must be a directory")
    if (
        restore_root == backup.destination
        or restore_root.is_relative_to(backup.destination)
        or backup.destination.is_relative_to(restore_root)
    ):
        raise ValueError("restore and durable backup paths must be disjoint")

    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    source_unchanged = backup.source_before == backup.source_after
    base_checks = {
        "source_unchanged": _check(
            "source_unchanged",
            CheckStatus.PASS if source_unchanged else CheckStatus.FAIL,
            backup.source_after.sha256,
        )
    }
    aliases = tuple(
        item.alias for item in sorted(inventory_manifest.roots, key=lambda item: item.alias)
    )
    durable_roots = {alias: backup.destination / alias for alias in aliases}
    try:
        current_backup = snapshot_roots(durable_roots)
    except BackupBlocked:
        return _early_failure(
            backup,
            inventory_manifest,
            restore_root,
            created,
            source_unchanged,
            base_checks,
            "backup_hash_parity",
        )
    hash_parity = current_backup == backup.destination_manifest
    base_checks["backup_hash_parity"] = _check(
        "backup_hash_parity",
        CheckStatus.PASS if hash_parity else CheckStatus.FAIL,
        current_backup.sha256,
    )
    if not hash_parity or not source_unchanged:
        return _result(
            inventory_manifest,
            restore_root,
            created,
            base_checks,
            source_unchanged=source_unchanged,
            foreign_key_parity=False,
            retrieval_parity=False,
        )

    disposable = restore_root / "not-created"
    with TemporaryDirectory(prefix="aura-restore-", dir=restore_root) as temporary:
        disposable = Path(temporary).resolve()
        for alias in aliases:
            restored_root = disposable / alias
            restored_root.mkdir(mode=0o700)
            _copy_directory(durable_roots[alias], restored_root)
        copied_manifest = snapshot_roots(
            {alias: disposable / alias for alias in aliases}
        )
        copy_parity = copied_manifest == current_backup
        base_checks["restore_copy_parity"] = _check(
            "restore_copy_parity",
            CheckStatus.PASS if copy_parity else CheckStatus.FAIL,
            copied_manifest.sha256,
        )
        if not copy_parity:
            return _result(
                inventory_manifest,
                disposable,
                created,
                base_checks,
                source_unchanged=source_unchanged,
                foreign_key_parity=False,
                retrieval_parity=False,
            )

        restored_inventory = inventory_roots(
            disposable,
            tuple(
                RootDeclaration(
                    alias=root.alias,
                    repository_relative_path=root.alias,
                    role=root.role,
                    required=root.required,
                )
                for root in inventory_manifest.roots
            ),
            hmac_key=hmac_key,
            run_id=inventory_manifest.run_id,
            tool_commit=inventory_manifest.tool_commit,
        )
        restored_databases = tuple(
            database
            for root in restored_inventory.roots
            for database in root.databases
        )
        expected_database_count = sum(
            len(root.databases) for root in inventory_manifest.roots
        )
        sqlite_pass = (
            expected_database_count > 0
            and len(restored_databases) == expected_database_count
            and _sqlite_facts(restored_inventory) == _sqlite_facts(inventory_manifest)
            and _sqlite_expectations_are_licensed(inventory_manifest)
        )
        fk_parity = _foreign_key_facts(restored_inventory) == _foreign_key_facts(
            inventory_manifest
        )
        base_checks["sqlite_integrity"] = _check(
            "sqlite_integrity",
            CheckStatus.PASS if sqlite_pass else CheckStatus.FAIL,
            _sqlite_fingerprint(restored_inventory),
        )
        base_checks["foreign_key_parity"] = _check(
            "foreign_key_parity",
            CheckStatus.PASS if fk_parity else CheckStatus.FAIL,
            _foreign_key_fingerprint(restored_inventory),
        )

        chroma = _verify_chroma(
            disposable,
            _chroma_aliases(inventory_manifest),
            hmac_key,
        )
        base_checks["chroma_counts"] = _check(
            "chroma_counts", chroma.count_status, chroma.count_fingerprint
        )
        base_checks["retrieval_parity"] = _check(
            "retrieval_parity", chroma.retrieval_status, chroma.fingerprint
        )
        return _result(
            inventory_manifest,
            disposable,
            created,
            base_checks,
            source_unchanged=source_unchanged,
            foreign_key_parity=fk_parity,
            retrieval_parity=chroma.retrieval_status is CheckStatus.PASS,
            collection_count=chroma.collection_count,
            record_count=chroma.record_count,
            retrieval_fixture_count=chroma.fixture_count,
            retrieval_fingerprint=chroma.fingerprint,
        )


@dataclass(frozen=True, slots=True)
class _ChromaEvidence:
    count_status: CheckStatus
    retrieval_status: CheckStatus
    collection_count: int
    record_count: int
    fixture_count: int
    count_fingerprint: str
    fingerprint: str


def _verify_chroma(
    disposable: Path, aliases: tuple[str, ...], hmac_key: bytes
) -> _ChromaEvidence:
    """Open Chroma only here, after the durable evidence has a second copy."""
    import chromadb

    count_digest = hmac.new(hmac_key, digestmod=hashlib.sha256)
    retrieval_digest = hmac.new(hmac_key, digestmod=hashlib.sha256)
    collection_total = 0
    record_total = 0
    fixture_total = 0
    count_status = CheckStatus.PASS
    retrieval_status = CheckStatus.PASS
    try:
        for root_ordinal, alias in enumerate(aliases):
            client = chromadb.PersistentClient(path=str(disposable / alias))
            listed = client.list_collections()
            names = sorted(
                item if isinstance(item, str) else item.name for item in listed
            )
            collection_total += len(names)
            for collection_ordinal, name in enumerate(names):
                collection = client.get_collection(name)
                api_count = collection.count()
                identities = collection.get(include=[])["ids"]
                actual_count = len(identities)
                count_digest.update(
                    json.dumps(
                        (root_ordinal, collection_ordinal, api_count, actual_count),
                        separators=(",", ":"),
                    ).encode("utf-8")
                )
                count_digest.update(b"\n")
                record_total += actual_count
                if api_count != actual_count:
                    count_status = CheckStatus.FAIL
                    retrieval_status = CheckStatus.NOT_RUN
                    continue
                if actual_count == 0:
                    continue

                selected = sorted(str(identity) for identity in identities)[0]
                record = collection.get(ids=[selected], include=["embeddings"])
                embeddings = record.get("embeddings")
                if embeddings is None or len(embeddings) != 1:
                    retrieval_status = CheckStatus.BLOCKED
                    continue
                embedding = embeddings[0]
                query = collection.query(
                    query_embeddings=[embedding],
                    n_results=min(5, actual_count),
                    include=["distances"],
                )
                result_ids = query.get("ids")
                distances = query.get("distances")
                if (
                    not result_ids
                    or not result_ids[0]
                    or distances is None
                    or not distances[0]
                    or str(result_ids[0][0]) != selected
                    or len(result_ids[0]) != len(distances[0])
                ):
                    retrieval_status = CheckStatus.FAIL
                    continue
                fixture_total += 1
                for result_ordinal, (identity, distance) in enumerate(
                    zip(result_ids[0], distances[0], strict=True)
                ):
                    numeric_distance = float(distance)
                    if not math.isfinite(numeric_distance):
                        retrieval_status = CheckStatus.FAIL
                        break
                    retrieval_digest.update(
                        json.dumps(
                            (
                                root_ordinal,
                                collection_ordinal,
                                result_ordinal,
                                str(identity),
                                format(numeric_distance, ".17g"),
                            ),
                            separators=(",", ":"),
                            ensure_ascii=True,
                        ).encode("utf-8")
                    )
                    retrieval_digest.update(b"\n")
    except Exception:
        if count_status is CheckStatus.PASS:
            retrieval_status = CheckStatus.BLOCKED

    if fixture_total == 0 and retrieval_status is CheckStatus.PASS:
        retrieval_status = CheckStatus.NOT_RUN
    return _ChromaEvidence(
        count_status=count_status,
        retrieval_status=retrieval_status,
        collection_count=collection_total,
        record_count=record_total,
        fixture_count=fixture_total,
        count_fingerprint=count_digest.hexdigest(),
        fingerprint=retrieval_digest.hexdigest(),
    )


def _result(
    inventory: InventoryManifest,
    disposable: Path,
    created: str,
    checks_by_name: dict[str, EvidenceCheck],
    *,
    source_unchanged: bool,
    foreign_key_parity: bool,
    retrieval_parity: bool,
    collection_count: int = 0,
    record_count: int = 0,
    retrieval_fixture_count: int = 0,
    retrieval_fingerprint: str = "",
) -> RestoreResult:
    required = (
        "source_unchanged",
        "backup_hash_parity",
        "restore_copy_parity",
        "sqlite_integrity",
        "foreign_key_parity",
        "chroma_counts",
        "retrieval_parity",
    )
    checks = tuple(
        checks_by_name.get(name, _check(name, CheckStatus.NOT_RUN, ""))
        for name in required
    )
    states = {item.status for item in checks}
    if CheckStatus.FAIL in states:
        status = CheckStatus.FAIL
    elif CheckStatus.BLOCKED in states or CheckStatus.NOT_RUN in states:
        status = CheckStatus.BLOCKED
    else:
        status = CheckStatus.PASS
    return RestoreResult(
        status=status,
        checks=checks,
        disposable_path=disposable,
        run_id=inventory.run_id,
        source_set_sha256=inventory.source_set_sha256,
        created_at_utc=created,
        tool_commit=inventory.tool_commit,
        source_unchanged=source_unchanged,
        foreign_key_parity=foreign_key_parity,
        retrieval_parity=retrieval_parity,
        collection_count=collection_count,
        record_count=record_count,
        retrieval_fixture_count=retrieval_fixture_count,
        retrieval_fingerprint=retrieval_fingerprint,
    )


def _early_failure(
    backup: BackupResult,
    inventory: InventoryManifest,
    disposable: Path,
    created: str,
    source_unchanged: bool,
    checks: dict[str, EvidenceCheck],
    failed_check: str,
) -> RestoreResult:
    checks[failed_check] = _check(failed_check, CheckStatus.FAIL, "")
    return _result(
        inventory,
        disposable,
        created,
        checks,
        source_unchanged=source_unchanged,
        foreign_key_parity=False,
        retrieval_parity=False,
    )


def _foreign_key_facts(manifest: InventoryManifest) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            root.alias,
            root.role.value,
            item.relative_path,
            item.foreign_key_status.value,
            item.foreign_key_violation_count,
            item.foreign_key_fingerprint,
            item.reason_code,
        )
        for root in sorted(manifest.roots, key=lambda value: value.alias)
        for item in sorted(root.databases, key=lambda value: value.relative_path)
    )


def _foreign_key_fingerprint(manifest: InventoryManifest) -> str:
    return hashlib.sha256(
        json.dumps(_foreign_key_facts(manifest), separators=(",", ":")).encode()
    ).hexdigest()


def _sqlite_fingerprint(manifest: InventoryManifest) -> str:
    return hashlib.sha256(
        json.dumps(_sqlite_facts(manifest), separators=(",", ":")).encode()
    ).hexdigest()


def _sqlite_facts(manifest: InventoryManifest) -> tuple[tuple[Any, ...], ...]:
    """Return role-bound SQLite facts required to match after restoration."""
    return tuple(
        (
            root.alias,
            root.role.value,
            item.relative_path,
            item.integrity_status.value,
            item.integrity_result,
            item.reason_code,
        )
        for root in sorted(manifest.roots, key=lambda value: value.alias)
        for item in sorted(root.databases, key=lambda value: value.relative_path)
    )


def _sqlite_expectations_are_licensed(manifest: InventoryManifest) -> bool:
    """License PASS, plus the one explicit archive-only N/A classification."""
    return all(
        item.integrity_status is CheckStatus.PASS
        or (
            root.role.value == "archive"
            and item.integrity_status is CheckStatus.NOT_APPLICABLE
            and item.foreign_key_status is CheckStatus.NOT_APPLICABLE
            and item.reason_code == "preserved_non_sqlite_archive"
        )
        for root in manifest.roots
        for item in root.databases
    )


def _chroma_aliases(manifest: InventoryManifest) -> tuple[str, ...]:
    """Open only restored roots with a structurally valid Chroma SQLite file."""
    return tuple(
        root.alias
        for root in sorted(manifest.roots, key=lambda value: value.alias)
        if any(
            item.integrity_status is CheckStatus.PASS
            and Path(item.relative_path).name == "chroma.sqlite3"
            for item in root.databases
        )
    )


def _check(name: str, status: CheckStatus, evidence: str) -> EvidenceCheck:
    return EvidenceCheck(
        name=name,
        status=status,
        evidence_sha256=hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
    )
