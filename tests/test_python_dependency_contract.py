"""Fail-closed Python dependency authority contract for Phase 2.

The pre-change gate is intentionally separate from the desired-state tests.  It
licenses one narrow manifest edit only while Ty's exact decision, the audited
evidence, and both current authority files still match the reviewed state.
Normal test runs validate the resulting authority without expecting those old
pre-change digests to remain current.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / ".planning/evidence/phase-02/package-legitimacy.json"
DECISION_SUMMARY_PATH = (
    ROOT / ".planning/phases/02-provider-and-runtime-core/02-15-SUMMARY.md"
)
PYPROJECT_PATH = ROOT / "pyproject.toml"
LOCK_PATH = ROOT / "uv.lock"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
DOCKERFILE_PATH = ROOT / "aura_backend/Dockerfile"

EXPECTED_DECISION = (
    "Approve only the 16 OK rows; reject the four SUS rows; revise Plans 02-16 "
    "and 02-17 before any manifest or lock changes."
)
EXPECTED_EVIDENCE_SHA256 = (
    "18492972b43f0cdbc0c04526d3181fd9a09b61b3932be8e1f96abd828ff21fd3"
)
PRECHANGE_AUTHORITY_SHA256 = {
    "pyproject.toml": (
        "d9459bd69739ff4891e641bbcdd00f13abd4d41bf241e09141d6c7ebc2feef0c"
    ),
    "uv.lock": "4b7df8a21291f380a42f4b4a5d360d194b8228a0632ca84cae7dcffe35fca74e",
}
REQUIREMENTS_SHA256 = "90f40e456899c4f1b3088dd327afb42b2498ae76e28b5b135e3fdb39ac273db9"
MAX_EVIDENCE_AGE = timedelta(days=7)

APPROVED_PYTHON_ACTIONS = {
    "pypi:ruff@0.12.7": ("add", "dev", "ruff==0.12.7"),
    "pypi:google-genai@1.75.0": (
        "move",
        "provider-gemini",
        "google-genai==1.75.0",
    ),
    "pypi:mcp@1.27.0": ("move", "mcp", "mcp==1.27.0"),
    "pypi:fastmcp@3.2.4": ("move", "mcp", "fastmcp==3.2.4"),
    "pypi:memvid-sdk@2.0.160": ("move", "memvid", "memvid-sdk==2.0.160"),
    "pypi:beautifulsoup4@4.13.4": ("remove-direct", "base", None),
    "pypi:ebooklib@0.19": ("remove-direct", "base", None),
    "pypi:opencv-python@4.11.0.86": ("remove-direct", "base", None),
    "pypi:pandas@2.2.3": ("remove-direct", "base", None),
    "pypi:pillow@12.2.0": ("remove-direct", "base", None),
    "pypi:pypdf@6.10.2": ("remove-direct", "base", None),
    "pypi:qrcode@8.2": ("remove-direct", "base", None),
    "pypi:anthropic@0.54.0": ("remove-direct", "base", None),
    "pypi:websockets@15.0.1": ("remove-direct", "base", None),
}
REJECTED_CANDIDATES = {
    "pypi:pyzbar@0.1.9",
    "pypi:faiss-cpu@1.11.0",
    "pypi:faiss-gpu-cu12@1.14.1.post1",
    "pypi:asyncio-mqtt@0.16.2",
}
REJECTED_DIRECT_DECLARATIONS = {
    "asyncio-mqtt": "asyncio-mqtt>=0.16.2",
    "faiss-cpu": "faiss-cpu>=1.11.0",
    "faiss-gpu-cu12": "faiss-gpu-cu12>=1.11.0",
    "pyzbar": "pyzbar>=0.1.9",
}
REJECTED_LOCK_RECORD_SHA256 = {
    "asyncio-mqtt": (
        "151bad2f48d5e630f0aae7c548845bce59ef99329a8275e99924d02b575feb87"
    ),
    "faiss-cpu": ("f68e3568d34ef9fa5dccf5b45a02f53531fe641fe145677969ce8d34b9c0da29"),
    "faiss-gpu-cu12": (
        "254e90b6a88f3227c18d3afdf292ce621714f9ea1e6178d457d5fe40f884e93b"
    ),
    "pyzbar": "02f51addea044f8a9e931c6ee57932a461297f3460332b69beafd599cbd87ea2",
}

EXPECTED_BASE_DEPENDENCIES = {
    "aiofiles>=24.1.0",
    "asyncio-mqtt>=0.16.2",
    "chromadb>=1.5.8",
    "faiss-cpu>=1.11.0",
    "faiss-gpu-cu12>=1.11.0",
    "fastapi>=0.136.1",
    "httpx>=0.28.1",
    "numpy>=2.0.0",
    "openai>=1.86.0",
    "pydantic>=2.13.3",
    "pytest>=9.0.3",
    "pytest-asyncio>=0.24.0",
    "python-dateutil>=2.9.0",
    "python-dotenv>=1.2.2",
    "python-multipart>=0.0.26",
    "pyzbar>=0.1.9",
    "sentence-transformers>=3.3.1",
    "torch==2.11.0",
    "uvicorn>=0.34.0",
}
EXPECTED_OPTIONAL_LANES = {
    "provider-gemini": ["google-genai==1.75.0"],
    "mcp": ["mcp==1.27.0", "fastmcp==3.2.4"],
    "memvid": ["memvid-sdk==2.0.160"],
}
SUPPORTED_ENTRYPOINT_LANES = {
    "aura_backend.main": {"base"},
    "aura_backend.runtime": {"base"},
    "aura_backend.providers.gemini": {"base", "provider-gemini"},
    "aura_backend.aura_server": {"base", "mcp", "memvid"},
    "aura_backend.aura_as_mcp_server": {"base"},
    "aura_backend.aura_real_memvid": {"base", "memvid"},
}


class AuthorizationError(ValueError):
    """Raised when the narrow dependency authorization envelope does not match."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AuthorizationError(f"{field} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AuthorizationError(f"{field} is malformed") from error
    return parsed.astimezone(UTC)


def _canonical_record(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return _sha256(payload.encode("utf-8"))


def _dependency_name(declaration: str) -> str:
    match = re.match(r"^([A-Za-z0-9_.-]+)", declaration)
    if match is None:
        raise AssertionError(f"malformed dependency declaration: {declaration!r}")
    return match.group(1).lower().replace("_", "-")


def _direct_declarations(document: dict[str, Any]) -> dict[str, str]:
    declarations = document["project"]["dependencies"]
    return {_dependency_name(item): item for item in declarations}


def _package_records(lock_document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for package in lock_document["package"]:
        name = package["name"]
        if name in records:
            raise AssertionError(f"duplicate lock package name is unsupported: {name}")
        records[name] = package
    return records


def validate_prechange_authorization(
    *,
    evidence_bytes: bytes,
    summary_text: str,
    pyproject_bytes: bytes,
    lock_bytes: bytes,
    now: datetime,
    actions: dict[str, tuple[str, str, str | None]],
) -> None:
    """Validate evidence and authority digests before any manifest edit."""

    if _sha256(evidence_bytes) != EXPECTED_EVIDENCE_SHA256:
        raise AuthorizationError("evidence SHA-256 mismatch")
    if _sha256(pyproject_bytes) != PRECHANGE_AUTHORITY_SHA256["pyproject.toml"]:
        raise AuthorizationError("pyproject.toml pre-change SHA-256 mismatch")
    if _sha256(lock_bytes) != PRECHANGE_AUTHORITY_SHA256["uv.lock"]:
        raise AuthorizationError("uv.lock pre-change SHA-256 mismatch")
    if actions != APPROVED_PYTHON_ACTIONS:
        raise AuthorizationError("approved Python action set mismatch")
    if EXPECTED_DECISION not in summary_text:
        raise AuthorizationError("decision summary text mismatch")

    document = json.loads(evidence_bytes)
    validate_evidence_scope(document, now=now, actions=actions)


def validate_evidence_scope(
    document: dict[str, Any],
    *,
    now: datetime,
    actions: dict[str, tuple[str, str, str | None]],
) -> None:
    """Validate the exact human partition, lanes, and supported consumers."""

    retrieved_at = _parse_utc(document.get("retrieved_at"), "retrieved_at")
    if retrieved_at > now + timedelta(minutes=5):
        raise AuthorizationError("evidence timestamp is in the future")
    if now - retrieved_at > MAX_EVIDENCE_AGE:
        raise AuthorizationError("evidence is stale")

    packages = {package["candidate_id"]: package for package in document["packages"]}
    ok_candidates = {key for key, row in packages.items() if row["verdict"] == "OK"}
    sus_candidates = {key for key, row in packages.items() if row["verdict"] == "SUS"}
    approval = document["approval"]
    if approval.get("decision_text") != EXPECTED_DECISION:
        raise AuthorizationError("evidence decision text mismatch")
    if approval.get("reviewer") != "Ty":
        raise AuthorizationError("reviewer mismatch")
    if set(approval.get("conditionally_approved_candidate_ids", [])) != ok_candidates:
        raise AuthorizationError("conditionally approved rows are not the exact OK set")
    if len(ok_candidates) != 16:
        raise AuthorizationError("expected exactly 16 OK rows")
    if set(approval.get("rejected_candidate_ids", [])) != sus_candidates:
        raise AuthorizationError("rejected rows are not the exact SUS set")
    if sus_candidates != REJECTED_CANDIDATES:
        raise AuthorizationError("expected exactly the four named SUS rows")
    if approval.get("manifest_changes_authorized") is not False:
        raise AuthorizationError("evidence may not grant broad manifest authority")
    if approval.get("authorized_candidate_ids") != []:
        raise AuthorizationError("evidence may not directly authorize candidates")
    if set(approval.get("blocked_downstream_plans", [])) != {"02-16", "02-17"}:
        raise AuthorizationError("revised plans must independently clear their gates")
    if any(
        row.get("manifest_change_authorized") is not False for row in packages.values()
    ):
        raise AuthorizationError("row-level evidence may not grant manifest authority")

    approved_python = {
        candidate for candidate in ok_candidates if candidate.startswith("pypi:")
    }
    if set(actions) != approved_python:
        raise AuthorizationError("actions are not the exact approved Python subset")
    if set(actions) & REJECTED_CANDIDATES:
        raise AuthorizationError("a rejected row appeared in the action set")

    inventory = {row["dependency_id"]: row for row in document["dependency_inventory"]}
    expected_lanes = {
        "pypi:google-genai": ("move-to-named-extra/group", "provider-gemini"),
        "pypi:mcp": ("move-to-named-extra/group", "mcp"),
        "pypi:fastmcp": ("move-to-named-extra/group", "mcp"),
        "pypi:memvid-sdk": ("move-to-named-extra/group", "memvid"),
    }
    for dependency_id, expected in expected_lanes.items():
        row = inventory[dependency_id]
        if (row["disposition"], row["lane"]) != expected:
            raise AuthorizationError(f"{dependency_id} lane evidence mismatch")
        if row["uncovered_supported_consumers"] != []:
            raise AuthorizationError(f"{dependency_id} has an uncovered entry point")
    for candidate, (action, _lane, _declaration) in actions.items():
        if action != "remove-direct":
            continue
        dependency_id = candidate.rsplit("@", 1)[0]
        row = inventory[dependency_id]
        if row["disposition"] != "remove-direct":
            raise AuthorizationError(f"{dependency_id} removal evidence mismatch")
        if row["uncovered_supported_consumers"] != []:
            raise AuthorizationError(f"{dependency_id} has an uncovered entry point")


def validate_docker_authority(source: str) -> None:
    """Require one exact official uv source and forbid legacy pip authority."""

    normalized = " ".join(source.replace("\\\n", " ").split())
    exact_copy = "COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/"
    if source.count(exact_copy) != 1:
        raise AuthorizationError("Docker must copy one exact uv 0.11.21 source")
    if "COPY pyproject.toml uv.lock ./" not in source:
        raise AuthorizationError("Docker project authority metadata is missing")
    locked_sync = (
        "uv sync --locked --no-dev --extra provider-gemini --extra mcp --extra memvid"
    )
    if locked_sync not in normalized:
        raise AuthorizationError("Docker locked explicit-lane sync is missing")
    if "requirements.txt" in source or "pip install" in source:
        raise AuthorizationError("Docker contains duplicate legacy authority")
    if "/health" not in source or "requests" in source:
        raise AuthorizationError("Docker readiness is not stdlib and /health based")
    if '"--host", "127.0.0.1"' not in source or "0.0.0.0" in source:
        raise AuthorizationError("Docker runtime must remain loopback-only")


def validate_no_unrelated_version_churn(
    before_bytes: bytes,
    after_bytes: bytes,
    *,
    allowed_added: set[str],
    allowed_removed: set[str],
) -> None:
    """Reject version churn for every package shared by two lock snapshots."""

    before = _package_records(tomllib.loads(before_bytes.decode("utf-8")))
    after = _package_records(tomllib.loads(after_bytes.decode("utf-8")))
    added = set(after) - set(before)
    removed = set(before) - set(after)
    if not added <= allowed_added:
        raise AuthorizationError(
            f"unexpected lock additions: {sorted(added - allowed_added)}"
        )
    if not removed <= allowed_removed:
        raise AuthorizationError(
            f"unexpected lock removals: {sorted(removed - allowed_removed)}"
        )
    for name in set(before) & set(after):
        if before[name].get("version") != after[name].get("version"):
            raise AuthorizationError(f"unrelated version churn: {name}")


def test_prechange_authorization_gate() -> None:
    """Opt-in execution gate; run immediately before dependency edits."""

    if os.environ.get("AURA_DEPENDENCY_PRECHANGE_GATE") != "1":
        pytest.skip("pre-change dependency authorization gate is opt-in")
    validate_prechange_authorization(
        evidence_bytes=EVIDENCE_PATH.read_bytes(),
        summary_text=DECISION_SUMMARY_PATH.read_text(encoding="utf-8"),
        pyproject_bytes=PYPROJECT_PATH.read_bytes(),
        lock_bytes=LOCK_PATH.read_bytes(),
        now=datetime.now(UTC),
        actions=APPROVED_PYTHON_ACTIONS,
    )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (
            lambda values: values.update(
                evidence_bytes=values["evidence_bytes"] + b" "
            ),
            "evidence SHA-256",
        ),
        (
            lambda values: values.update(pyproject_bytes=b"changed"),
            "pyproject.toml",
        ),
    ],
)
def test_prechange_mutations_fail_closed(mutation: Any, match: str) -> None:
    values: dict[str, Any] = {
        "evidence_bytes": EVIDENCE_PATH.read_bytes(),
        "summary_text": DECISION_SUMMARY_PATH.read_text(encoding="utf-8"),
        "pyproject_bytes": PYPROJECT_PATH.read_bytes(),
        "lock_bytes": LOCK_PATH.read_bytes(),
        "now": datetime.now(UTC),
        "actions": copy.deepcopy(APPROVED_PYTHON_ACTIONS),
    }
    mutation(values)
    with pytest.raises(AuthorizationError, match=match):
        validate_prechange_authorization(**values)


def test_stale_evidence_and_action_widening_fail_closed_after_revision() -> None:
    document = json.loads(EVIDENCE_PATH.read_bytes())
    with pytest.raises(AuthorizationError, match="stale"):
        validate_evidence_scope(
            document,
            now=datetime(2030, 1, 1, tzinfo=UTC),
            actions=APPROVED_PYTHON_ACTIONS,
        )

    widened = copy.deepcopy(APPROVED_PYTHON_ACTIONS)
    widened["pypi:pyzbar@0.1.9"] = ("remove-direct", "base", None)
    with pytest.raises(AuthorizationError, match="exact approved Python subset"):
        validate_evidence_scope(
            document,
            now=datetime.now(UTC),
            actions=widened,
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (
            lambda document: next(
                row
                for row in document["packages"]
                if row["candidate_id"] == "pypi:pyzbar@0.1.9"
            ).update(verdict="OK"),
            "exact OK set",
        ),
        (
            lambda document: next(
                row
                for row in document["dependency_inventory"]
                if row["dependency_id"] == "pypi:mcp"
            ).update(lane="base"),
            "lane evidence",
        ),
        (
            lambda document: next(
                row
                for row in document["dependency_inventory"]
                if row["dependency_id"] == "pypi:memvid-sdk"
            ).update(uncovered_supported_consumers=["api-runtime"]),
            "uncovered entry point",
        ),
    ],
)
def test_evidence_scope_mutations_fail_closed(mutation: Any, match: str) -> None:
    document = json.loads(EVIDENCE_PATH.read_bytes())
    mutation(document)
    with pytest.raises(AuthorizationError, match=match):
        validate_evidence_scope(
            document,
            now=datetime.now(UTC),
            actions=APPROVED_PYTHON_ACTIONS,
        )


def test_manifest_contains_only_the_exact_approved_python_actions() -> None:
    document = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    direct = _direct_declarations(document)

    assert set(document["project"]["dependencies"]) == EXPECTED_BASE_DEPENDENCIES
    assert document["project"]["optional-dependencies"] == EXPECTED_OPTIONAL_LANES
    assert document["dependency-groups"] == {"dev": ["ruff==0.12.7"]}
    assert {name: direct[name] for name in REJECTED_DIRECT_DECLARATIONS} == (
        REJECTED_DIRECT_DECLARATIONS
    )
    for candidate, (action, _lane, declaration) in APPROVED_PYTHON_ACTIONS.items():
        name = candidate.removeprefix("pypi:").rsplit("@", 1)[0]
        if action in {"move", "remove-direct"}:
            assert name not in direct
        if declaration is not None:
            assert declaration not in document["project"]["dependencies"]


def test_rejected_lock_records_and_legacy_requirements_are_unchanged() -> None:
    lock = tomllib.loads(LOCK_PATH.read_text(encoding="utf-8"))
    records = _package_records(lock)
    for name, expected_hash in REJECTED_LOCK_RECORD_SHA256.items():
        assert _canonical_record(records[name]) == expected_hash
    assert _sha256(REQUIREMENTS_PATH.read_bytes()) == REQUIREMENTS_SHA256


def test_lock_contains_exact_lanes_and_ruff() -> None:
    lock = tomllib.loads(LOCK_PATH.read_text(encoding="utf-8"))
    records = _package_records(lock)
    assert records["ruff"]["version"] == "0.12.7"
    root = records["aura-backend"]
    metadata = root["metadata"]
    required = metadata["requires-dist"]
    observed_extras = {
        item["name"]: item.get("marker") for item in required if item.get("marker")
    }
    assert observed_extras == {
        "fastmcp": "extra == 'mcp'",
        "google-genai": "extra == 'provider-gemini'",
        "mcp": "extra == 'mcp'",
        "memvid-sdk": "extra == 'memvid'",
    }
    groups = metadata["requires-dev"]
    assert groups == {"dev": [{"name": "ruff", "specifier": "==0.12.7"}]}


def test_gemini_sdk_import_is_lazy_and_entrypoint_lanes_are_explicit() -> None:
    factory_path = ROOT / "aura_backend/providers/factory.py"
    gemini_path = ROOT / "aura_backend/providers/gemini.py"
    for path in (ROOT / "aura_backend/main.py", factory_path, gemini_path):
        module = ast.parse(path.read_text(encoding="utf-8"))
        top_level_imports = [
            node
            for node in module.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        rendered = "\n".join(ast.unparse(node) for node in top_level_imports)
        assert "google" not in rendered

    factory_source = factory_path.read_text(encoding="utf-8")
    gemini_source = gemini_path.read_text(encoding="utf-8")
    assert "if settings.kind is ProviderKind.GEMINI:" in factory_source
    assert "from .gemini import GeminiProvider" in factory_source
    assert "def _default_client_factory" in gemini_source
    assert "from google import genai" in gemini_source

    expected_paths = {
        "aura_backend.main": ROOT / "aura_backend/main.py",
        "aura_backend.runtime": ROOT / "aura_backend/runtime/__main__.py",
        "aura_backend.providers.gemini": gemini_path,
        "aura_backend.aura_server": ROOT / "aura_backend/aura_server.py",
        "aura_backend.aura_as_mcp_server": ROOT / "aura_backend/aura_as_mcp_server.py",
        "aura_backend.aura_real_memvid": ROOT / "aura_backend/aura_real_memvid.py",
    }
    assert set(expected_paths) == set(SUPPORTED_ENTRYPOINT_LANES)
    assert all(path.is_file() for path in expected_paths.values())
    assert all(lanes for lanes in SUPPORTED_ENTRYPOINT_LANES.values())


def test_docker_uses_one_exact_locked_uv_authority() -> None:
    source = DOCKERFILE_PATH.read_text(encoding="utf-8")
    validate_docker_authority(source)


def test_duplicate_docker_authority_fails_closed() -> None:
    approved_source = """\
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra provider-gemini --extra mcp --extra memvid
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('/health')"
CMD ["uvicorn", "aura_backend.main:create_app", "--host", "127.0.0.1"]
"""
    synthetic = (
        approved_source
        + "\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\n"
    )
    with pytest.raises(AuthorizationError, match="duplicate legacy authority"):
        validate_docker_authority(synthetic)


def test_unrelated_lock_version_churn_fails_closed() -> None:
    before = LOCK_PATH.read_bytes()
    document = tomllib.loads(before.decode("utf-8"))
    for package in document["package"]:
        if package["name"] == "httpx":
            package["version"] = "999.0.0"
            break
    mutated = before.replace(
        b'name = "httpx"\nversion = "0.28.1"',
        b'name = "httpx"\nversion = "999.0.0"',
        1,
    )
    with pytest.raises(AuthorizationError, match="version churn"):
        validate_no_unrelated_version_churn(
            before,
            mutated,
            allowed_added=set(),
            allowed_removed=set(),
        )
