"""Fail-closed validation for Phase 2 dependency decision evidence.

This module deliberately validates a checked-in evidence document instead of
contacting registries. Network observations are review inputs; deterministic CI
must prove that the captured inputs are complete, fresh, and cannot authorize a
change while any legitimacy or entry-point signal remains unresolved.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / ".planning/evidence/phase-02/package-legitimacy.json"
MAX_EVIDENCE_AGE = timedelta(days=7)

EXPECTED_CANDIDATES = {
    "npm:@google/genai@1.51.0",
    "npm:pyright@1.1.413",
    "pypi:anthropic@0.54.0",
    "pypi:asyncio-mqtt@0.16.2",
    "pypi:beautifulsoup4@4.13.4",
    "pypi:ebooklib@0.19",
    "pypi:faiss-cpu@1.11.0",
    "pypi:faiss-gpu-cu12@1.14.1.post1",
    "pypi:fastmcp@3.2.4",
    "pypi:google-genai@1.75.0",
    "pypi:mcp@1.27.0",
    "pypi:memvid-sdk@2.0.159",
    "pypi:opencv-python@4.11.0.86",
    "pypi:pandas@2.2.3",
    "pypi:pillow@12.2.0",
    "pypi:pypdf@6.10.2",
    "pypi:pyzbar@0.1.9",
    "pypi:qrcode@8.2",
    "pypi:ruff@0.12.7",
    "pypi:websockets@15.0.1",
}

EXPECTED_ENTRYPOINTS = {
    "api-runtime",
    "aura-fastmcp-server",
    "companion-mcp-wrapper",
    "docker-backend",
    "frontend-build",
    "frontend-typecheck",
    "memvid-integration",
    "python-deterministic-tests",
}

ALLOWED_VERDICTS = {"OK", "SUS", "UNASSESSED"}
ALLOWED_DISPOSITIONS = {
    "keep-base",
    "move-to-named-extra/group",
    "remove-direct",
    "retain-pending",
}
ALLOWED_ENTRYPOINT_STATUS = {"supported", "conditional", "blocked"}
REQUIRED_PACKAGE_FIELDS = {
    "candidate_id",
    "ecosystem",
    "name",
    "version",
    "proposed_change",
    "registry",
    "source",
    "release",
    "maintainers",
    "license",
    "status",
    "install_scripts",
    "declared_cli_entrypoints",
    "verdict",
    "verdict_reasons",
    "manifest_change_authorized",
}


class EvidenceError(ValueError):
    """Raised when package or dependency evidence fails closed."""


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EvidenceError(f"{field} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EvidenceError(f"{field} is malformed") from error
    if parsed.tzinfo is None:
        raise EvidenceError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _require_https(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise EvidenceError(f"{field} must be an HTTPS URL")


def _require_string_list(value: object, field: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise EvidenceError(f"{field} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise EvidenceError(f"{field} may not be empty")


def load_evidence() -> dict[str, Any]:
    """Load the canonical audit without importing or executing package code."""

    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def validate_package_evidence(
    document: dict[str, Any], *, now: datetime | None = None
) -> None:
    """Validate exact candidates, current provenance, and authorization safety."""

    if document.get("schema_version") != 1:
        raise EvidenceError("schema_version must be 1")
    observed_now = now or datetime.now(UTC)
    retrieved_at = _parse_timestamp(document.get("retrieved_at"), "retrieved_at")
    if retrieved_at > observed_now + timedelta(minutes=5):
        raise EvidenceError("retrieved_at may not be in the future")
    if observed_now - retrieved_at > MAX_EVIDENCE_AGE:
        raise EvidenceError("package evidence is stale")

    packages = document.get("packages")
    if not isinstance(packages, list):
        raise EvidenceError("packages must be a list")
    candidate_ids = [item.get("candidate_id") for item in packages if isinstance(item, dict)]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise EvidenceError("duplicate package candidate")
    if set(candidate_ids) != EXPECTED_CANDIDATES:
        missing = sorted(EXPECTED_CANDIDATES - set(candidate_ids))
        unexpected = sorted(set(candidate_ids) - EXPECTED_CANDIDATES)
        raise EvidenceError(f"candidate set mismatch; missing={missing}, unexpected={unexpected}")

    for package in packages:
        if not isinstance(package, dict):
            raise EvidenceError("each package candidate must be an object")
        missing_fields = REQUIRED_PACKAGE_FIELDS - package.keys()
        if missing_fields:
            raise EvidenceError(f"{package.get('candidate_id')}: missing {sorted(missing_fields)}")

        candidate_id = package["candidate_id"]
        expected_id = (
            f"{package['ecosystem']}:{package['name']}@{package['version']}"
        )
        if candidate_id != expected_id:
            raise EvidenceError(f"{candidate_id}: identity fields do not match")
        if package["ecosystem"] not in {"pypi", "npm"}:
            raise EvidenceError(f"{candidate_id}: unsupported ecosystem")

        registry = package["registry"]
        source = package["source"]
        release = package["release"]
        status = package["status"]
        scripts = package["install_scripts"]
        if not all(isinstance(item, dict) for item in (registry, source, release, status, scripts)):
            raise EvidenceError(f"{candidate_id}: nested evidence must be objects")

        _require_https(registry.get("url"), f"{candidate_id}.registry.url")
        _require_https(registry.get("evidence_url"), f"{candidate_id}.registry.evidence_url")
        registry_time = _parse_timestamp(
            registry.get("retrieved_at"), f"{candidate_id}.registry.retrieved_at"
        )
        if observed_now - registry_time > MAX_EVIDENCE_AGE:
            raise EvidenceError(f"{candidate_id}: registry evidence is stale")
        _require_https(source.get("url"), f"{candidate_id}.source.url")
        _require_https(source.get("evidence_url"), f"{candidate_id}.source.evidence_url")
        if not isinstance(source.get("owner"), str) or not source["owner"]:
            raise EvidenceError(f"{candidate_id}: source owner is missing")
        if source.get("archived") not in {True, False}:
            raise EvidenceError(f"{candidate_id}: archived status must be explicit")

        _parse_timestamp(release.get("published_at"), f"{candidate_id}.release.published_at")
        if not isinstance(release.get("age_days_at_retrieval"), int) or release["age_days_at_retrieval"] < 0:
            raise EvidenceError(f"{candidate_id}: release age must be a non-negative integer")
        _require_string_list(package["maintainers"], f"{candidate_id}.maintainers")
        if not isinstance(package["license"], str) or not package["license"]:
            raise EvidenceError(f"{candidate_id}: license is missing")
        if status.get("yanked") not in {True, False, "not-applicable"}:
            raise EvidenceError(f"{candidate_id}: yanked status must be explicit")
        if status.get("deprecated") not in {True, False, "unknown"}:
            raise EvidenceError(f"{candidate_id}: deprecated status must be explicit")

        if set(scripts) != {"preinstall", "install", "postinstall", "evidence_url", "evidence_kind"}:
            raise EvidenceError(f"{candidate_id}: install-script evidence is malformed")
        _require_https(scripts["evidence_url"], f"{candidate_id}.install_scripts.evidence_url")
        for key in ("preinstall", "install", "postinstall"):
            if scripts[key] is not None and not isinstance(scripts[key], str):
                raise EvidenceError(f"{candidate_id}: {key} must be a string or null")
        _require_string_list(
            package["declared_cli_entrypoints"],
            f"{candidate_id}.declared_cli_entrypoints",
            allow_empty=True,
        )

        verdict = package["verdict"]
        if verdict not in ALLOWED_VERDICTS:
            raise EvidenceError(f"{candidate_id}: unknown verdict")
        _require_string_list(package["verdict_reasons"], f"{candidate_id}.verdict_reasons")
        if package["manifest_change_authorized"] is not False:
            raise EvidenceError(f"{candidate_id}: automated evidence cannot authorize a change")
        if verdict != "OK" and package["manifest_change_authorized"]:
            raise EvidenceError(f"{candidate_id}: unresolved evidence was approved")

    additions = {item["name"]: item for item in packages if item["proposed_change"] == "add"}
    if set(additions) != {"ruff", "pyright"}:
        raise EvidenceError("the exact proposed additions must be Ruff and Pyright")
    if "ruff" not in additions["ruff"]["declared_cli_entrypoints"]:
        raise EvidenceError("Ruff executable evidence is missing")
    if "pyright" not in additions["pyright"]["declared_cli_entrypoints"]:
        raise EvidenceError("Pyright executable evidence is missing")

    approval = document.get("approval")
    if not isinstance(approval, dict):
        raise EvidenceError("approval must be an object")
    if approval.get("status") != "PENDING_HUMAN_REVIEW":
        raise EvidenceError("Plan 02-14 evidence must remain pending human review")
    if approval.get("manifest_changes_authorized") is not False:
        raise EvidenceError("package audit may not self-authorize manifest changes")
    if approval.get("authorized_candidate_ids") != []:
        raise EvidenceError("pending evidence may not list authorized candidates")


def validate_dependency_inventory(document: dict[str, Any]) -> None:
    """Validate direct-dependency consumers and supported entry-point lanes."""

    inventory = document.get("dependency_inventory")
    entrypoints = document.get("supported_entrypoints")
    if not isinstance(inventory, list) or not isinstance(entrypoints, list):
        raise EvidenceError("dependency_inventory and supported_entrypoints must be lists")

    manifest_names = document.get("manifest_direct_dependencies")
    if not isinstance(manifest_names, list) or len(manifest_names) != len(set(manifest_names)):
        raise EvidenceError("manifest_direct_dependencies must be a unique list")
    inventory_names = [item.get("dependency_id") for item in inventory if isinstance(item, dict)]
    if len(inventory_names) != len(set(inventory_names)):
        raise EvidenceError("duplicate dependency inventory record")
    if set(inventory_names) != set(manifest_names):
        raise EvidenceError("every direct manifest dependency must have one inventory record")

    entrypoint_ids = [item.get("id") for item in entrypoints if isinstance(item, dict)]
    if len(entrypoint_ids) != len(set(entrypoint_ids)):
        raise EvidenceError("duplicate supported entry point")
    if set(entrypoint_ids) != EXPECTED_ENTRYPOINTS:
        raise EvidenceError("supported entry-point inventory is incomplete")

    lanes_by_entrypoint: dict[str, set[str]] = {}
    for entrypoint in entrypoints:
        if entrypoint.get("status") not in ALLOWED_ENTRYPOINT_STATUS:
            raise EvidenceError(f"{entrypoint.get('id')}: invalid entry-point status")
        if not isinstance(entrypoint.get("command"), str) or not entrypoint["command"]:
            raise EvidenceError(f"{entrypoint.get('id')}: command is missing")
        _require_string_list(entrypoint.get("source_paths"), f"{entrypoint.get('id')}.source_paths")
        _require_string_list(entrypoint.get("dependency_lanes"), f"{entrypoint.get('id')}.dependency_lanes")
        lanes_by_entrypoint[entrypoint["id"]] = set(entrypoint["dependency_lanes"])

    for dependency in inventory:
        dependency_id = dependency["dependency_id"]
        if dependency.get("disposition") not in ALLOWED_DISPOSITIONS:
            raise EvidenceError(f"{dependency_id}: invalid disposition")
        if not isinstance(dependency.get("lane"), str) or not dependency["lane"]:
            raise EvidenceError(f"{dependency_id}: dependency lane is missing")
        consumers = dependency.get("consumers")
        if not isinstance(consumers, list):
            raise EvidenceError(f"{dependency_id}: consumers must be a list")
        for consumer in consumers:
            if not isinstance(consumer, dict):
                raise EvidenceError(f"{dependency_id}: consumer must be an object")
            path = consumer.get("path")
            symbols = consumer.get("symbols")
            entrypoint_refs = consumer.get("entrypoints")
            if not isinstance(path, str) or not (ROOT / path).is_file():
                raise EvidenceError(f"{dependency_id}: consumer path is absent")
            _require_string_list(symbols, f"{dependency_id}.consumer.symbols")
            _require_string_list(entrypoint_refs, f"{dependency_id}.consumer.entrypoints")
            for entrypoint_id in entrypoint_refs:
                if entrypoint_id not in lanes_by_entrypoint:
                    raise EvidenceError(f"{dependency_id}: unknown entry point {entrypoint_id}")
                if dependency["lane"] not in lanes_by_entrypoint[entrypoint_id]:
                    raise EvidenceError(
                        f"{dependency_id}: active entry point {entrypoint_id} lacks lane {dependency['lane']}"
                    )

        if dependency["disposition"] in {"remove-direct", "move-to-named-extra/group"}:
            uncovered = dependency.get("uncovered_supported_consumers")
            if uncovered != []:
                raise EvidenceError(f"{dependency_id}: move/removal has uncovered consumers")
        if dependency.get("manifest_change_authorized") is not False:
            raise EvidenceError(f"{dependency_id}: inventory cannot authorize a manifest change")


def test_package_legitimacy_evidence_is_current_and_complete() -> None:
    validate_package_evidence(load_evidence())


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda doc: doc.update(retrieved_at="2020-01-01T00:00:00Z"), "stale"),
        (lambda doc: doc["packages"].pop(), "candidate set mismatch"),
        (lambda doc: doc["packages"].append(copy.deepcopy(doc["packages"][0])), "duplicate"),
        (
            lambda doc: doc["packages"].append(
                {**copy.deepcopy(doc["packages"][0]), "candidate_id": "pypi:surprise@1.0"}
            ),
            "candidate set mismatch",
        ),
        (lambda doc: doc["packages"][0].pop("source"), "missing"),
        (lambda doc: doc["packages"][0].update(version="wrong"), "do not match"),
        (
            lambda doc: doc["packages"][0].update(
                verdict="UNASSESSED", manifest_change_authorized=True
            ),
            "cannot authorize",
        ),
        (
            lambda doc: doc["packages"][0].update(
                verdict="SUS", manifest_change_authorized=True
            ),
            "cannot authorize",
        ),
    ],
)
def test_package_candidate_mutations_fail_closed(mutation: Any, match: str) -> None:
    document = load_evidence()
    mutation(document)
    with pytest.raises(EvidenceError, match=match):
        validate_package_evidence(document)


def test_package_addition_entrypoints_and_install_scripts_are_explicit() -> None:
    document = load_evidence()
    additions = {item["name"]: item for item in document["packages"] if item["proposed_change"] == "add"}
    assert additions["ruff"]["declared_cli_entrypoints"] == ["ruff"]
    assert additions["pyright"]["declared_cli_entrypoints"] == [
        "pyright",
        "pyright-langserver",
    ]
    for package in additions.values():
        assert set(package["install_scripts"]) == {
            "preinstall",
            "install",
            "postinstall",
            "evidence_url",
            "evidence_kind",
        }


def test_dependency_inventory_covers_every_manifest_and_entrypoint() -> None:
    document = load_evidence()
    validate_package_evidence(document)
    validate_dependency_inventory(document)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda doc: doc["dependency_inventory"].pop(),
        lambda doc: doc["supported_entrypoints"].pop(),
        lambda doc: doc["supported_entrypoints"].append(
            copy.deepcopy(doc["supported_entrypoints"][0])
        ),
        lambda doc: doc["dependency_inventory"][0].update(
            uncovered_supported_consumers=["api-runtime"]
        ),
        lambda doc: doc["dependency_inventory"][0].update(
            manifest_change_authorized=True
        ),
    ],
)
def test_dependency_move_or_removal_mutations_fail_closed(mutation: Any) -> None:
    document = load_evidence()
    mutation(document)
    with pytest.raises(EvidenceError):
        validate_dependency_inventory(document)
