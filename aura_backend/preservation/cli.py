"""Command-line interface for private and committable inventory evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from aura_backend.preservation.inventory import inventory_roots
from aura_backend.preservation.manifest import (
    CheckStatus,
    RootDeclaration,
    RootRole,
)

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_TOP_LEVEL_FIELDS = {
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
_PUBLIC_ROOT_FIELDS = {
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
_DATABASE_CHECK_FIELDS = {
    "database_count",
    "integrity_status_counts",
    "foreign_key_status_counts",
    "foreign_key_violation_count",
    "foreign_key_fingerprint",
}
_TOTAL_FIELDS = {
    "root_count",
    "file_count",
    "byte_total",
    "database_count",
    "anomaly_count",
    "root_status_counts",
}
_CHECK_FIELDS = {"name", "status", "evidence_sha256"}
_STATUS_FIELDS = {status.value for status in CheckStatus}


def build_parser() -> argparse.ArgumentParser:
    """Build the non-destructive preservation command parser."""
    parser = argparse.ArgumentParser(prog="aura-preservation")
    subcommands = parser.add_subparsers(dest="command", required=True)

    inventory = subcommands.add_parser(
        "inventory", description="Create read-only private and public inventory evidence"
    )
    inventory.add_argument("--repository-root", type=Path, required=True)
    inventory.add_argument("--backup-root", type=Path, required=True)
    inventory.add_argument("--run-id", required=True)
    inventory.add_argument("--private-manifest", type=Path, required=True)
    inventory.add_argument("--public-summary", type=Path, required=True)
    inventory.add_argument("--root", action="append", required=True, default=[])
    inventory.add_argument("--require-role", action="append", default=[])

    validate = subcommands.add_parser(
        "validate-summary", description="Validate a committable inventory summary"
    )
    validate.add_argument("--summary", type=Path, required=True)
    validate.add_argument("--require-role", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a preservation command and return a truthful process status."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "inventory":
            return _run_inventory(arguments)
        if arguments.command == "validate-summary":
            return _run_validate_summary(arguments)
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as error:
        print(
            f"preservation command failed ({type(error).__name__})",
            file=sys.stderr,
        )
        return 2
    parser.error("unknown preservation command")


def _run_inventory(arguments: argparse.Namespace) -> int:
    repository_root = arguments.repository_root.resolve(strict=True)
    if not repository_root.is_dir():
        raise ValueError("repository root must be a directory")
    if not _RUN_ID.fullmatch(arguments.run_id):
        raise ValueError("run ID contains unsupported characters")

    backup_root = arguments.backup_root.resolve(strict=False)
    private_manifest = arguments.private_manifest.resolve(strict=False)
    public_summary = arguments.public_summary.resolve(strict=False)
    if backup_root == repository_root or backup_root.is_relative_to(repository_root):
        raise ValueError("private output root must be outside the repository")
    if not private_manifest.is_relative_to(backup_root):
        raise ValueError("private manifest must stay beneath the backup root")
    if not public_summary.is_relative_to(repository_root):
        raise ValueError("public summary must stay beneath the repository root")
    if private_manifest.exists() or public_summary.exists():
        raise FileExistsError("inventory evidence output already exists")

    required_roles = _parse_roles(arguments.require_role)
    declarations = _parse_declarations(arguments.root, required_roles)
    if required_roles - {item.role for item in declarations}:
        raise ValueError("a required root role was not declared")

    manifest = inventory_roots(
        repository_root,
        declarations,
        run_id=arguments.run_id,
    )
    private_payload = _json_bytes(manifest.to_private_dict())
    private_digest = hashlib.sha256(private_payload).hexdigest()
    private_relpath = private_manifest.relative_to(backup_root).as_posix()
    public_payload = _json_bytes(
        manifest.to_public_summary(
            private_artifact_relpath=private_relpath,
            private_artifact_sha256=private_digest,
        )
    )
    _write_new_pair(
        private_manifest,
        private_payload,
        public_summary,
        public_payload,
    )
    return 0 if manifest.status is CheckStatus.PASS else 1


def _run_validate_summary(arguments: argparse.Namespace) -> int:
    with arguments.summary.open("r", encoding="utf-8") as stream:
        summary = json.load(stream)
    required_roles = _parse_roles(arguments.require_role)
    return 0 if _is_valid_public_summary(summary, required_roles) else 1


def _parse_roles(values: Sequence[str]) -> set[RootRole]:
    try:
        return {RootRole(value) for value in values}
    except ValueError as error:
        raise ValueError("unknown preservation root role") from error


def _parse_declarations(
    values: Sequence[str], required_roles: set[RootRole]
) -> tuple[RootDeclaration, ...]:
    counters: dict[RootRole, int] = {role: 0 for role in RootRole}
    declarations: list[RootDeclaration] = []
    for value in values:
        role_text, separator, relative_path = value.partition("=")
        if not separator or not relative_path:
            raise ValueError("root mapping must use ROLE=PATH")
        try:
            role = RootRole(role_text)
        except ValueError as error:
            raise ValueError("unknown preservation root role") from error
        counters[role] += 1
        declarations.append(
            RootDeclaration(
                alias=f"{role.value}-{counters[role]:02d}",
                repository_relative_path=relative_path,
                role=role,
                required=not required_roles or role in required_roles,
            )
        )
    return tuple(declarations)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _write_new_pair(
    private_path: Path,
    private_payload: bytes,
    public_path: Path,
    public_payload: bytes,
) -> None:
    """Exclusively claim both paths, then durably write both artifacts."""
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_stream: BinaryIO | None = None
    public_stream: BinaryIO | None = None
    created: list[Path] = []
    try:
        private_stream = _open_exclusive(private_path, 0o600)
        created.append(private_path)
        public_stream = _open_exclusive(public_path, 0o644)
        created.append(public_path)
        _write_durable(private_stream, private_payload)
        _write_durable(public_stream, public_payload)
    except Exception:
        if private_stream is not None:
            private_stream.close()
        if public_stream is not None:
            public_stream.close()
        for path in created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    else:
        private_stream.close()
        public_stream.close()


def _open_exclusive(path: Path, mode: int) -> BinaryIO:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    return os.fdopen(descriptor, "wb")


def _write_durable(stream: BinaryIO, payload: bytes) -> None:
    stream.write(payload)
    stream.flush()
    os.fsync(stream.fileno())


def _is_valid_public_summary(value: Any, required_roles: set[RootRole]) -> bool:
    if not isinstance(value, dict) or set(value) != _PUBLIC_TOP_LEVEL_FIELDS:
        return False
    if value.get("schema_version") != 1 or value.get("command") != "inventory":
        return False
    if value.get("status") != CheckStatus.PASS.value:
        return False
    if not _is_digest(value.get("source_set_sha256")) or not _is_digest(
        value.get("private_artifact_sha256")
    ):
        return False
    roles = value.get("root_roles")
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        return False
    if {role.value for role in required_roles} - set(roles):
        return False
    checks = value.get("checks")
    if not isinstance(checks, list) or not all(_valid_check(item) for item in checks):
        return False
    roots = value.get("roots")
    if not isinstance(roots, list) or not all(_valid_root(item) for item in roots):
        return False
    actual_roles = {item["role"] for item in roots}
    if set(roles) != actual_roles:
        return False
    if any(
        item["status"] != CheckStatus.PASS.value
        and not (not item["required"] and item["status"] == CheckStatus.NOT_RUN.value)
        for item in roots
    ):
        return False
    checks_by_name = {item["name"]: item for item in checks}
    if len(checks_by_name) != len(checks):
        return False
    if any(
        checks_by_name.get(f"root:{item['alias']}")
        != {
            "name": f"root:{item['alias']}",
            "status": item["status"],
            "evidence_sha256": item["aggregate_sha256"],
        }
        for item in roots
    ):
        return False
    totals = value.get("totals")
    if not isinstance(totals, dict) or set(totals) != _TOTAL_FIELDS:
        return False
    if not _valid_status_counts(totals.get("root_status_counts")):
        return False
    private_relpath = value.get("private_artifact_relpath")
    if not isinstance(private_relpath, str):
        return False
    private_path = PurePosixPath(private_relpath)
    if private_path.is_absolute() or ".." in private_path.parts:
        return False
    return all(
        isinstance(totals.get(field), int) and totals[field] >= 0
        for field in _TOTAL_FIELDS - {"root_status_counts"}
    )


def _valid_check(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == _CHECK_FIELDS
        and value.get("status") in _STATUS_FIELDS
        and _is_digest(value.get("evidence_sha256"))
        and isinstance(value.get("name"), str)
    )


def _valid_root(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != _PUBLIC_ROOT_FIELDS:
        return False
    if value.get("status") not in _STATUS_FIELDS:
        return False
    if value.get("role") not in {role.value for role in RootRole}:
        return False
    if not isinstance(value.get("alias"), str) or not isinstance(
        value.get("repository_relative_path"), str
    ):
        return False
    if not isinstance(value.get("required"), bool):
        return False
    if not all(
        isinstance(value.get(field), int) and value[field] >= 0
        for field in ("file_count", "byte_total")
    ):
        return False
    if not _is_digest(value.get("aggregate_sha256")):
        return False
    database_checks = value.get("database_checks")
    if not isinstance(database_checks, dict) or set(database_checks) != _DATABASE_CHECK_FIELDS:
        return False
    if not _valid_status_counts(database_checks.get("integrity_status_counts")):
        return False
    if not _valid_status_counts(database_checks.get("foreign_key_status_counts")):
        return False
    if not all(
        isinstance(database_checks.get(field), int) and database_checks[field] >= 0
        for field in (
            "database_count",
            "foreign_key_violation_count",
        )
    ):
        return False
    return _is_digest(database_checks.get("foreign_key_fingerprint"))


def _valid_status_counts(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == _STATUS_FIELDS
        and all(isinstance(count, int) and count >= 0 for count in value.values())
    )


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and _HEX_DIGEST.fullmatch(value) is not None


if __name__ == "__main__":
    raise SystemExit(main())
