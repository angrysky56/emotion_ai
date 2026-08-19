"""Regression tests for deterministic discovery and tracked runtime artifacts."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path, PurePosixPath


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = (
    REPOSITORY_ROOT
    / ".planning"
    / "evidence"
    / "phase-01"
    / "tracked-runtime-baseline.json"
)

RUNTIME_DIRECTORY_RE = re.compile(
    r"^(?:aura_chroma_db(?:_.+)?|mcp_aura_chroma_db|test_aura_chroma_db|"
    r"auto_backups|chromadb_backups|chromadb_emergency_backups|exports|sessions|"
    r"profiles?|users?|logs?|traces?)$",
    re.IGNORECASE,
)
RUNTIME_FILE_RE = re.compile(
    r"(?:\.db|\.sqlite|\.sqlite3)(?:-(?:shm|wal))?$|"
    r"^(?:chroma\.sqlite3|index_metadata\.pickle|data_level0\.bin|header\.bin|"
    r"length\.bin|link_lists\.bin|\.chromadb\.lock|recovery_report\.json)$",
    re.IGNORECASE,
)
SECRET_FILE_RE = re.compile(
    r"^(?:\.env(?:\..+)?|mcp_client_config\.json)$", re.IGNORECASE
)


def _git(*args: str) -> str:
    """Run a read-only Git command at the repository root."""

    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def is_runtime_candidate(path: str) -> bool:
    """Return whether a tracked path looks generated, sensitive, or stateful."""

    candidate = PurePosixPath(path)
    if candidate.name == ".gitkeep":
        return False
    if candidate.name in {".env.example", ".env.template", "example_mcp_client_config.json"}:
        return False
    return (
        any(RUNTIME_DIRECTORY_RE.fullmatch(part) for part in candidate.parts[:-1])
        or RUNTIME_FILE_RE.search(candidate.name) is not None
        or SECRET_FILE_RE.fullmatch(candidate.name) is not None
    )


def tracked_runtime_records() -> list[dict[str, object]]:
    """Return path, indexed byte size, and blob OID for tracked candidates."""

    records: list[dict[str, object]] = []
    for line in _git("ls-files", "-s").splitlines():
        metadata, path = line.split("\t", 1)
        _mode, blob_oid, _stage = metadata.split()
        if is_runtime_candidate(path):
            records.append(
                {
                    "path": path,
                    "bytes": int(_git("cat-file", "-s", blob_oid).strip()),
                    "blob_oid": blob_oid,
                }
            )
    return sorted(records, key=lambda record: str(record["path"]))


def unexpected_candidate_paths(
    current_paths: set[str], grandfathered_paths: set[str]
) -> set[str]:
    """Return newly tracked candidates not licensed by the exact baseline."""

    return current_paths - grandfathered_paths


def test_tracked_runtime_artifacts_match_content_free_baseline() -> None:
    """Existing anomalies are exact; no additional runtime artifact is tracked."""

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert baseline["schema_version"] == 1
    assert baseline["artifacts"] == tracked_runtime_records()


def test_synthetic_new_tracked_candidate_is_rejected() -> None:
    """The comparison rejects a new candidate even when old anomalies remain."""

    baseline_paths = {"aura_chroma_db/chroma.sqlite3"}
    current_paths = baseline_paths | {"exports/private-conversation.json"}
    assert unexpected_candidate_paths(current_paths, baseline_paths) == {
        "exports/private-conversation.json"
    }


def test_runtime_secret_and_generated_paths_are_ignored() -> None:
    """Representative future runtime paths cannot be added accidentally."""

    candidates = [
        "aura_chroma_db/new/chroma.sqlite3",
        "aura_backend/aura_chroma_db/new/chroma.sqlite3",
        "mcp_aura_chroma_db/chroma.sqlite3",
        "auto_backups/new/chroma.sqlite3",
        "aura_backend/auto_backups/new/chroma.sqlite3",
        "aura_backend/chromadb_backups/new/chroma.sqlite3",
        "aura_backend/aura_data/exports/export.json",
        "aura_backend/aura_data/sessions/session.json",
        "aura_backend/aura_data/profiles/profile.json",
        "aura_backend/aura_data/users/user.json",
        "logs/aura.log",
        "profiles/aura.prof",
        "traces/aura.trace",
        "runtime.sqlite3-wal",
        "runtime.sqlite3-shm",
        ".env.production",
        ".envrc",
        "mcp_client_config.json",
    ]

    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        cwd=REPOSITORY_ROOT,
        check=False,
        input="\n".join(candidates) + "\n",
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert set(ignored) == set(candidates)
