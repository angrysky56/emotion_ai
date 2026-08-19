"""Command-line interface for private and committable inventory evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from aura_backend.preservation.backup import (
    BackupBlocked,
    BackupResult,
    FileSnapshot,
    QuiescenceTicket,
    TreeManifest,
    copy_from_ticket,
    issue_quiescence_ticket,
)
from aura_backend.preservation.inventory import inventory_roots
from aura_backend.preservation.manifest import (
    CheckStatus,
    DatabaseEvidence,
    EvidenceCheck,
    FileEvidence,
    InventoryManifest,
    RootDeclaration,
    RootEvidence,
    RootRole,
)
from aura_backend.preservation.restore import verify_disposable_restore

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

    preflight = subcommands.add_parser(
        "preflight", description="Create a short-lived quiescence ticket"
    )
    preflight.add_argument("--inventory-summary", type=Path, required=True)
    preflight.add_argument("--backup-root", type=Path, required=True)
    preflight.add_argument("--public-summary", type=Path, required=True)
    preflight.add_argument("--ticket-ttl-seconds", type=int, required=True)

    validate_quiescence = subcommands.add_parser(
        "validate-quiescence", description="Validate inventory-bound ticket evidence"
    )
    validate_quiescence.add_argument("--summary", type=Path, required=True)
    validate_quiescence.add_argument("--inventory", type=Path, required=True)
    validate_quiescence.add_argument("--require-pass", action="store_true")

    backup = subcommands.add_parser(
        "backup-from-ticket", description="Copy all roots under a passing ticket"
    )
    backup.add_argument("--inventory-summary", type=Path, required=True)
    backup.add_argument("--quiescence-summary", type=Path, required=True)
    backup.add_argument("--backup-root", type=Path, required=True)
    backup.add_argument("--destination-name", required=True)

    verify = subcommands.add_parser(
        "verify", description="Verify a durable backup through a disposable restore"
    )
    verify.add_argument("--inventory-summary", type=Path, required=True)
    verify.add_argument("--quiescence-summary", type=Path, required=True)
    verify.add_argument("--backup-root", type=Path, required=True)
    verify.add_argument("--restore-parent", type=Path, required=True)
    verify.add_argument("--public-summary", type=Path, required=True)

    validate_restore = subcommands.add_parser(
        "validate-restore-summary", description="Validate the complete evidence chain"
    )
    validate_restore.add_argument("--summary", type=Path, required=True)
    validate_restore.add_argument("--inventory", type=Path, required=True)
    validate_restore.add_argument("--quiescence", type=Path, required=True)
    validate_restore.add_argument("--require-pass", action="store_true")
    validate_restore.add_argument("--require-source-unchanged", action="store_true")
    validate_restore.add_argument("--require-fk-parity", action="store_true")
    validate_restore.add_argument("--require-retrieval-parity", action="store_true")
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
        if arguments.command == "preflight":
            return _run_preflight(arguments)
        if arguments.command == "validate-quiescence":
            return _run_validate_quiescence(arguments)
        if arguments.command == "backup-from-ticket":
            return _run_backup(arguments)
        if arguments.command == "verify":
            return _run_verify(arguments)
        if arguments.command == "validate-restore-summary":
            return _run_validate_restore(arguments)
    except BackupBlocked:
        print("preservation command blocked by a safety precondition", file=sys.stderr)
        return 3
    except VerificationMismatch:
        print("preservation verification mismatch", file=sys.stderr)
        return 4
    except (ValueError, json.JSONDecodeError, TypeError) as error:
        print(
            f"preservation command failed ({type(error).__name__})",
            file=sys.stderr,
        )
        return 2
    except OSError as error:
        print(
            f"preservation command failed ({type(error).__name__})",
            file=sys.stderr,
        )
        return 5
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
    private_dict = manifest.to_private_dict()
    private_dict["repository_root"] = repository_root.as_posix()
    private_payload = _json_bytes(private_dict)
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


class VerificationMismatch(RuntimeError):
    """A cryptographic, integrity, count, or retrieval comparison failed."""


def _run_preflight(arguments: argparse.Namespace) -> int:
    backup_root = arguments.backup_root.resolve(strict=True)
    manifest, sources, inventory_public, inventory_bytes = _load_inventory_bundle(
        arguments.inventory_summary, backup_root
    )
    run_directory = backup_root / manifest.run_id
    run_directory.mkdir(mode=0o700, exist_ok=True)
    open_handles = _find_open_handles(sources)
    writer_processes = _find_writer_processes()
    ticket = issue_quiescence_ticket(
        sources,
        run_directory,
        ttl_seconds=arguments.ticket_ttl_seconds,
        inventory_manifest=manifest,
        open_handles=open_handles,
    )
    required_bytes = int(inventory_public["totals"]["byte_total"])
    free_bytes = __import__("shutil").disk_usage(run_directory).free
    free_status = CheckStatus.PASS if free_bytes >= required_bytes * 2 else CheckStatus.BLOCKED
    free_check = EvidenceCheck(
        name="mount_free_space",
        status=free_status,
        evidence_sha256=hashlib.sha256(
            json.dumps((required_bytes, free_bytes), separators=(",", ":")).encode()
        ).hexdigest(),
    )
    process_check = EvidenceCheck(
        name="process_scan",
        status=CheckStatus.BLOCKED if writer_processes else CheckStatus.PASS,
        evidence_sha256=hashlib.sha256("\n".join(writer_processes).encode()).hexdigest(),
    )
    checks = (*ticket.checks, process_check, free_check)
    ticket = replace(
        ticket,
        checks=checks,
        status=(
            CheckStatus.PASS
            if all(item.status is CheckStatus.PASS for item in checks)
            else CheckStatus.BLOCKED
        ),
    )
    inventory_digest = hashlib.sha256(inventory_bytes).hexdigest()
    private_path = run_directory / f"quiescence.{ticket.ticket_id}.private.json"
    private_dict = {
        **_ticket_common(ticket, manifest),
        "inventory_summary_sha256": inventory_digest,
        "inventory_private_sha256": inventory_public["private_artifact_sha256"],
        "destination_parent": ticket.destination_parent.as_posix(),
        "source_snapshot_sha256": ticket.source_set_sha256,
    }
    private_payload = _json_bytes(private_dict)
    private_digest = hashlib.sha256(private_payload).hexdigest()
    public_dict = {
        **_ticket_common(ticket, manifest),
        "inventory_summary_sha256": inventory_digest,
        "private_ticket_relpath": private_path.relative_to(backup_root).as_posix(),
        "private_ticket_sha256": private_digest,
        "ticket_id": ticket.ticket_id,
        "issued_at_utc": _format_time(ticket.issued_at_utc),
        "expires_at_utc": _format_time(ticket.expires_at_utc),
        "proposed_destination": run_directory.as_posix(),
    }
    _write_private_replace_public(
        private_path,
        private_payload,
        arguments.public_summary.resolve(strict=False),
        _json_bytes(public_dict),
    )
    return 0 if ticket.status is CheckStatus.PASS else 3


def _run_validate_quiescence(arguments: argparse.Namespace) -> int:
    ticket, _, _, _ = _load_quiescence_bundle(
        arguments.summary, arguments.inventory
    )
    if arguments.require_pass:
        if ticket.status is not CheckStatus.PASS:
            return 3
        if datetime.now(UTC) >= ticket.expires_at_utc:
            return 3
        if any(item.status is not CheckStatus.PASS for item in ticket.checks):
            return 3
    return 0


def _run_backup(arguments: argparse.Namespace) -> int:
    backup_root = arguments.backup_root.resolve(strict=True)
    manifest, sources, inventory_public, inventory_bytes = _load_inventory_bundle(
        arguments.inventory_summary, backup_root
    )
    ticket, quiescence_public, _, quiescence_bytes = _load_quiescence_bundle(
        arguments.quiescence_summary,
        arguments.inventory_summary,
        expected_backup_root=backup_root,
    )
    if ticket.inventory_source_set_sha256 != manifest.source_set_sha256:
        raise BackupBlocked("ticket source set does not match inventory")
    if _find_open_handles(sources):
        raise BackupBlocked("source roots gained open handles after preflight")
    if _find_writer_processes():
        raise BackupBlocked("an Aura writer process appeared after preflight")
    required_bytes = int(inventory_public["totals"]["byte_total"])
    if __import__("shutil").disk_usage(ticket.destination_parent).free < required_bytes * 2:
        raise BackupBlocked("backup destination no longer has sufficient free space")
    result = copy_from_ticket(
        sources,
        ticket.destination_parent,
        arguments.destination_name,
        ticket,
    )
    private_path = ticket.destination_parent / "backup.private.json"
    payload = _json_bytes(
        {
            "schema_version": 1,
            "command": "backup-from-ticket",
            "run_id": manifest.run_id,
            "status": result.status.value,
            "source_set_sha256": manifest.source_set_sha256,
            "checks": [
                _check_dict("source_unchanged", CheckStatus.PASS, result.source_after.sha256),
                _check_dict("destination_parity", CheckStatus.PASS, result.destination_manifest.sha256),
            ],
            "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "tool_commit": manifest.tool_commit,
            "inventory_summary_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
            "inventory_private_sha256": inventory_public["private_artifact_sha256"],
            "quiescence_summary_sha256": hashlib.sha256(quiescence_bytes).hexdigest(),
            "quiescence_ticket_sha256": quiescence_public["private_ticket_sha256"],
            "destination": result.destination.as_posix(),
            "source_before": _tree_dict(result.source_before),
            "source_after": _tree_dict(result.source_after),
            "destination_manifest": _tree_dict(result.destination_manifest),
        }
    )
    _write_new_private(private_path, payload)
    return 0


def _run_verify(arguments: argparse.Namespace) -> int:
    backup_root = arguments.backup_root.resolve(strict=True)
    manifest, _, inventory_public, inventory_bytes = _load_inventory_bundle(
        arguments.inventory_summary, backup_root
    )
    ticket, quiescence_public, _, quiescence_bytes = _load_quiescence_bundle(
        arguments.quiescence_summary,
        arguments.inventory_summary,
        expected_backup_root=backup_root,
    )
    backup_path = ticket.destination_parent / "backup.private.json"
    backup_bytes = backup_path.read_bytes()
    backup_private = json.loads(backup_bytes)
    if backup_private.get("inventory_summary_sha256") != hashlib.sha256(
        inventory_bytes
    ).hexdigest():
        raise VerificationMismatch("backup inventory binding mismatch")
    if backup_private.get("quiescence_summary_sha256") != hashlib.sha256(
        quiescence_bytes
    ).hexdigest():
        raise VerificationMismatch("backup ticket binding mismatch")
    result = BackupResult(
        status=CheckStatus(backup_private["status"]),
        destination=Path(backup_private["destination"]).resolve(strict=True),
        partial_destination=Path(f"{backup_private['destination']}.partial"),
        source_before=_tree_from_dict(backup_private["source_before"]),
        source_after=_tree_from_dict(backup_private["source_after"]),
        destination_manifest=_tree_from_dict(backup_private["destination_manifest"]),
    )
    private_manifest_path = backup_root / inventory_public["private_artifact_relpath"]
    inventory_private = json.loads(private_manifest_path.read_bytes())
    hmac_key = bytes.fromhex(inventory_private["hmac_key_hex"])
    restore = verify_disposable_restore(
        result,
        arguments.restore_parent,
        manifest,
        hmac_key=hmac_key,
    )
    private_path = ticket.destination_parent / "restore.private.json"
    private_dict = {
        **restore.to_private_dict(),
        "inventory_summary_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "quiescence_summary_sha256": hashlib.sha256(quiescence_bytes).hexdigest(),
        "backup_result_sha256": hashlib.sha256(backup_bytes).hexdigest(),
        "finalized_backup_path": result.destination.as_posix(),
    }
    private_payload = _json_bytes(private_dict)
    public_dict = {
        **restore.to_public_dict(),
        "inventory_summary_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "quiescence_summary_sha256": hashlib.sha256(quiescence_bytes).hexdigest(),
        "backup_result_sha256": hashlib.sha256(backup_bytes).hexdigest(),
        "private_artifact_relpath": private_path.relative_to(backup_root).as_posix(),
        "private_artifact_sha256": hashlib.sha256(private_payload).hexdigest(),
    }
    _write_private_replace_public(
        private_path,
        private_payload,
        arguments.public_summary.resolve(strict=False),
        _json_bytes(public_dict),
    )
    return 0 if restore.status is CheckStatus.PASS else 4


def _run_validate_restore(arguments: argparse.Namespace) -> int:
    summary_bytes = arguments.summary.read_bytes()
    summary = json.loads(summary_bytes)
    inventory_bytes = arguments.inventory.read_bytes()
    quiescence_bytes = arguments.quiescence.read_bytes()
    if summary.get("schema_version") != 1 or summary.get("command") != "verify":
        raise VerificationMismatch("restore schema mismatch")
    if summary.get("inventory_summary_sha256") != hashlib.sha256(
        inventory_bytes
    ).hexdigest():
        raise VerificationMismatch("inventory digest mismatch")
    if summary.get("quiescence_summary_sha256") != hashlib.sha256(
        quiescence_bytes
    ).hexdigest():
        raise VerificationMismatch("quiescence digest mismatch")
    checks = summary.get("checks")
    if not isinstance(checks, list) or not all(_valid_check(item) for item in checks):
        raise VerificationMismatch("restore checks invalid")
    if arguments.require_pass and (
        summary.get("status") != CheckStatus.PASS.value
        or any(item["status"] != CheckStatus.PASS.value for item in checks)
    ):
        raise VerificationMismatch("restore did not pass every required check")
    gates = summary.get("gates")
    if not isinstance(gates, dict):
        raise VerificationMismatch("restore gates missing")
    gate_requirements = (
        (arguments.require_source_unchanged, "source_unchanged"),
        (arguments.require_fk_parity, "foreign_key_parity"),
        (arguments.require_retrieval_parity, "retrieval_parity"),
    )
    if any(required and gates.get(name) is not True for required, name in gate_requirements):
        raise VerificationMismatch("required restore parity gate failed")
    return 0


def _load_inventory_bundle(
    summary_path: Path, backup_root: Path
) -> tuple[InventoryManifest, dict[str, Path], dict[str, Any], bytes]:
    summary_bytes = summary_path.read_bytes()
    public = json.loads(summary_bytes)
    if not _is_valid_public_summary(public, set()):
        raise ValueError("inventory public summary is invalid")
    relative = PurePosixPath(public["private_artifact_relpath"])
    private_path = backup_root.joinpath(*relative.parts).resolve(strict=True)
    if not private_path.is_relative_to(backup_root):
        raise ValueError("inventory private artifact escapes backup root")
    private_bytes = private_path.read_bytes()
    if hashlib.sha256(private_bytes).hexdigest() != public["private_artifact_sha256"]:
        raise VerificationMismatch("inventory private artifact digest mismatch")
    private = json.loads(private_bytes)
    manifest = _manifest_from_private(private)
    if manifest.source_set_sha256 != public["source_set_sha256"]:
        raise VerificationMismatch("inventory source-set binding mismatch")
    repository_root = Path(private["repository_root"]).resolve(strict=True)
    sources = {
        root.alias: repository_root.joinpath(
            *Path(root.repository_relative_path).parts
        ).resolve(strict=True)
        for root in manifest.roots
    }
    return manifest, sources, public, summary_bytes


def _load_quiescence_bundle(
    summary_path: Path,
    inventory_path: Path,
    *,
    expected_backup_root: Path | None = None,
) -> tuple[QuiescenceTicket, dict[str, Any], dict[str, Any], bytes]:
    summary_bytes = summary_path.read_bytes()
    public = json.loads(summary_bytes)
    inventory_bytes = inventory_path.read_bytes()
    inventory_public = json.loads(inventory_bytes)
    required = {
        "schema_version",
        "command",
        "run_id",
        "status",
        "source_set_sha256",
        "checks",
        "created_at_utc",
        "tool_commit",
        "inventory_summary_sha256",
        "private_ticket_relpath",
        "private_ticket_sha256",
        "ticket_id",
        "issued_at_utc",
        "expires_at_utc",
        "proposed_destination",
    }
    if not isinstance(public, dict) or set(public) != required:
        raise ValueError("quiescence public summary is invalid")
    if public.get("schema_version") != 1 or public.get("command") != "preflight":
        raise ValueError("quiescence schema is invalid")
    if public.get("inventory_summary_sha256") != hashlib.sha256(
        inventory_bytes
    ).hexdigest():
        raise VerificationMismatch("quiescence inventory binding mismatch")
    if public.get("source_set_sha256") != inventory_public.get("source_set_sha256"):
        raise VerificationMismatch("quiescence source-set binding mismatch")
    destination_parent = Path(public["proposed_destination"]).resolve(strict=True)
    backup_root = destination_parent.parent
    if expected_backup_root is not None and backup_root != expected_backup_root:
        raise BackupBlocked("quiescence destination mismatches backup root")
    relative = PurePosixPath(public["private_ticket_relpath"])
    private_path = backup_root.joinpath(*relative.parts).resolve(strict=True)
    if not private_path.is_relative_to(backup_root):
        raise ValueError("quiescence private artifact escapes backup root")
    private_bytes = private_path.read_bytes()
    if hashlib.sha256(private_bytes).hexdigest() != public["private_ticket_sha256"]:
        raise VerificationMismatch("quiescence private ticket digest mismatch")
    private = json.loads(private_bytes)
    if private.get("ticket_id") != public["ticket_id"]:
        raise VerificationMismatch("quiescence ticket pointer mismatch")
    bound_fields = (
        "status",
        "source_set_sha256",
        "checks",
        "issued_at_utc",
        "expires_at_utc",
    )
    if any(private.get(field) != public.get(field) for field in bound_fields):
        raise VerificationMismatch("quiescence public/private field mismatch")
    if private.get("inventory_summary_sha256") != public.get(
        "inventory_summary_sha256"
    ):
        raise VerificationMismatch("quiescence private inventory binding mismatch")
    ticket = QuiescenceTicket(
        ticket_id=private["ticket_id"],
        status=CheckStatus(private["status"]),
        issued_at_utc=_parse_time(private["issued_at_utc"]),
        expires_at_utc=_parse_time(private["expires_at_utc"]),
        destination_parent=Path(private["destination_parent"]).resolve(strict=True),
        source_set_sha256=private["source_snapshot_sha256"],
        inventory_source_set_sha256=private["source_set_sha256"],
        checks=tuple(
            EvidenceCheck(
                name=item["name"],
                status=CheckStatus(item["status"]),
                evidence_sha256=item["evidence_sha256"],
            )
            for item in private["checks"]
        ),
    )
    return ticket, public, private, summary_bytes


def _manifest_from_private(value: dict[str, Any]) -> InventoryManifest:
    roots = tuple(_root_from_private(item) for item in value["roots"])
    return InventoryManifest(
        roots=roots,
        status=CheckStatus(value["status"]),
        source_set_sha256=value["source_set_sha256"],
        hmac_key_hex=value["hmac_key_hex"],
        run_id=value["run_id"],
        created_at_utc=value["created_at_utc"],
        tool_commit=value["tool_commit"],
        schema_version=value["schema_version"],
        tool_version=value["tool_version"],
        command=value["command"],
    )


def _root_from_private(value: dict[str, Any]) -> RootEvidence:
    files = tuple(
        FileEvidence(
            relative_path=item["relative_path"],
            role=RootRole(item["role"]),
            byte_size=item["byte_size"],
            mtime_ns=item["mtime_ns"],
            file_type=item["file_type"],
            status=CheckStatus(item["status"]),
            sha256=item["sha256"],
            private_error_code=item["private_error_code"],
            private_error=item["private_error"],
        )
        for item in value["files"]
    )
    databases = tuple(
        DatabaseEvidence(
            relative_path=item["relative_path"],
            integrity_status=CheckStatus(item["integrity_status"]),
            integrity_result=item["integrity_result"],
            foreign_key_status=CheckStatus(item["foreign_key_status"]),
            foreign_key_violation_count=item["foreign_key_violation_count"],
            foreign_key_fingerprint=item["foreign_key_fingerprint"],
            private_integrity_results=tuple(item["private_integrity_results"]),
            private_error_code=item["private_error_code"],
            private_error=item["private_error"],
        )
        for item in value["databases"]
    )
    return RootEvidence(
        alias=value["alias"],
        repository_relative_path=value["repository_relative_path"],
        role=RootRole(value["role"]),
        required=value["required"],
        status=CheckStatus(value["status"]),
        files=files,
        databases=databases,
        file_count=value["file_count"],
        byte_total=value["byte_total"],
        aggregate_sha256=value["aggregate_sha256"],
        private_error_code=value["private_error_code"],
        private_error=value["private_error"],
    )


def _tree_dict(manifest: TreeManifest) -> dict[str, Any]:
    return {
        "sha256": manifest.sha256,
        "files": [
            {
                "root_alias": item.root_alias,
                "relative_path": item.relative_path,
                "byte_size": item.byte_size,
                "mtime_ns": item.mtime_ns,
                "sha256": item.sha256,
            }
            for item in manifest.files
        ],
    }


def _tree_from_dict(value: dict[str, Any]) -> TreeManifest:
    return TreeManifest(
        files=tuple(FileSnapshot(**item) for item in value["files"]),
        sha256=value["sha256"],
    )


def _ticket_common(
    ticket: QuiescenceTicket, manifest: InventoryManifest
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "preflight",
        "run_id": manifest.run_id,
        "status": ticket.status.value,
        "source_set_sha256": manifest.source_set_sha256,
        "checks": [
            {
                "name": item.name,
                "status": item.status.value,
                "evidence_sha256": item.evidence_sha256,
            }
            for item in ticket.checks
        ],
        "created_at_utc": _format_time(ticket.issued_at_utc),
        "tool_commit": manifest.tool_commit,
        "ticket_id": ticket.ticket_id,
        "issued_at_utc": _format_time(ticket.issued_at_utc),
        "expires_at_utc": _format_time(ticket.expires_at_utc),
    }


def _find_open_handles(source_roots: dict[str, Path]) -> tuple[str, ...]:
    import subprocess

    handles: list[str] = []
    for alias, source in sorted(source_roots.items()):
        try:
            result = subprocess.run(
                ["lsof", "+D", str(source)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            handles.append(f"{alias}:scan-unavailable")
            continue
        if result.returncode == 0 and result.stdout.strip():
            handles.append(f"{alias}:open")
        elif result.returncode not in {0, 1}:
            handles.append(f"{alias}:scan-failed")
    return tuple(handles)


def _find_writer_processes() -> tuple[str, ...]:
    """Return opaque process categories for likely Aura persistence writers."""
    import subprocess

    try:
        result = subprocess.run(
            ["ps", "-eo", "args="],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ("process-scan-unavailable",)
    signatures = (
        "uvicorn aura_backend.main",
        "aura_backend/aura_server.py",
        "aura_backend/database_protection.py",
    )
    return tuple(
        f"writer-category-{index}"
        for index, signature in enumerate(signatures, start=1)
        if any(signature in line for line in result.stdout.splitlines())
    )


def _write_private_replace_public(
    private_path: Path,
    private_payload: bytes,
    public_path: Path,
    public_payload: bytes,
) -> None:
    _write_new_private(private_path, private_payload)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = public_path.with_name(f".{public_path.name}.{os.getpid()}.tmp")
    try:
        with _open_exclusive(temporary, 0o644) as stream:
            _write_durable(stream, public_payload)
        os.replace(temporary, public_path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _write_new_private(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _open_exclusive(path, 0o600) as stream:
        _write_durable(stream, payload)


def _check_dict(name: str, status: CheckStatus, evidence: str) -> dict[str, str]:
    return {
        "name": name,
        "status": status.value,
        "evidence_sha256": hashlib.sha256(evidence.encode()).hexdigest(),
    }


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


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
