"""Static fail-closed contract for Aura's independent GitHub Actions lanes."""

from __future__ import annotations

import copy
import html
import json
import re
import shlex
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
PHASE_DIRECTORY = (
    REPOSITORY_ROOT
    / ".planning"
    / "phases"
    / "02-provider-and-runtime-core"
)
VALIDATION_PATH = (
    REPOSITORY_ROOT
    / ".planning"
    / "phases"
    / "02-provider-and-runtime-core"
    / "02-VALIDATION.md"
)
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
EXPECTED_PLAN_NAMES = tuple(f"02-{number:02d}-PLAN.md" for number in range(1, 21))
PLAN_TASK_ID = re.compile(r"<name>(?:Task )?(02-\d{2}-\d{2}):")
AUTOMATED_BODY = re.compile(r"<automated>(.*?)</automated>", re.DOTALL)
VERIFICATION_BODY = re.compile(r"<verification>(.*?)</verification>", re.DOTALL)
BACKTICK_COMMAND = re.compile(r"`([^`\n]+)`")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)
UV_RUN_OPTIONS_WITH_VALUES = {
    "--allow-insecure-host",
    "--cache-dir",
    "--color",
    "--config-file",
    "--config-setting",
    "--config-settings-package",
    "--default-index",
    "--directory",
    "--env-file",
    "--exclude-newer",
    "--exclude-newer-package",
    "--extra",
    "--extra-index-url",
    "--find-links",
    "--group",
    "--index",
    "--index-strategy",
    "--index-url",
    "--keyring-provider",
    "--link-mode",
    "--no-binary-package",
    "--no-build-isolation-package",
    "--no-build-package",
    "--no-editable-package",
    "--no-extra",
    "--no-group",
    "--no-sources-package",
    "--only-group",
    "--package",
    "--prerelease",
    "--project",
    "--python",
    "--python-platform",
    "--refresh-package",
    "--reinstall-package",
    "--resolution",
    "--upgrade-group",
    "--upgrade-package",
    "--with",
    "--with-editable",
    "--with-requirements",
    "-C",
    "-P",
    "-f",
    "-i",
    "-p",
    "-w",
}


def _load_workflow() -> dict[str, Any]:
    """Load workflow YAML without constructing arbitrary Python objects."""
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _phase_plan_paths(directory: Path = PHASE_DIRECTORY) -> tuple[Path, ...]:
    """Return the complete, unique Phase 2 plan inventory or fail closed."""
    paths = tuple(sorted(directory.glob("02-*-PLAN.md")))
    names = tuple(path.name for path in paths)
    assert names == EXPECTED_PLAN_NAMES, (
        f"Phase 2 plan inventory mismatch: expected {EXPECTED_PLAN_NAMES}, got {names}"
    )
    return paths


def _plan_commands(document: str, *, source: str) -> tuple[str, ...]:
    """Extract schema-defined executable fields, never ordinary plan prose."""
    automated = tuple(
        html.unescape(body).strip() for body in AUTOMATED_BODY.findall(document)
    )
    assert automated, f"{source}: no automated command surfaces"
    assert all(automated), f"{source}: empty automated command surface"

    verification_blocks = VERIFICATION_BODY.findall(document)
    assert len(verification_blocks) == 1, (
        f"{source}: expected one plan-level verification section"
    )
    commands = list(automated)
    verification = verification_blocks[0]

    for fenced in re.findall(
        r"```(?:bash|sh|shell|powershell)?\s*\n(.*?)```",
        verification,
        re.DOTALL | re.IGNORECASE,
    ):
        command = html.unescape(fenced).strip()
        assert command, f"{source}: empty verification code cell"
        commands.append(command)

    command_prefixes = ("", "red:", "green:", "docs green:", "run", "optional only:")
    for line in verification.splitlines():
        bullet = re.match(r"^\s*-\s*(.*?)`", line)
        if bullet is None:
            continue
        prefix = bullet.group(1).strip().lower()
        if not any(prefix == allowed or prefix.startswith(f"{allowed} ") for allowed in command_prefixes):
            continue
        for command in BACKTICK_COMMAND.findall(line):
            decoded = html.unescape(command).strip()
            assert decoded, f"{source}: empty verification list command"
            commands.append(decoded)

    return tuple(commands)


def _validation_commands(document: str) -> tuple[tuple[str, str], ...]:
    """Parse the task ID and command columns from the Phase 2 validation matrix."""
    rows = [line for line in document.splitlines() if line.strip().startswith("|")]
    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if "Task ID" in row and "Exact automated command" in row
        ),
        None,
    )
    assert header_index is not None, "validation matrix header is missing"
    header = [cell.strip() for cell in rows[header_index].strip().strip("|").split("|")]
    command_index = header.index("Exact automated command")
    task_index = header.index("Task ID")

    extracted: list[tuple[str, str]] = []
    for row in rows[header_index + 2 :]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != len(header) or not re.fullmatch(r"02-\d{2}-\d{2}", cells[task_index]):
            break
        match = re.fullmatch(r"`(.+)`", cells[command_index])
        assert match is not None, f"{cells[task_index]}: missing executable command"
        extracted.append((cells[task_index], html.unescape(match.group(1)).strip()))

    assert extracted, "validation matrix has no executable command rows"
    task_ids = [task_id for task_id, _command in extracted]
    assert len(task_ids) == len(set(task_ids)), "validation matrix has duplicate task IDs"
    assert all(command for _task_id, command in extracted), (
        "validation matrix contains an empty command"
    )
    return tuple(extracted)


def _workflow_run_commands(workflow: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Return every non-empty CI run scalar and require every job to own one."""
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict) and jobs, "workflow jobs are missing or empty"
    extracted: list[tuple[str, str]] = []
    for job_name, job in jobs.items():
        assert isinstance(job, dict), f"{job_name}: job must be a mapping"
        runs = _runs(job)
        assert runs, f"{job_name}: job has no run blocks"
        assert all(run.strip() for run in runs), f"{job_name}: empty run block"
        extracted.extend((str(job_name), run) for run in runs)
    assert extracted, "workflow has no executable run blocks"
    return tuple(extracted)


def _shell_segments(command: str) -> tuple[str, ...]:
    """Split shell operators outside quotes after decoding stored representations."""
    normalized = html.unescape(command)
    normalized = re.sub(r"\\[ \t]*\r?\n", " ", normalized)
    segments: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0

    def flush() -> None:
        segment = "".join(buffer).strip()
        buffer.clear()
        if segment:
            segments.append(segment)

    while index < len(normalized):
        character = normalized[index]
        if escaped:
            buffer.append(character)
            escaped = False
            index += 1
            continue
        if character == "\\" and quote != "'":
            buffer.append(character)
            escaped = True
            index += 1
            continue
        if character in {"'", '"'}:
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
            buffer.append(character)
            index += 1
            continue
        if quote is None and character in {";", "\n", "&", "|"}:
            flush()
            if character in {"&", "|"} and index + 1 < len(normalized):
                if normalized[index + 1] == character:
                    index += 1
            index += 1
            continue
        buffer.append(character)
        index += 1

    assert quote is None and not escaped, "unbalanced shell quoting or escaping"
    flush()
    assert segments, "executable command contains no shell segments"
    return tuple(segments)


def _skip_assignments(tokens: list[str], index: int) -> int:
    while index < len(tokens) and ASSIGNMENT.fullmatch(tokens[index]):
        index += 1
    return index


def _uv_command_index(tokens: list[str], uv_index: int) -> int:
    """Resolve the wrapped executable across uv global and run option variants."""
    try:
        run_index = tokens.index("run", uv_index + 1)
    except ValueError as error:
        raise AssertionError("uv executable surface is missing the run subcommand") from error

    index = run_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        option_name = token.split("=", 1)[0]
        if token.startswith("-"):
            if option_name in UV_RUN_OPTIONS_WITH_VALUES and "=" not in token:
                assert index + 1 < len(tokens), f"uv option {token} is missing its value"
                index += 2
            else:
                index += 1
            continue
        break
    assert index < len(tokens), "uv run surface is missing its executable"
    return index


def _resolved_command(segment: str) -> tuple[list[str], int]:
    """Tokenize one shell segment and locate its actual executable token."""
    try:
        tokens = shlex.split(segment, comments=True, posix=True)
    except ValueError as error:
        raise AssertionError(f"unparseable shell segment: {segment!r}") from error
    assert tokens, "empty shell segment"

    index = 0
    while index < len(tokens) and tokens[index] in {"!", "if", "then", "elif", "else", "do"}:
        index += 1
    index = _skip_assignments(tokens, index)
    assert index < len(tokens), f"segment has no executable: {segment!r}"

    if tokens[index] == "env":
        index += 1
        while index < len(tokens) and tokens[index].startswith("-"):
            option = tokens[index]
            index += 1
            if option in {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}:
                assert index < len(tokens), f"env option {option} is missing its value"
                index += 1
        index = _skip_assignments(tokens, index)
        assert index < len(tokens), f"env surface has no executable: {segment!r}"

    if tokens[index] == "uv" and "run" in tokens[index + 1 :]:
        index = _uv_command_index(tokens, index)
    return tokens, index


def _pytest_console_violations(
    surfaces: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    """Return labels whose resolved executable is the pytest console script."""
    violations: list[str] = []
    for label, command in surfaces:
        for segment in _shell_segments(command):
            tokens, executable_index = _resolved_command(segment)
            executable = tokens[executable_index]
            if executable == "pytest":
                violations.append(f"{label}: {segment}")
            elif executable == "python" and tokens[executable_index + 1 : executable_index + 3] == ["-m", "pytest"]:
                continue
    return tuple(violations)


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


def test_phase2_pytest_commands_are_complete_parsed_and_module_safe() -> None:
    """Every executable Phase 2 command surface is present and import-safe."""
    plan_surfaces: list[tuple[str, str]] = []
    planned_task_ids: list[str] = []
    for path in _phase_plan_paths():
        document = path.read_text(encoding="utf-8")
        commands = _plan_commands(document, source=path.name)
        plan_surfaces.extend((path.name, command) for command in commands)
        planned_task_ids.extend(PLAN_TASK_ID.findall(document))

    validation_document = VALIDATION_PATH.read_text(encoding="utf-8")
    validation_rows = _validation_commands(validation_document)
    validation_task_ids = [task_id for task_id, _command in validation_rows]
    assert len(planned_task_ids) == len(set(planned_task_ids))
    assert set(validation_task_ids) == set(planned_task_ids)

    workflow_surfaces = _workflow_run_commands(_load_workflow())
    all_surfaces = (
        plan_surfaces
        + [("02-VALIDATION.md", command) for _task_id, command in validation_rows]
        + [(f"ci.yml:{job}", command) for job, command in workflow_surfaces]
    )
    assert _pytest_console_violations(all_surfaces) == ()


def test_plan_02_17_has_exactly_three_corrected_pytest_invocations() -> None:
    document = (PHASE_DIRECTORY / "02-17-PLAN.md").read_text(encoding="utf-8")
    decoded = html.unescape(document)
    exact = (
        "uv run --locked --no-sync python -m pytest "
        "tests/test_node_dependency_contract.py -q"
    )
    automated = tuple(
        html.unescape(body).strip() for body in AUTOMATED_BODY.findall(document)
    )

    assert decoded.count(exact) == 3
    assert automated == (
        exact,
        f"{exact} && npm run typecheck:frontend && npm run build",
    )
    assert "uv run --locked --no-sync pytest" not in decoded


def test_shell_parser_rejects_console_pytest_across_boundaries_and_uv_flags() -> None:
    invalid = (
        "pytest tests -q",
        "uv run pytest tests -q",
        "uv --quiet run --locked --no-sync pytest tests -q",
        "python -m pytest tests -q && uv run --isolated pytest tests/other.py",
        "python -m pytest tests -q &amp;&amp; pytest tests/other.py",
        "python -m pytest tests -q; uv run -q pytest tests/other.py",
        "python -m pytest tests -q\nuv run --offline pytest tests/other.py",
        "python -m pytest tests -q | pytest tests/other.py",
    )
    for command in invalid:
        assert _pytest_console_violations((("fixture", command),)), command


def test_shell_parser_accepts_module_mode_and_ignores_pytest_arguments() -> None:
    valid = (
        "python -m pytest tests -q",
        "AURA_TEST=1 python -m pytest tests -q",
        "env -u TOKEN AURA_TEST=1 python -m pytest tests -q",
        "uv run --locked --no-sync python -m pytest tests -q",
        "uv --quiet run --python 3.12 --with pytest python -m pytest tests -q",
        "echo pytest",
        "python scripts/check_name.py pytest",
        "touch pytest",
        "echo pytest-results.xml",
        "uv run --locked echo pytest",
    )
    for command in valid:
        assert _pytest_console_violations((("fixture", command),)) == (), command


def test_shell_parser_fails_closed_on_unbalanced_or_empty_commands() -> None:
    for command in ("", "python -m pytest 'tests"):
        try:
            _pytest_console_violations((("fixture", command),))
        except AssertionError:
            pass
        else:
            raise AssertionError(f"expected fail-closed parse for {command!r}")


def test_plan_extraction_ignores_explanatory_pytest_prose() -> None:
    document = """
<task><name>02-99-01: fixture</name>
<verify><automated>python -m pytest tests -q</automated></verify></task>
<verification>
This explanatory prose mentions pytest and `pytest` but is not a command-form
code cell or list entry.
</verification>
"""
    assert _plan_commands(document, source="fixture") == (
        "python -m pytest tests -q",
    )


def test_command_surface_discovery_fails_closed(tmp_path: Path) -> None:
    for number in range(1, 20):
        (tmp_path / f"02-{number:02d}-PLAN.md").write_text(
            "<automated>python -m pytest tests</automated>", encoding="utf-8"
        )
    try:
        _phase_plan_paths(tmp_path)
    except AssertionError:
        pass
    else:
        raise AssertionError("missing Phase 2 plan was accepted")

    for document in (
        "<verification></verification>",
        "<automated> </automated><verification></verification>",
    ):
        try:
            _plan_commands(document, source="fixture")
        except AssertionError:
            pass
        else:
            raise AssertionError("missing or empty plan command surface was accepted")

    for document in ("", "| Task ID | Exact automated command |\n|---|---|"):
        try:
            _validation_commands(document)
        except AssertionError:
            pass
        else:
            raise AssertionError("missing or empty validation matrix was accepted")

    for workflow in ({}, {"jobs": {}}, {"jobs": {"empty": {"steps": []}}}):
        try:
            _workflow_run_commands(workflow)
        except AssertionError:
            pass
        else:
            raise AssertionError("missing or empty CI executable surface was accepted")


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
