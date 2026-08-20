"""Deterministic contracts for Aura's non-mutating runtime CLI."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from aura_backend.providers.base import ProviderHealth, ProviderHealthStatus
from aura_backend.runtime.cli import (
    REQUIRED_CHECK_NAMES,
    CheckStatus,
    CommandResult,
    PreflightCheck,
    PreflightProbes,
    PreflightReport,
    StorageObservation,
    build_preflight_report,
    main,
)


def _write_project_contract(root: Path) -> None:
    """Create the smallest coherent pair of read-only lock fixtures."""
    (root / "pyproject.toml").write_text(
        '[project]\nname = "aura-test"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    package = {
        "name": "aura-test",
        "version": "0.0.0",
        "dependencies": {"marked": "^18.0.3"},
        "devDependencies": {"vite": "^8.0.0"},
    }
    lock = {
        "name": "aura-test",
        "version": "0.0.0",
        "lockfileVersion": 3,
        "packages": {"": package},
    }
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")


def _passing_probes(commands: list[tuple[str, ...]] | None = None) -> PreflightProbes:
    def command_probe(command: tuple[str, ...], _timeout: float) -> CommandResult:
        if commands is not None:
            commands.append(command)
        assert not {
            "install",
            "sync",
            "pull",
            "download",
            "chmod",
            "kill",
            "pkill",
            "taskkill",
        }.intersection(command)
        if command[:2] == ("uv", "lock"):
            return CommandResult(returncode=0, stdout="")
        return CommandResult(returncode=0, stdout="version 1.2.3")

    return PreflightProbes(
        command=command_probe,
        port_available=lambda _host, _port: True,
        storage=lambda _path: StorageObservation(exists=True, writable=True),
        provider=lambda settings: ProviderHealth(
            provider=settings.provider.kind.value,
            model=settings.provider.model,
            status=ProviderHealthStatus.READY,
        ),
        app_factory=lambda: True,
    )


def test_preflight_complete_success_has_exact_registry_and_zero_exit(
    tmp_path: Path,
) -> None:
    _write_project_contract(tmp_path)

    report = build_preflight_report(
        environment={"OLLAMA_MODEL": "ornith:latest"},
        repository_root=tmp_path,
        probes=_passing_probes(),
    )

    assert tuple(check.name for check in report.checks) == REQUIRED_CHECK_NAMES
    assert all(check.status is CheckStatus.PASS for check in report.checks)
    assert report.status is CheckStatus.PASS
    assert report.exit_code == 0


@pytest.mark.parametrize("failed_name", REQUIRED_CHECK_NAMES)
def test_every_required_non_pass_fails_the_aggregate(
    tmp_path: Path,
    failed_name: str,
) -> None:
    _write_project_contract(tmp_path)
    passing = tuple(
        PreflightCheck(name=name, required=True, status=CheckStatus.PASS)
        for name in REQUIRED_CHECK_NAMES
    )
    checks = tuple(
        PreflightCheck(
            name=check.name,
            required=True,
            status=CheckStatus.FAILED,
            code="check_failed",
            remediation="follow_the_documented_remediation",
        )
        if check.name == failed_name
        else check
        for check in passing
    )

    report = PreflightReport.from_checks(checks)

    assert report.status is CheckStatus.FAILED
    assert report.exit_code != 0


@pytest.mark.parametrize(
    "checks",
    (
        (),
        (
            PreflightCheck(
                name=REQUIRED_CHECK_NAMES[0],
                required=True,
                status=CheckStatus.PASS,
            ),
        ),
        tuple(
            PreflightCheck(name=name, required=True, status=CheckStatus.PASS)
            for name in (*REQUIRED_CHECK_NAMES[:-1], REQUIRED_CHECK_NAMES[-2])
        ),
    ),
)
def test_preflight_rejects_empty_omitted_and_duplicate_evidence(
    checks: tuple[PreflightCheck, ...],
) -> None:
    with pytest.raises(ValueError, match="complete unique check registry"):
        PreflightReport.from_checks(checks)


def test_preflight_rejects_contradictory_success_evidence() -> None:
    with pytest.raises(ValueError, match="passing check cannot carry failure metadata"):
        PreflightCheck(
            name="python",
            required=True,
            status=CheckStatus.PASS,
            code="failed_but_claimed_pass",
        )


def test_preflight_distinguishes_all_non_success_states() -> None:
    assert {
        CheckStatus.MISSING.value,
        CheckStatus.FAILED.value,
        CheckStatus.BLOCKED.value,
        CheckStatus.NOT_RUN.value,
        CheckStatus.NOT_APPLICABLE.value,
        CheckStatus.PASS.value,
    } == {
        "missing",
        "failed",
        "blocked",
        "not_run",
        "not_applicable",
        "pass",
    }


def test_preflight_is_report_only_and_redacts_private_inputs(tmp_path: Path) -> None:
    secret = "SECRET-API-KEY-SENTINEL"
    private_path = tmp_path / secret
    _write_project_contract(tmp_path)
    commands: list[tuple[str, ...]] = []
    probes = _passing_probes(commands)
    probes = PreflightProbes(
        command=probes.command,
        port_available=probes.port_available,
        storage=lambda _path: StorageObservation(exists=False, writable=False),
        provider=lambda _settings: (_ for _ in ()).throw(RuntimeError(secret)),
        app_factory=probes.app_factory,
    )

    report = build_preflight_report(
        environment={
            "AURA_DATA_DIRECTORY": str(private_path),
            "OLLAMA_MODEL": "ornith:latest",
        },
        repository_root=tmp_path,
        probes=probes,
    )
    serialized = json.dumps(report.to_public_dict(), sort_keys=True)

    assert secret not in serialized
    assert str(private_path) not in serialized
    assert "Traceback" not in serialized
    assert all("install" not in command for command in commands)
    assert report.status is not CheckStatus.PASS


def test_busy_port_reports_only_safe_numeric_remediation(tmp_path: Path) -> None:
    _write_project_contract(tmp_path)
    passing = _passing_probes()
    probes = PreflightProbes(
        command=passing.command,
        port_available=lambda _host, _port: False,
        storage=passing.storage,
        provider=passing.provider,
        app_factory=passing.app_factory,
    )

    report = build_preflight_report(
        environment={"PORT": "8123", "OLLAMA_MODEL": "ornith:latest"},
        repository_root=tmp_path,
        probes=probes,
    )
    port = next(check for check in report.checks if check.name == "port")

    assert port.status is CheckStatus.BLOCKED
    assert port.safe_value == "8123"
    assert port.remediation == "choose_an_available_port"
    assert "kill" not in json.dumps(port.to_public_dict()).lower()


def test_module_entry_point_exposes_help_without_runtime_work() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "aura_backend.runtime", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )

    assert completed.returncode == 0
    assert "preflight" in completed.stdout
    assert "serve" in completed.stdout
    assert completed.stderr == ""


def test_main_emits_one_public_json_document(tmp_path: Path) -> None:
    _write_project_contract(tmp_path)
    output = io.StringIO()

    exit_code = main(
        ["preflight"],
        environment={"OLLAMA_MODEL": "ornith:latest"},
        repository_root=tmp_path,
        probes=_passing_probes(),
        stdout=output,
    )
    payload = json.loads(output.getvalue())

    assert exit_code == 0
    assert payload["command"] == "preflight"
    assert payload["status"] == "pass"
    assert payload["exit_code"] == 0
    assert [check["name"] for check in payload["checks"]] == list(
        REQUIRED_CHECK_NAMES
    )
