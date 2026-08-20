"""Fail-closed contract for Aura's Node dependency authority.

The pre-change gate is deliberately opt-in because its manifest digests are
expected to stop matching after the two approved dependency edits.  The normal
tests describe the post-change authority consumed by CI.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import pytest


ROOT: Final = Path(__file__).resolve().parents[1]
EVIDENCE_PATH: Final = ROOT / ".planning/evidence/phase-02/package-legitimacy.json"
SUMMARY_PATH: Final = (
    ROOT / ".planning/phases/02-provider-and-runtime-core/02-15-SUMMARY.md"
)
PACKAGE_PATH: Final = ROOT / "package.json"
LOCK_PATH: Final = ROOT / "package-lock.json"

EVIDENCE_SHA256: Final = (
    "e3efba9197560d9559629448cfa088003e9239567c645c0204d4d9f994724bdb"
)
PRECHANGE_SHA256: Final = {
    "package.json": "305b5f54910fd39499493d5a06e2b5f756ad65cf18e02c8134e1037bd17160db",
    "package-lock.json": "e7dc3835f15dfcc00f5b4c19a73c0dee207a9dd915aa4551df8faab1190be302",
}
EXPECTED_DECISION_TEXT: Final = (
    "Approve only the 16 OK rows; reject the four SUS rows; revise Plans 02-16 "
    "and 02-17 before any manifest or lock changes."
)
APPROVED_CANDIDATES: Final = frozenset(
    {
        "pypi:ruff@0.12.7",
        "npm:pyright@1.1.413",
        "pypi:google-genai@1.75.0",
        "pypi:mcp@1.27.0",
        "pypi:fastmcp@3.2.4",
        "pypi:memvid-sdk@2.0.159",
        "pypi:beautifulsoup4@4.13.4",
        "pypi:ebooklib@0.19",
        "pypi:opencv-python@4.11.0.86",
        "pypi:pandas@2.2.3",
        "pypi:pillow@12.2.0",
        "pypi:pypdf@6.10.2",
        "pypi:qrcode@8.2",
        "pypi:anthropic@0.54.0",
        "pypi:websockets@15.0.1",
        "npm:@google/genai@1.51.0",
    }
)
REJECTED_CANDIDATES: Final = frozenset(
    {
        "pypi:pyzbar@0.1.9",
        "pypi:faiss-cpu@1.11.0",
        "pypi:faiss-gpu-cu12@1.14.1.post1",
        "pypi:asyncio-mqtt@0.16.2",
    }
)
APPROVED_NODE_ACTIONS: Final = frozenset(
    {
        ("add-dev", "npm:pyright@1.1.413"),
        ("remove-direct", "npm:@google/genai@1.51.0"),
    }
)
EXPECTED_DEPENDENCIES: Final = {"marked": "^18.0.3"}
EXPECTED_DEV_DEPENDENCIES: Final = {
    "@types/node": "^22.14.0",
    "pyright": "1.1.413",
    "typescript": "~5.7.2",
    "vite": "^8.0.0",
}
EXPECTED_SCRIPTS: Final = {
    "dev": "vite",
    "typecheck:python": "pyright --project pyproject.toml",
    "typecheck:frontend": "tsc --noEmit",
    "build": "vite build",
    "preview": "vite preview",
}
MAX_EVIDENCE_AGE: Final = timedelta(days=7)


class NodeAuthorityError(ValueError):
    """Raised when dependency authority is stale, changed, or widened."""


def _sha256(content: bytes) -> str:
    """Return a stable lowercase SHA-256 digest."""

    return hashlib.sha256(content).hexdigest()


def _utc_timestamp(value: object, field: str) -> datetime:
    """Parse a required RFC 3339 UTC timestamp."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise NodeAuthorityError(f"{field} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise NodeAuthorityError(f"{field} is malformed") from error
    return parsed.astimezone(UTC)


def validate_prechange_authority(
    document: dict[str, Any],
    *,
    evidence_bytes: bytes,
    summary_text: str,
    live_digests: dict[str, str],
    actions: frozenset[tuple[str, str]],
    now: datetime | None = None,
) -> None:
    """Independently authorize only the exact reviewed Node action subset."""

    if _sha256(evidence_bytes) != EVIDENCE_SHA256:
        raise NodeAuthorityError("evidence SHA-256 mismatch")
    if live_digests != PRECHANGE_SHA256:
        raise NodeAuthorityError("pre-change manifest digest mismatch")
    if actions != APPROVED_NODE_ACTIONS:
        raise NodeAuthorityError("Node action set is wider or different than approved")

    observed_now = now or datetime.now(UTC)
    retrieved_at = _utc_timestamp(document.get("retrieved_at"), "retrieved_at")
    if retrieved_at > observed_now + timedelta(minutes=5):
        raise NodeAuthorityError("evidence timestamp is in the future")
    if observed_now - retrieved_at > MAX_EVIDENCE_AGE:
        raise NodeAuthorityError("package evidence is stale")

    packages = document.get("packages")
    if not isinstance(packages, list) or any(
        not isinstance(package, dict) for package in packages
    ):
        raise NodeAuthorityError("package evidence is malformed")
    verdicts = {
        package.get("candidate_id"): package.get("verdict") for package in packages
    }
    ok_rows = {
        candidate_id for candidate_id, verdict in verdicts.items() if verdict == "OK"
    }
    sus_rows = {
        candidate_id for candidate_id, verdict in verdicts.items() if verdict == "SUS"
    }
    if (
        len(verdicts) != 20
        or ok_rows != APPROVED_CANDIDATES
        or sus_rows != REJECTED_CANDIDATES
    ):
        raise NodeAuthorityError("evidence must retain the exact 16 OK / 4 SUS partition")
    if any(package.get("manifest_change_authorized") is not False for package in packages):
        raise NodeAuthorityError("row-level evidence may not authorize a manifest change")

    approval = document.get("approval")
    if not isinstance(approval, dict):
        raise NodeAuthorityError("approval record is missing")
    if approval.get("decision_text") != EXPECTED_DECISION_TEXT:
        raise NodeAuthorityError("human decision text mismatch")
    if approval.get("reviewer") != "Ty":
        raise NodeAuthorityError("human reviewer mismatch")
    if (
        set(approval.get("conditionally_approved_candidate_ids", []))
        != APPROVED_CANDIDATES
    ):
        raise NodeAuthorityError("conditional approval set mismatch")
    if set(approval.get("rejected_candidate_ids", [])) != REJECTED_CANDIDATES:
        raise NodeAuthorityError("rejected set mismatch")
    if approval.get("manifest_changes_authorized") is not False:
        raise NodeAuthorityError("evidence document cannot directly authorize edits")
    if approval.get("authorized_candidate_ids") != []:
        raise NodeAuthorityError("evidence authorization list must remain empty")
    if set(approval.get("blocked_downstream_plans", [])) != {"02-16", "02-17"}:
        raise NodeAuthorityError("downstream revision gate mismatch")

    action_candidates = {candidate_id for _, candidate_id in actions}
    if not action_candidates <= APPROVED_CANDIDATES:
        raise NodeAuthorityError("an action targets a non-approved candidate")
    if action_candidates & REJECTED_CANDIDATES:
        raise NodeAuthorityError("an action targets a rejected candidate")
    if EXPECTED_DECISION_TEXT not in summary_text:
        raise NodeAuthorityError("Plan 02-15 summary decision mismatch")


def _load_json(path: Path) -> dict[str, Any]:
    """Load one JSON authority as an object."""

    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise AssertionError(f"{path.name} must contain a JSON object")
    return result


def _live_prechange_digests() -> dict[str, str]:
    """Hash only the two Node authorities covered by the pre-edit gate."""

    return {
        path.name: _sha256(path.read_bytes()) for path in (PACKAGE_PATH, LOCK_PATH)
    }


@pytest.mark.skipif(
    os.environ.get("AURA_DEPENDENCY_PRECHANGE_GATE") != "1",
    reason="opt-in gate is valid only before the approved manifest edit",
)
def test_prechange_node_authority_gate() -> None:
    """Block all edits unless evidence, decision, scope, and live digests match."""

    evidence_bytes = EVIDENCE_PATH.read_bytes()
    validate_prechange_authority(
        json.loads(evidence_bytes),
        evidence_bytes=evidence_bytes,
        summary_text=SUMMARY_PATH.read_text(encoding="utf-8"),
        live_digests=_live_prechange_digests(),
        actions=APPROVED_NODE_ACTIONS,
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "stale",
        "evidence-content",
        "digest",
        "widen-action",
        "rejected-action",
    ],
)
def test_prechange_gate_fails_closed_on_authority_drift(mutation: str) -> None:
    """Exercise the independent gate against each prohibited widening class."""

    evidence_bytes = EVIDENCE_PATH.read_bytes()
    document = json.loads(evidence_bytes)
    digests = dict(PRECHANGE_SHA256)
    actions = APPROVED_NODE_ACTIONS
    now = datetime.now(UTC)
    if mutation == "stale":
        document["retrieved_at"] = "2020-01-01T00:00:00Z"
        evidence_bytes = json.dumps(document, sort_keys=True).encode()
    elif mutation == "evidence-content":
        evidence_bytes += b"\n"
    elif mutation == "digest":
        digests["package.json"] = "0" * 64
    elif mutation == "widen-action":
        actions = actions | {("upgrade", "npm:marked@19.0.0")}
    else:
        actions = actions | {("remove-direct", "pypi:pyzbar@0.1.9")}

    with pytest.raises(NodeAuthorityError):
        validate_prechange_authority(
            document,
            evidence_bytes=evidence_bytes,
            summary_text=SUMMARY_PATH.read_text(encoding="utf-8"),
            live_digests=digests,
            actions=actions,
            now=now,
        )


def test_manifest_has_only_the_approved_direct_dependency_changes() -> None:
    """Reject floated Pyright or any unreviewed direct dependency churn."""

    package = _load_json(PACKAGE_PATH)
    assert package.get("dependencies") == EXPECTED_DEPENDENCIES
    assert package.get("devDependencies") == EXPECTED_DEV_DEPENDENCIES
    assert package.get("scripts") == EXPECTED_SCRIPTS


def test_lock_agrees_with_manifest_and_exact_pyright() -> None:
    """Require exact direct agreement and the official locked Pyright package."""

    package = _load_json(PACKAGE_PATH)
    lock = _load_json(LOCK_PATH)
    assert lock.get("lockfileVersion") == 3
    lock_root = lock["packages"][""]
    assert lock_root.get("dependencies") == package["dependencies"]
    assert lock_root.get("devDependencies") == package["devDependencies"]

    pyright = lock["packages"]["node_modules/pyright"]
    assert pyright["version"] == "1.1.413"
    assert pyright["dev"] is True
    assert pyright["bin"]["pyright"]
    assert "node_modules/@google/genai" not in lock["packages"]


def test_named_scripts_resolve_only_project_local_locked_tools() -> None:
    """npm scripts use its local bin PATH and never download or call globals."""

    scripts = _load_json(PACKAGE_PATH)["scripts"]
    assert scripts["typecheck:python"] == "pyright --project pyproject.toml"
    assert scripts["typecheck:frontend"] == "tsc --noEmit"
    assert scripts["build"] == "vite build"
    for command in scripts.values():
        assert "npx" not in command
        assert "npm install" not in command
        assert " -g " not in f" {command} "


def test_active_typescript_imports_keep_marked_and_exclude_google_sdk() -> None:
    """Scan supported source while excluding archived, generated, and vendor trees."""

    excluded_parts = {
        ".git",
        ".trunk",
        "node_modules",
        "dist",
        "archive",
        "archive_unused",
    }
    sources = [
        path
        for path in ROOT.rglob("*")
        if path.suffix in {".ts", ".tsx"}
        and not any(
            part in excluded_parts or part.startswith("archive") for part in path.parts
        )
    ]
    imports: dict[Path, set[str]] = {}
    pattern = re.compile(
        r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]"
    )
    for path in sources:
        imports[path.relative_to(ROOT)] = set(pattern.findall(path.read_text(encoding="utf-8")))

    assert "marked" in imports[Path("index.tsx")]
    assert all("@google/genai" not in modules for modules in imports.values())


def test_root_package_lock_is_the_only_active_node_lock() -> None:
    """Reject a second active Node authority."""

    active_locks = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("package-lock.json")
        if not any(
            part in {".git", ".trunk", "node_modules", "archive", "archive_unused"}
            or part.startswith("archive")
            for part in path.parts
        )
    ]
    assert active_locks == [Path("package-lock.json")]
