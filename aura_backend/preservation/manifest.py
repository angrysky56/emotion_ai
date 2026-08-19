"""Typed evidence records for Aura's preservation inventory.

The records deliberately distinguish required checks that passed, failed, were
blocked, or did not run.  Serialization into private and committable lanes lives
on :class:`InventoryManifest` and is added by the privacy-facing CLI layer.
"""

from __future__ import annotations

import re
import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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

    def to_private_dict(self) -> dict[str, Any]:
        """Serialize complete evidence for private storage outside Git."""
        return {
            **self._common_fields(),
            "hmac_key_hex": self.hmac_key_hex,
            "roots": [self._private_root(root) for root in self.roots],
        }

    def to_public_summary(
        self,
        *,
        private_artifact_relpath: str,
        private_artifact_sha256: str,
    ) -> dict[str, Any]:
        """Serialize an explicit allowlist safe for a Git commit.

        This method constructs the public schema from aggregate facts.  It never
        starts from the private dictionary and therefore cannot accidentally leave
        behind a newly added sensitive field.
        """
        roots = [self._public_root(root) for root in self.roots]
        return {
            **self._common_fields(),
            "root_roles": sorted({root.role.value for root in self.roots}),
            "roots": roots,
            "totals": {
                "root_count": len(self.roots),
                "file_count": sum(root.file_count for root in self.roots),
                "byte_total": sum(root.byte_total for root in self.roots),
                "database_count": sum(len(root.databases) for root in self.roots),
                "anomaly_count": sum(_root_anomaly_count(root) for root in self.roots),
                "root_status_counts": _status_counts(root.status for root in self.roots),
            },
            "private_artifact_relpath": private_artifact_relpath,
            "private_artifact_sha256": private_artifact_sha256,
        }

    def _common_fields(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_version": self.tool_version,
            "command": self.command,
            "run_id": self.run_id,
            "status": self.status.value,
            "source_set_sha256": self.source_set_sha256,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "evidence_sha256": check.evidence_sha256,
                }
                for check in self.checks
            ],
            "created_at_utc": self.created_at_utc,
            "tool_commit": self.tool_commit,
        }

    @staticmethod
    def _private_root(root: RootEvidence) -> dict[str, Any]:
        return {
            "alias": root.alias,
            "repository_relative_path": root.repository_relative_path,
            "role": root.role.value,
            "required": root.required,
            "status": root.status.value,
            "file_count": root.file_count,
            "byte_total": root.byte_total,
            "aggregate_sha256": root.aggregate_sha256,
            "private_error_code": root.private_error_code,
            "private_error": root.private_error,
            "files": [
                {
                    "relative_path": item.relative_path,
                    "role": item.role.value,
                    "byte_size": item.byte_size,
                    "mtime_ns": item.mtime_ns,
                    "file_type": item.file_type,
                    "status": item.status.value,
                    "sha256": item.sha256,
                    "private_error_code": item.private_error_code,
                    "private_error": item.private_error,
                }
                for item in root.files
            ],
            "databases": [
                {
                    "relative_path": item.relative_path,
                    "integrity_status": item.integrity_status.value,
                    "integrity_result": item.integrity_result,
                    "foreign_key_status": item.foreign_key_status.value,
                    "foreign_key_violation_count": item.foreign_key_violation_count,
                    "foreign_key_fingerprint": item.foreign_key_fingerprint,
                    "private_integrity_results": list(item.private_integrity_results),
                    "private_error_code": item.private_error_code,
                    "private_error": item.private_error,
                }
                for item in root.databases
            ],
        }

    @staticmethod
    def _public_root(root: RootEvidence) -> dict[str, Any]:
        database_fingerprint = hashlib.sha256()
        for item in root.databases:
            database_fingerprint.update(item.foreign_key_fingerprint.encode("ascii"))
            database_fingerprint.update(b"\n")
        return {
            "alias": root.alias,
            "repository_relative_path": root.repository_relative_path,
            "role": root.role.value,
            "required": root.required,
            "status": root.status.value,
            "file_count": root.file_count,
            "byte_total": root.byte_total,
            "aggregate_sha256": root.aggregate_sha256,
            "database_checks": {
                "database_count": len(root.databases),
                "integrity_status_counts": _status_counts(
                    item.integrity_status for item in root.databases
                ),
                "foreign_key_status_counts": _status_counts(
                    item.foreign_key_status for item in root.databases
                ),
                "foreign_key_violation_count": sum(
                    item.foreign_key_violation_count for item in root.databases
                ),
                "foreign_key_fingerprint": database_fingerprint.hexdigest(),
            },
        }


def _status_counts(statuses: Iterable[CheckStatus]) -> dict[str, int]:
    """Return all status buckets so absence cannot masquerade as success."""
    counts = {status.value: 0 for status in CheckStatus}
    for status in statuses:
        counts[status.value] += 1
    return counts


def _root_anomaly_count(root: RootEvidence) -> int:
    file_anomalies = sum(item.status is not CheckStatus.PASS for item in root.files)
    database_anomalies = sum(
        item.integrity_status is not CheckStatus.PASS
        or item.foreign_key_status is not CheckStatus.PASS
        for item in root.databases
    )
    foreign_key_anomalies = sum(
        item.foreign_key_violation_count for item in root.databases
    )
    return file_anomalies + database_anomalies + foreign_key_anomalies
