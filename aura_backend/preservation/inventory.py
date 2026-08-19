"""Read-only, no-follow filesystem and SQLite preservation inventory."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import stat
import subprocess
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from aura_backend.preservation.manifest import (
    CheckStatus,
    DatabaseEvidence,
    FileEvidence,
    InventoryManifest,
    RootDeclaration,
    RootEvidence,
)

_SQLITE_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3"})


def inventory_roots(
    repository_root: Path,
    declarations: Iterable[RootDeclaration],
    *,
    hmac_key: bytes | None = None,
    run_id: str | None = None,
    tool_commit: str | None = None,
) -> InventoryManifest:
    """Inventory declared roots without copying, modifying, or following data.

    Args:
        repository_root: Trusted repository directory containing declared roots.
        declarations: Typed, repository-relative roots and their evidence roles.
        hmac_key: Optional deterministic key for tests; production uses randomness.
        run_id: Optional caller-provided evidence identifier.
        tool_commit: Optional Git revision describing the inventory implementation.

    Returns:
        A typed private manifest whose public serializer can safely aggregate it.
    """
    root_path = repository_root.resolve(strict=True)
    if not root_path.is_dir():
        raise ValueError("repository root must be a directory")

    declared = tuple(declarations)
    aliases = [item.alias for item in declared]
    if len(set(aliases)) != len(aliases):
        raise ValueError("inventory root aliases must be unique")

    key = hmac_key if hmac_key is not None else secrets.token_bytes(32)
    if len(key) < 16:
        raise ValueError("inventory HMAC key must contain at least 16 bytes")

    roots = tuple(_inventory_root(root_path, item, key) for item in declared)
    status = _manifest_status(roots)
    source_set_sha256 = _source_set_digest(roots)
    return InventoryManifest(
        roots=roots,
        status=status,
        source_set_sha256=source_set_sha256,
        hmac_key_hex=key.hex(),
        run_id=run_id or uuid.uuid4().hex,
        created_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        tool_commit=tool_commit or _current_git_commit(root_path),
    )


def _inventory_root(
    repository_root: Path,
    declaration: RootDeclaration,
    hmac_key: bytes,
) -> RootEvidence:
    path = repository_root.joinpath(*Path(declaration.repository_relative_path).parts)
    try:
        root_stat = path.lstat()
    except FileNotFoundError:
        missing_status = CheckStatus.BLOCKED if declaration.required else CheckStatus.NOT_RUN
        return _empty_root(
            declaration,
            missing_status,
            "missing_required_root" if declaration.required else "missing_optional_root",
        )
    except OSError as error:
        return _empty_root(declaration, CheckStatus.BLOCKED, "root_lstat_failed", error)

    if stat.S_ISLNK(root_stat.st_mode):
        return _empty_root(declaration, CheckStatus.BLOCKED, "root_is_symlink")
    if not stat.S_ISDIR(root_stat.st_mode):
        return _empty_root(declaration, CheckStatus.BLOCKED, "root_is_not_directory")

    files: list[FileEvidence] = []
    databases: list[DatabaseEvidence] = []
    _scan_directory(path, path, declaration, hmac_key, files, databases)
    files.sort(key=lambda item: item.relative_path)
    databases.sort(key=lambda item: item.relative_path)
    root_status = _root_status(files, databases)
    return RootEvidence(
        alias=declaration.alias,
        repository_relative_path=declaration.repository_relative_path,
        role=declaration.role,
        required=declaration.required,
        status=root_status,
        files=tuple(files),
        databases=tuple(databases),
        file_count=len(files),
        byte_total=sum(item.byte_size for item in files if item.file_type == "regular"),
        aggregate_sha256=_aggregate_digest(files, databases),
    )


def _scan_directory(
    directory: Path,
    root: Path,
    declaration: RootDeclaration,
    hmac_key: bytes,
    files: list[FileEvidence],
    databases: list[DatabaseEvidence],
) -> None:
    """Recursively scan a real directory without following directory entries."""
    try:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda item: item.name)
    except OSError as error:
        files.append(
            _blocked_entry(
                directory,
                root,
                declaration,
                "directory",
                "directory_scan_failed",
                error,
            )
        )
        return

    for entry in ordered:
        path = Path(entry.path)
        relative_path = path.relative_to(root).as_posix()
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError as error:
            files.append(
                FileEvidence(
                    relative_path=relative_path,
                    role=declaration.role,
                    byte_size=0,
                    mtime_ns=0,
                    file_type="unknown",
                    status=CheckStatus.BLOCKED,
                    private_error_code="entry_lstat_failed",
                    private_error=str(error),
                )
            )
            continue

        mode = entry_stat.st_mode
        if stat.S_ISDIR(mode):
            _scan_directory(path, root, declaration, hmac_key, files, databases)
            continue
        if not stat.S_ISREG(mode):
            files.append(
                FileEvidence(
                    relative_path=relative_path,
                    role=declaration.role,
                    byte_size=entry_stat.st_size,
                    mtime_ns=entry_stat.st_mtime_ns,
                    file_type=_file_type(mode),
                    status=CheckStatus.BLOCKED,
                    private_error_code="unsupported_entry_type",
                )
            )
            continue

        file_evidence = _hash_regular_file(path, relative_path, declaration, entry_stat)
        files.append(file_evidence)
        if file_evidence.status is not CheckStatus.PASS:
            continue
        if path.suffix.lower() not in _SQLITE_SUFFIXES:
            continue

        database_evidence = _inspect_sqlite(path, relative_path, hmac_key)
        databases.append(database_evidence)
        try:
            after_database_stat = path.lstat()
        except OSError:
            after_database_stat = None
        if after_database_stat is None or not _same_file_version(
            entry_stat, after_database_stat
        ):
            files[-1] = FileEvidence(
                relative_path=relative_path,
                role=declaration.role,
                byte_size=entry_stat.st_size,
                mtime_ns=entry_stat.st_mtime_ns,
                file_type="regular",
                status=CheckStatus.FAIL,
                private_error_code="file_changed_during_database_check",
            )
            databases[-1] = DatabaseEvidence(
                relative_path=relative_path,
                integrity_status=CheckStatus.FAIL,
                integrity_result="unstable",
                foreign_key_status=CheckStatus.FAIL,
                foreign_key_violation_count=database_evidence.foreign_key_violation_count,
                foreign_key_fingerprint=database_evidence.foreign_key_fingerprint,
                private_error_code="file_changed_during_database_check",
            )


def _hash_regular_file(
    path: Path,
    relative_path: str,
    declaration: RootDeclaration,
    before: os.stat_result,
) -> FileEvidence:
    """Hash one descriptor and reject replacement or mutation races."""
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or not _same_identity(before, opened):
                return _failed_file(
                    relative_path, declaration, before, "file_replaced_before_hash"
                )
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            after_descriptor = os.fstat(stream.fileno())
        after_path = path.lstat()
    except OSError as error:
        return _failed_file(
            relative_path,
            declaration,
            before,
            "file_hash_blocked",
            CheckStatus.BLOCKED,
            error,
        )

    if not _same_file_version(before, after_descriptor) or not _same_file_version(
        before, after_path
    ):
        return _failed_file(
            relative_path, declaration, before, "file_changed_during_hash"
        )
    return FileEvidence(
        relative_path=relative_path,
        role=declaration.role,
        byte_size=before.st_size,
        mtime_ns=before.st_mtime_ns,
        file_type="regular",
        status=CheckStatus.PASS,
        sha256=digest,
    )


def _inspect_sqlite(path: Path, relative_path: str, hmac_key: bytes) -> DatabaseEvidence:
    """Run full structural and FK checks through a read-only SQLite URI."""
    fingerprint = hmac.new(hmac_key, digestmod=hashlib.sha256)
    connection: sqlite3.Connection | None = None
    try:
        uri = f"{path.absolute().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only = ON")
        integrity_rows = tuple(
            str(row[0]) for row in connection.execute("PRAGMA integrity_check")
        )
        foreign_key_count = 0
        for row in connection.execute("PRAGMA foreign_key_check"):
            fingerprint.update(
                json.dumps(tuple(row), separators=(",", ":"), ensure_ascii=True).encode()
            )
            fingerprint.update(b"\n")
            foreign_key_count += 1
    except (OSError, sqlite3.Error) as error:
        return DatabaseEvidence(
            relative_path=relative_path,
            integrity_status=CheckStatus.FAIL,
            integrity_result="error",
            foreign_key_status=CheckStatus.NOT_RUN,
            foreign_key_violation_count=0,
            foreign_key_fingerprint=fingerprint.hexdigest(),
            private_error_code="sqlite_read_only_check_failed",
            private_error=str(error),
        )
    finally:
        if connection is not None:
            connection.close()

    integrity_passed = integrity_rows == ("ok",)
    return DatabaseEvidence(
        relative_path=relative_path,
        integrity_status=CheckStatus.PASS if integrity_passed else CheckStatus.FAIL,
        integrity_result="ok" if integrity_passed else "errors",
        foreign_key_status=CheckStatus.PASS,
        foreign_key_violation_count=foreign_key_count,
        foreign_key_fingerprint=fingerprint.hexdigest(),
        private_integrity_results=integrity_rows,
    )


def _file_type(mode: int) -> str:
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISBLK(mode):
        return "block_device"
    if stat.S_ISCHR(mode):
        return "character_device"
    return "unknown"


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _same_file_version(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        _same_identity(left, right)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def _failed_file(
    relative_path: str,
    declaration: RootDeclaration,
    file_stat: os.stat_result,
    error_code: str,
    status: CheckStatus = CheckStatus.FAIL,
    error: OSError | None = None,
) -> FileEvidence:
    return FileEvidence(
        relative_path=relative_path,
        role=declaration.role,
        byte_size=file_stat.st_size,
        mtime_ns=file_stat.st_mtime_ns,
        file_type="regular",
        status=status,
        private_error_code=error_code,
        private_error=str(error) if error is not None else None,
    )


def _blocked_entry(
    path: Path,
    root: Path,
    declaration: RootDeclaration,
    file_type: str,
    error_code: str,
    error: OSError,
) -> FileEvidence:
    return FileEvidence(
        relative_path=path.relative_to(root).as_posix() or ".",
        role=declaration.role,
        byte_size=0,
        mtime_ns=0,
        file_type=file_type,
        status=CheckStatus.BLOCKED,
        private_error_code=error_code,
        private_error=str(error),
    )


def _empty_root(
    declaration: RootDeclaration,
    status: CheckStatus,
    error_code: str,
    error: OSError | None = None,
) -> RootEvidence:
    aggregate = hashlib.sha256(
        f"{declaration.alias}:{declaration.repository_relative_path}:{status.value}".encode()
    ).hexdigest()
    return RootEvidence(
        alias=declaration.alias,
        repository_relative_path=declaration.repository_relative_path,
        role=declaration.role,
        required=declaration.required,
        status=status,
        aggregate_sha256=aggregate,
        private_error_code=error_code,
        private_error=str(error) if error is not None else None,
    )


def _root_status(
    files: Iterable[FileEvidence], databases: Iterable[DatabaseEvidence]
) -> CheckStatus:
    statuses = [item.status for item in files]
    statuses.extend(item.integrity_status for item in databases)
    statuses.extend(item.foreign_key_status for item in databases)
    if CheckStatus.FAIL in statuses:
        return CheckStatus.FAIL
    if CheckStatus.BLOCKED in statuses or CheckStatus.NOT_RUN in statuses:
        return CheckStatus.BLOCKED
    return CheckStatus.PASS


def _manifest_status(roots: Iterable[RootEvidence]) -> CheckStatus:
    material = [
        root.status
        for root in roots
        if root.required or root.status is not CheckStatus.NOT_RUN
    ]
    if CheckStatus.FAIL in material:
        return CheckStatus.FAIL
    if CheckStatus.BLOCKED in material or CheckStatus.NOT_RUN in material:
        return CheckStatus.BLOCKED
    return CheckStatus.PASS


def _aggregate_digest(
    files: Iterable[FileEvidence], databases: Iterable[DatabaseEvidence]
) -> str:
    digest = hashlib.sha256()
    for item in files:
        public_facts = (
            item.relative_path,
            item.role.value,
            item.byte_size,
            item.mtime_ns,
            item.file_type,
            item.status.value,
            item.sha256,
        )
        digest.update(json.dumps(public_facts, separators=(",", ":")).encode())
        digest.update(b"\n")
    for item in databases:
        public_facts = (
            item.relative_path,
            item.integrity_status.value,
            item.integrity_result,
            item.foreign_key_status.value,
            item.foreign_key_violation_count,
            item.foreign_key_fingerprint,
        )
        digest.update(json.dumps(public_facts, separators=(",", ":")).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _source_set_digest(roots: Iterable[RootEvidence]) -> str:
    digest = hashlib.sha256()
    for root in roots:
        facts = (
            root.alias,
            root.repository_relative_path,
            root.role.value,
            root.required,
            root.status.value,
            root.aggregate_sha256,
        )
        digest.update(json.dumps(facts, separators=(",", ":")).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _current_git_commit(repository_root: Path) -> str:
    """Return the current commit without making Git a runtime requirement."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"
