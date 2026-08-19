"""Fail-closed, no-follow copying for complete Aura persistence roots.

The module intentionally has no deletion or rotation operation.  A failed copy
keeps its ``.partial`` directory for diagnosis and a successful copy is exposed
only through an atomic rename after source-before/source-after/destination parity.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aura_backend.preservation.manifest import (
    CheckStatus,
    EvidenceCheck,
    InventoryManifest,
)


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class BackupBlocked(RuntimeError):
    """A preservation safety precondition or parity gate did not pass."""


@dataclass(frozen=True, slots=True, order=True)
class FileSnapshot:
    """Content and stable metadata for one regular file in a source set."""

    root_alias: str
    relative_path: str
    byte_size: int
    mtime_ns: int
    sha256: str


@dataclass(frozen=True, slots=True)
class TreeManifest:
    """Deterministically ordered full-root file evidence."""

    files: tuple[FileSnapshot, ...]
    sha256: str


@dataclass(frozen=True, slots=True)
class QuiescenceTicket:
    """Short-lived evidence authorizing one immutable source-set copy."""

    ticket_id: str
    status: CheckStatus
    issued_at_utc: datetime
    expires_at_utc: datetime
    destination_parent: Path
    source_set_sha256: str
    inventory_source_set_sha256: str
    checks: tuple[EvidenceCheck, ...]


@dataclass(frozen=True, slots=True)
class BackupResult:
    """Completed copy evidence returned only after atomic finalization."""

    status: CheckStatus
    destination: Path
    partial_destination: Path
    source_before: TreeManifest
    source_after: TreeManifest
    destination_manifest: TreeManifest


def issue_quiescence_ticket(
    source_roots: Mapping[str, Path],
    backup_root: Path,
    *,
    ttl_seconds: int = 900,
    inventory_manifest: InventoryManifest | None = None,
    open_handles: tuple[str, ...] = (),
    now: datetime | None = None,
) -> QuiescenceTicket:
    """Issue a short-lived ticket after static copy preconditions pass.

    Real CLI preflight supplies open-handle evidence.  Tests can exercise the
    same immutable ticket contract without starting or inspecting live Aura.
    """
    if ttl_seconds <= 0:
        raise ValueError("ticket TTL must be positive")
    normalized_sources, normalized_backup = validate_copy_paths(
        source_roots, backup_root
    )
    snapshot = snapshot_roots(normalized_sources)
    if inventory_manifest is not None:
        if inventory_manifest.status is not CheckStatus.PASS:
            raise BackupBlocked("inventory manifest must be passing")
        inventory_source_set = inventory_manifest.source_set_sha256
    else:
        inventory_source_set = snapshot.sha256

    checks = (
        _check("path_disjointness", CheckStatus.PASS, normalized_backup.as_posix()),
        _check("source_snapshot", CheckStatus.PASS, snapshot.sha256),
        _check(
            "open_handles",
            CheckStatus.BLOCKED if open_handles else CheckStatus.PASS,
            "\n".join(open_handles),
        ),
    )
    status = (
        CheckStatus.PASS
        if all(item.status is CheckStatus.PASS for item in checks)
        else CheckStatus.BLOCKED
    )
    issued = _as_utc(now or datetime.now(UTC))
    return QuiescenceTicket(
        ticket_id=uuid.uuid4().hex,
        status=status,
        issued_at_utc=issued,
        expires_at_utc=issued + timedelta(seconds=ttl_seconds),
        destination_parent=normalized_backup,
        source_set_sha256=snapshot.sha256,
        inventory_source_set_sha256=inventory_source_set,
        checks=checks,
    )


def copy_from_ticket(
    source_roots: Mapping[str, Path],
    backup_root: Path,
    destination_name: str,
    ticket: QuiescenceTicket,
    *,
    now: datetime | None = None,
) -> BackupResult:
    """Copy complete roots and expose the destination only after exact parity."""
    if not _SAFE_NAME.fullmatch(destination_name) or destination_name.endswith(
        ".partial"
    ):
        raise ValueError("destination name contains unsupported characters")

    normalized_sources, normalized_backup = validate_copy_paths(
        source_roots, backup_root
    )
    current_time = _as_utc(now or datetime.now(UTC))
    if ticket.status is not CheckStatus.PASS:
        raise BackupBlocked("copy requires a passing quiescence ticket")
    if any(item.status is not CheckStatus.PASS for item in ticket.checks):
        raise BackupBlocked("every required check in the ticket must pass")
    if current_time >= _as_utc(ticket.expires_at_utc):
        raise BackupBlocked("quiescence ticket has expired")
    if ticket.destination_parent != normalized_backup:
        raise BackupBlocked("ticket destination does not match the backup root")

    destination = normalized_backup / destination_name
    partial = normalized_backup / f"{destination_name}.partial"
    _ensure_new_destination(destination, partial)
    source_before = snapshot_roots(normalized_sources)
    if source_before.sha256 != ticket.source_set_sha256:
        raise BackupBlocked("source changed after the quiescence ticket was issued")

    # Claim the partial directory exclusively.  It remains in place on any
    # subsequent failure; preservation evidence is never deleted automatically.
    partial.mkdir(mode=0o700)
    try:
        for alias, source in sorted(normalized_sources.items()):
            target = partial / alias
            target.mkdir(mode=0o700)
            _copy_directory(source, target)
        source_after = snapshot_roots(normalized_sources)
        destination_manifest = snapshot_roots(
            {alias: partial / alias for alias in normalized_sources}
        )
    except BackupBlocked:
        raise
    except OSError as error:
        raise BackupBlocked("copy was blocked by an I/O error") from error

    if source_before != source_after:
        raise BackupBlocked("source changed during copy")
    if source_before != destination_manifest:
        raise BackupBlocked("destination does not exactly match the source")

    partial.rename(destination)
    return BackupResult(
        status=CheckStatus.PASS,
        destination=destination,
        partial_destination=partial,
        source_before=source_before,
        source_after=source_after,
        destination_manifest=destination_manifest,
    )


def validate_copy_paths(
    source_roots: Mapping[str, Path], backup_root: Path
) -> tuple[dict[str, Path], Path]:
    """Resolve roots without permitting links or ancestor/descendant overlap."""
    if not source_roots:
        raise ValueError("at least one source root is required")
    if len(set(source_roots)) != len(source_roots):
        raise ValueError("source aliases must be unique")
    for alias in source_roots:
        if not _SAFE_NAME.fullmatch(alias):
            raise ValueError("source alias contains unsupported characters")

    _reject_symlink_components(backup_root)
    normalized_backup = backup_root.resolve(strict=True)
    if not normalized_backup.is_dir():
        raise BackupBlocked("backup root must be a directory")
    normalized_sources: dict[str, Path] = {}
    for alias, raw_source in source_roots.items():
        _reject_symlink_components(raw_source)
        source = raw_source.resolve(strict=True)
        if not source.is_dir():
            raise BackupBlocked("every source root must be a directory")
        normalized_sources[alias] = source

    all_paths = [*normalized_sources.values(), normalized_backup]
    for index, left in enumerate(all_paths):
        for right in all_paths[index + 1 :]:
            if _paths_overlap(left, right):
                raise BackupBlocked("source and backup paths must be disjoint")
    return normalized_sources, normalized_backup


def snapshot_roots(source_roots: Mapping[str, Path]) -> TreeManifest:
    """Hash all and only regular files without following directory entries."""
    files: list[FileSnapshot] = []
    for alias, root in sorted(source_roots.items()):
        _scan_snapshot(alias, root, root, files)
    files.sort()
    digest = hashlib.sha256()
    for item in files:
        digest.update(
            json.dumps(
                (
                    item.root_alias,
                    item.relative_path,
                    item.byte_size,
                    item.mtime_ns,
                    item.sha256,
                ),
                separators=(",", ":"),
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return TreeManifest(tuple(files), digest.hexdigest())


def _scan_snapshot(
    alias: str, directory: Path, root: Path, files: list[FileSnapshot]
) -> None:
    try:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda item: item.name)
    except OSError as error:
        raise BackupBlocked("source directory could not be scanned") from error
    for entry in ordered:
        path = Path(entry.path)
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError as error:
            raise BackupBlocked("source entry could not be inspected") from error
        if stat.S_ISDIR(entry_stat.st_mode):
            _scan_snapshot(alias, path, root, files)
        elif stat.S_ISREG(entry_stat.st_mode):
            files.append(
                FileSnapshot(
                    root_alias=alias,
                    relative_path=path.relative_to(root).as_posix(),
                    byte_size=entry_stat.st_size,
                    mtime_ns=entry_stat.st_mtime_ns,
                    sha256=_hash_regular_file(path, entry_stat),
                )
            )
        else:
            raise BackupBlocked("source persistence roots may contain only regular files")


def _copy_directory(source: Path, destination: Path) -> None:
    with os.scandir(source) as entries:
        ordered = sorted(entries, key=lambda item: item.name)
    for entry in ordered:
        source_path = Path(entry.path)
        destination_path = destination / entry.name
        entry_stat = entry.stat(follow_symlinks=False)
        if stat.S_ISDIR(entry_stat.st_mode):
            destination_path.mkdir(mode=stat.S_IMODE(entry_stat.st_mode) or 0o700)
            _copy_directory(source_path, destination_path)
            os.utime(
                destination_path,
                ns=(entry_stat.st_atime_ns, entry_stat.st_mtime_ns),
                follow_symlinks=False,
            )
            continue
        if not stat.S_ISREG(entry_stat.st_mode):
            raise BackupBlocked("source persistence roots may contain only regular files")
        _copy_regular_file(source_path, destination_path, entry_stat)


def _copy_regular_file(
    source: Path, destination: Path, before: os.stat_result
) -> None:
    read_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    write_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    try:
        source_descriptor = os.open(source, read_flags)
        destination_descriptor = os.open(
            destination, write_flags, stat.S_IMODE(before.st_mode) or 0o600
        )
        with os.fdopen(source_descriptor, "rb") as source_stream, os.fdopen(
            destination_descriptor, "wb"
        ) as destination_stream:
            opened = os.fstat(source_stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or not _same_identity(before, opened):
                raise BackupBlocked("source changed before it could be copied")
            shutil.copyfileobj(source_stream, destination_stream, length=1024 * 1024)
            destination_stream.flush()
            os.fsync(destination_stream.fileno())
            after_descriptor = os.fstat(source_stream.fileno())
        after_path = source.lstat()
    except OSError as error:
        raise BackupBlocked("regular file copy was blocked") from error
    if not _same_version(before, after_descriptor) or not _same_version(
        before, after_path
    ):
        raise BackupBlocked("source changed while a file was being copied")
    os.utime(
        destination,
        ns=(before.st_atime_ns, before.st_mtime_ns),
        follow_symlinks=False,
    )


def _hash_regular_file(path: Path, before: os.stat_result) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or not _same_identity(before, opened):
                raise BackupBlocked("source changed before hashing")
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            after_descriptor = os.fstat(stream.fileno())
        after_path = path.lstat()
    except OSError as error:
        raise BackupBlocked("regular file hashing was blocked") from error
    if not _same_version(before, after_descriptor) or not _same_version(
        before, after_path
    ):
        raise BackupBlocked("source changed while hashing")
    return digest


def _ensure_new_destination(destination: Path, partial: Path) -> None:
    for path in (destination, partial):
        if path.exists() or path.is_symlink():
            raise BackupBlocked("backup destination and partial path must be new")


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            component_stat = current.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise BackupBlocked("path component could not be inspected") from error
        if stat.S_ISLNK(component_stat.st_mode):
            raise BackupBlocked("path contains a symlink component")


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _same_version(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        _same_identity(left, right)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def _check(name: str, status: CheckStatus, evidence: str) -> EvidenceCheck:
    return EvidenceCheck(
        name=name,
        status=status,
        evidence_sha256=hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("ticket timestamps must be timezone-aware")
    return value.astimezone(UTC)
