"""Static fail-closed contract for Aura's independent GitHub Actions lanes."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
EXPECTED_JOBS = {
    "deterministic-backend",
    "provider-live-ollama",
    "lint",
    "typing-python",
    "typing-frontend",
    "frontend-build",
    "environment-blocked",
}
PINNED_ACTIONS = {
    "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
    "actions/setup-node": "49933ea5288caeca8642d1e84afbd3f7d6820020",
    "astral-sh/setup-uv": "d0cc045d04ccac9d8b7881df0226f9e82c39688e",
    "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _load_workflow() -> dict[str, Any]:
    """Load workflow YAML without constructing arbitrary Python objects."""
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return steps


def _runs(job: dict[str, Any]) -> list[str]:
    return [str(step["run"]) for step in _steps(job) if "run" in step]


def _joined_runs(job: dict[str, Any]) -> str:
    return "\n".join(_runs(job))


def _step_index(job: dict[str, Any], command: str) -> int:
    for index, step in enumerate(_steps(job)):
        if command in str(step.get("run", "")):
            return index
    raise AssertionError(f"missing required command: {command}")


def _assert_unconditional_step(job: dict[str, Any], index: int) -> None:
    step = _steps(job)[index]
    assert "if" not in step
    assert step.get("continue-on-error") is not True


def _false_success_violations(workflow: dict[str, Any]) -> list[str]:
    """Return constructs that can relabel a failed command as successful."""
    violations: list[str] = []
    for name, job in workflow.get("jobs", {}).items():
        if job.get("continue-on-error") is True:
            violations.append(f"{name}:job-continue-on-error")
        for index, step in enumerate(job.get("steps", [])):
            if step.get("continue-on-error") is True:
                violations.append(f"{name}:{index}:continue-on-error")
            command = str(step.get("run", ""))
            for forbidden in ("|| true", "|| :", "; true", "pytest ||", "exit 0"):
                if forbidden in command:
                    violations.append(f"{name}:{index}:{forbidden}")
    return violations


def test_workflow_has_seven_exact_independent_truth_lanes() -> None:
    workflow = _load_workflow()
    jobs = workflow["jobs"]

    assert set(jobs) == EXPECTED_JOBS
    assert all(job.get("needs") != "provider-live-ollama" for job in jobs.values())
    assert jobs["deterministic-backend"].get("needs") is None
    assert jobs["provider-live-ollama"].get("needs") is None
    assert jobs["environment-blocked"].get("needs") is None


def test_all_external_actions_use_the_reviewed_full_commit_sha() -> None:
    workflow = _load_workflow()
    observed: set[str] = set()

    for job in workflow["jobs"].values():
        for step in _steps(job):
            reference = step.get("uses")
            if reference is None:
                continue
            action, separator, revision = str(reference).partition("@")
            assert separator == "@"
            assert FULL_SHA.fullmatch(revision), reference
            assert action in PINNED_ACTIONS, reference
            assert revision == PINNED_ACTIONS[action], reference
            observed.add(action)

    assert observed == set(PINNED_ACTIONS)


def test_required_python_lanes_install_and_run_from_the_uv_lock() -> None:
    workflow = _load_workflow()
    jobs = workflow["jobs"]

    deterministic = _joined_runs(jobs["deterministic-backend"])
    assert "uv sync --locked" in deterministic
    assert "uv run --locked --no-sync python -m pytest tests" in deterministic
    assert '-m "not live"' in deterministic
    assert "tests" in deterministic

    lint = _joined_runs(jobs["lint"])
    assert "uv sync --locked" in lint
    assert "uv run --locked --no-sync ruff check aura_backend tests" in lint
    for legacy_root in (
        "aura_backend/archive_unused",
        "aura_backend/scratch",
        "aura_backend/tests",
    ):
        assert f"--exclude {legacy_root}" in lint
    assert _false_success_violations(workflow) == []


def test_node_lanes_use_clean_installs_before_named_local_scripts() -> None:
    workflow = _load_workflow()
    jobs = workflow["jobs"]
    scripts = {
        "typing-python": "npm run typecheck:python",
        "typing-frontend": "npm run typecheck:frontend",
        "frontend-build": "npm run build",
    }

    for job_name, script in scripts.items():
        job = jobs[job_name]
        assert job["runs-on"] == "ubuntu-latest"
        install_index = _step_index(job, "npm ci")
        script_index = _step_index(job, script)
        assert install_index < script_index
        _assert_unconditional_step(job, install_index)
        _assert_unconditional_step(job, script_index)
        uses = [str(step.get("uses", "")) for step in _steps(job)]
        assert any(value.startswith("actions/checkout@") for value in uses)
        assert any(value.startswith("actions/setup-node@") for value in uses)


def test_pyright_authority_is_exactly_locked_but_not_claimed_locally() -> None:
    package = json.loads((REPOSITORY_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads(
        (REPOSITORY_ROOT / "package-lock.json").read_text(encoding="utf-8")
    )

    assert package["devDependencies"]["pyright"] == "1.1.413"
    assert package["scripts"]["typecheck:python"] == "pyright --project pyproject.toml"
    assert lock["packages"][""]["devDependencies"]["pyright"] == "1.1.413"
    assert lock["packages"]["node_modules/pyright"]["version"] == "1.1.413"
    assert "@google/genai" not in package.get("dependencies", {})


def test_live_lane_is_manual_self_hosted_strict_and_non_authoritative() -> None:
    workflow = _load_workflow()
    triggers = workflow["on"]
    job = workflow["jobs"]["provider-live-ollama"]
    commands = _joined_runs(job)

    assert "workflow_dispatch" in triggers
    assert "workflow_dispatch" in str(job["if"])
    assert set(job["runs-on"]) >= {"self-hosted", "linux", "x64", "aura-ollama"}
    assert job["env"] == {
        "AURA_RUN_LIVE": "1",
        "AURA_DEFAULT_PROVIDER": "ollama",
        "OLLAMA_MODEL": "ornith:latest",
        "AURA_LIVE_STRICT_AFTER_PREFLIGHT": "1",
    }
    assert "python -m aura_backend.runtime preflight" in commands
    assert "tests/live/test_ollama_ornith.py" in commands
    assert '-m "live and ollama"' in commands
    assert "--junitxml" in commands
    assert "skipped" in commands
    assert "else 4 if skipped" in commands
    assert job.get("needs") is None


def test_environment_blocked_lane_uploads_classification_and_never_says_passed() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["environment-blocked"]
    commands = _joined_runs(job)
    serialized = json.dumps(job, sort_keys=True).lower()

    assert "blocked" in str(job["name"]).lower()
    assert "passed" not in str(job["name"]).lower()
    assert "tests/test_legacy_classification.py" in commands
    assert "legacy-test-classification.json" in serialized
    uploads = [
        step for step in _steps(job) if str(step.get("uses", "")).startswith(
            "actions/upload-artifact@"
        )
    ]
    assert len(uploads) == 1
    assert uploads[0].get("if") == "always()"
    assert "exit 4" in commands


def test_adversarial_mutations_expose_swallowed_failure_and_reordered_pyright() -> None:
    workflow = _load_workflow()

    swallowed = copy.deepcopy(workflow)
    deterministic = swallowed["jobs"]["deterministic-backend"]
    test_index = _step_index(deterministic, "python -m pytest")
    deterministic["steps"][test_index]["run"] += " || true"
    assert _false_success_violations(swallowed)

    reordered = copy.deepcopy(workflow)
    typing = reordered["jobs"]["typing-python"]
    install_index = _step_index(typing, "npm ci")
    script_index = _step_index(typing, "npm run typecheck:python")
    typing["steps"][install_index], typing["steps"][script_index] = (
        typing["steps"][script_index],
        typing["steps"][install_index],
    )
    assert _step_index(typing, "npm ci") > _step_index(
        typing, "npm run typecheck:python"
    )

    floated = copy.deepcopy(workflow)
    checkout = next(
        step
        for step in floated["jobs"]["lint"]["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    checkout["uses"] = "actions/checkout@v4"
    _action, _separator, revision = checkout["uses"].partition("@")
    assert FULL_SHA.fullmatch(revision) is None
