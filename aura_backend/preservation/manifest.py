"""Typed evidence records for Aura's preservation inventory.

The records deliberately distinguish required checks that passed, failed, were
blocked, or did not run.  Serialization into private and committable lanes lives
on :class:`InventoryManifest` and is added by the privacy-facing CLI layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


SCHEMA_VERSION = 1
TOOL_VERSION = "0.1.0"
_SAFE_ALIAS = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class CheckStatus(str, Enum):
    """Truthful result states for preservation evidence."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class RootRole(str, Enum):
    """Supported persistence-root classifications."""

    ACTIVE = "active"
    BACKUP = "backup"
    TEST = "test"
    ARCHIVE = "archive"


@dataclass(frozen=True, slots=True)
class RootDeclaration:
    """A repository-relative root that should be inventoried."""

    alias: str
    repository_relative_path: str
    role: RootRole
    required: bool = True

    def __post_init__(self) -> None:
        """Reject aliases and paths that could escape the declared repository."""
        from pathlib import PurePath

        if not _SAFE_ALIAS.fullmatch(self.alias):
            raise ValueError("root alias must contain only safe lowercase characters")
        path = PurePath(self.repository_relative_path)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise ValueError("inventory root must be a repository-relative path")


@dataclass(frozen=True, slots=True)
class FileEvidence:
    """Metadata-only evidence for one filesystem entry."""

    relative_path: str
    role: RootRole
    byte_size: int
    mtime_ns: int
    file_type: str
    status: CheckStatus
    sha256: str | None = None
    private_error_code: str | None = None
    private_error: str | None = None


@dataclass(frozen=True, slots=True)
class DatabaseEvidence:
    """Independent structural and foreign-key evidence for one SQLite file."""

    relative_path: str
    integrity_status: CheckStatus
    integrity_result: str
    foreign_key_status: CheckStatus
    foreign_key_violation_count: int
    foreign_key_fingerprint: str
    private_integrity_results: tuple[str, ...] = ()
    private_error_code: str | None = None
    private_error: str | None = None


@dataclass(frozen=True, slots=True)
class RootEvidence:
    """Inventory evidence and deterministic aggregates for one declared root."""

    alias: str
    repository_relative_path: str
    role: RootRole
    required: bool
    status: CheckStatus
    files: tuple[FileEvidence, ...] = ()
    databases: tuple[DatabaseEvidence, ...] = ()
    file_count: int = 0
    byte_total: int = 0
    aggregate_sha256: str = ""
    private_error_code: str | None = None
    private_error: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceCheck:
    """Opaque public evidence that a named check reached a truthful state."""

    name: str
    status: CheckStatus
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class InventoryManifest:
    """Versioned result of inventorying a complete declared source set."""

    roots: tuple[RootEvidence, ...]
    status: CheckStatus
    source_set_sha256: str
    hmac_key_hex: str = field(repr=False)
    run_id: str
    created_at_utc: str
    tool_commit: str = "unknown"
    schema_version: int = SCHEMA_VERSION
    tool_version: str = TOOL_VERSION
    command: str = "inventory"

    @property
    def checks(self) -> tuple[EvidenceCheck, ...]:
        """Return one opaque status check per declared root."""
        return tuple(
            EvidenceCheck(
                name=f"root:{root.alias}",
                status=root.status,
                evidence_sha256=root.aggregate_sha256,
            )
            for root in self.roots
        )

