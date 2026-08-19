"""Completeness and truthfulness contract for legacy test-shaped scripts."""

from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    REPOSITORY_ROOT
    / ".planning"
    / "evidence"
    / "phase-01"
    / "legacy-test-classification.json"
)
LEGACY_ROOTS = (
    Path("aura_backend/tests"),
    Path("aura_backend/archive_unused"),
    Path("aura_backend/scratch"),
)
APPROVED_CATEGORIES = {
    "deterministic_candidate",
    "live_service_mcp",
    "optional_model_gpu",
    "destructive_concurrency",
    "migration_recovery_tool",
    "source_text_demo",
    "vacuous_diagnostic",
    "immutable_archive",
}
APPROVED_WRITE_BEHAVIORS = {
    "none",
    "temporary_only",
    "repository_relative_runtime",
    "production_runtime",
    "unknown",
}
UNTRUSTED_RESULT_SEMANTICS = {
    "printed_boolean_untrusted",
    "import_or_environment_blocked",
    "manual_exit_code_untrusted",
    "diagnostic_only",
    "archive_unexecuted",
}
MIGRATION_OWNERSHIP = {
    "aura_backend/tests/test_aura_parameter_fix.py": (
        "SmartMCPParameterHandler",
        "tests/test_smart_mcp_parameter_handler.py",
    ),
    "aura_backend/tests/test_mcp_bridge_fix.py": (
        "MCPGeminiBridge; ensure_json_serializable",
        "tests/test_mcp_bridge.py",
    ),
    "aura_backend/tests/test_numpy_serialization.py": (
        "ensure_json_serializable",
        "tests/test_json_serialization.py",
    ),
}


def discover_legacy_scripts(root: Path = REPOSITORY_ROOT) -> set[str]:
    """Discover only test-shaped Python scripts in the three legacy roots."""

    paths: set[str] = set()
    for relative_root in LEGACY_ROOTS:
        absolute_root = root / relative_root
        for candidate in absolute_root.rglob("*.py"):
            name = candidate.name
            if name.startswith("test_") or name.endswith("_test.py") or name == "quick_test.py":
                paths.add(candidate.relative_to(root).as_posix())
    return paths


def missing_classifications(discovered: set[str], classified: set[str]) -> set[str]:
    """Return discovered legacy scripts that have no manifest owner."""

    return discovered - classified


def test_manifest_classifies_every_legacy_script_exactly_once() -> None:
    """The manifest path set exactly equals current repository discovery."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest["entries"]
    classified_paths = [entry["path"] for entry in entries]

    assert manifest["schema_version"] == 1
    assert len(classified_paths) == len(set(classified_paths))
    assert set(classified_paths) == discover_legacy_scripts()


def test_manifest_schema_preserves_truthful_result_semantics() -> None:
    """No legacy print, boolean, import, or environment outcome is called pass."""

    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["entries"]
    required_fields = {
        "path",
        "category",
        "reason",
        "external_dependencies",
        "write_behavior",
        "production_symbol",
        "disposition",
        "replacement_test",
        "lane",
        "legacy_result_semantics",
    }

    for entry in entries:
        assert set(entry) == required_fields, entry["path"]
        assert entry["category"] in APPROVED_CATEGORIES, entry["path"]
        assert entry["write_behavior"] in APPROVED_WRITE_BEHAVIORS, entry["path"]
        assert entry["legacy_result_semantics"] in UNTRUSTED_RESULT_SEMANTICS, entry["path"]
        assert isinstance(entry["reason"], str) and entry["reason"].strip(), entry["path"]
        assert isinstance(entry["external_dependencies"], list), entry["path"]
        assert isinstance(entry["lane"], dict), entry["path"]
        assert set(entry["lane"]) == {"command", "markers"}, entry["path"]
        assert isinstance(entry["lane"]["markers"], list), entry["path"]
        assert entry["lane"]["command"] != "uv run python -m pytest -q", entry["path"]
        assert "pass" not in entry["legacy_result_semantics"].lower(), entry["path"]


def test_plan_01_04_owns_only_the_three_production_backed_migrations() -> None:
    """Migration candidates name production symbols and exact replacement tests."""

    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["entries"]
    migrated = {
        entry["path"]: (entry["production_symbol"], entry["replacement_test"])
        for entry in entries
        if entry["disposition"] == "migrate_in_plan_01_04"
    }
    assert migrated == MIGRATION_OWNERSHIP


def test_synthetic_unclassified_script_is_detected() -> None:
    """An added test-shaped script cannot disappear from classification."""

    assert missing_classifications(
        {"aura_backend/tests/test_existing.py", "aura_backend/scratch/test_new.py"},
        {"aura_backend/tests/test_existing.py"},
    ) == {"aura_backend/scratch/test_new.py"}
