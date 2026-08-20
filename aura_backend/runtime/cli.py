"""Canonical, report-only preflight and local process entry point for Aura.

Preflight inspects a fixed registry of startup prerequisites.  It never installs,
syncs, downloads, writes configuration, changes permissions, opens Aura storage,
starts services, or terminates processes.  Public diagnostics are built only from
fixed codes and validated metadata; source exceptions are deliberately discarded.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import IO

from aura_backend.providers.base import ProviderHealth, ProviderHealthStatus

from .config import RuntimeConfigurationError, RuntimeSettings

EXIT_OK = 0
EXIT_MISSING = 2
EXIT_FAILED = 3
EXIT_BLOCKED = 4
EXIT_NOT_RUN = 5
EXIT_NOT_APPLICABLE = 6
EXIT_USAGE = 64

REQUIRED_CHECK_NAMES = (
    "python",
    "uv",
    "node",
    "npm",
    "python_lock",
    "node_lock",
    "provider_config",
    "port",
    "storage",
    "provider_service",
    "provider_model",
    "app_readiness",
)

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_VERSION = re.compile(r"(?<![A-Za-z0-9])v?(\d+(?:\.\d+){1,3})(?![A-Za-z0-9])")


class CheckStatus(str, Enum):
    """Truthful preflight states; only :attr:`PASS` licenses startup."""

    PASS = "pass"
    MISSING = "missing"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"
    NOT_APPLICABLE = "not_applicable"


_EXIT_BY_STATUS = {
    CheckStatus.PASS: EXIT_OK,
    CheckStatus.MISSING: EXIT_MISSING,
    CheckStatus.FAILED: EXIT_FAILED,
    CheckStatus.BLOCKED: EXIT_BLOCKED,
    CheckStatus.NOT_RUN: EXIT_NOT_RUN,
    CheckStatus.NOT_APPLICABLE: EXIT_NOT_APPLICABLE,
}


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Bounded, content-bearing command observation kept inside preflight."""

    returncode: int
    stdout: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.returncode, int) or isinstance(self.returncode, bool):
            raise TypeError("returncode must be an integer")
        if not isinstance(self.stdout, str):
            raise TypeError("stdout must be text")


@dataclass(frozen=True, slots=True)
class StorageObservation:
    """Non-content storage metadata; the inspected path is never retained."""

    exists: bool
    writable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.exists, bool) or not isinstance(self.writable, bool):
            raise TypeError("storage flags must be booleans")


CommandProbe = Callable[[tuple[str, ...], float], CommandResult]
PortProbe = Callable[[str, int], bool]
StorageProbe = Callable[[Path], StorageObservation]
ProviderProbe = Callable[[RuntimeSettings], ProviderHealth]
AppFactoryProbe = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class PreflightProbes:
    """Injected inspection seams used by deterministic tests and the real CLI."""

    command: CommandProbe
    port_available: PortProbe
    storage: StorageProbe
    provider: ProviderProbe
    app_factory: AppFactoryProbe


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    """One allowlisted preflight fact with no raw path, content, or exception."""

    name: str
    required: bool
    status: CheckStatus
    code: str | None = None
    remediation: str | None = None
    safe_value: str | None = None

    def __post_init__(self) -> None:
        if self.name not in REQUIRED_CHECK_NAMES:
            raise ValueError("check name is not in the preflight registry")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean")
        if not isinstance(self.status, CheckStatus):
            raise TypeError("status must be CheckStatus")
        for value in (self.code, self.remediation, self.safe_value):
            if value is not None and _SAFE_TOKEN.fullmatch(value) is None:
                raise ValueError("public preflight metadata must be a safe token")
        if self.status is CheckStatus.PASS and (
            self.code is not None or self.remediation is not None
        ):
            raise ValueError("passing check cannot carry failure metadata")
        if self.status is not CheckStatus.PASS and self.code is None:
            raise ValueError("non-passing check requires a safe code")

    def to_public_dict(self) -> dict[str, object]:
        """Return the complete public allowlist for one check."""
        return {
            "name": self.name,
            "required": self.required,
            "status": self.status.value,
            "code": self.code,
            "remediation": self.remediation,
            "value": self.safe_value,
        }


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Validated complete preflight evidence with a derived aggregate."""

    status: CheckStatus
    exit_code: int
    checks: tuple[PreflightCheck, ...]

    @classmethod
    def from_checks(cls, checks: Sequence[PreflightCheck]) -> PreflightReport:
        """Validate the exact registry and derive status from every required row."""
        observed = tuple(checks)
        names = tuple(check.name for check in observed)
        if (
            len(observed) != len(REQUIRED_CHECK_NAMES)
            or len(set(names)) != len(names)
            or set(names) != set(REQUIRED_CHECK_NAMES)
        ):
            raise ValueError("preflight requires a complete unique check registry")
        by_name = {check.name: check for check in observed}
        ordered = tuple(by_name[name] for name in REQUIRED_CHECK_NAMES)
        if any(not check.required for check in ordered):
            raise ValueError("the canonical preflight registry must remain required")

        non_pass = tuple(
            check.status for check in ordered if check.status is not CheckStatus.PASS
        )
        if not non_pass:
            status = CheckStatus.PASS
        else:
            status = next(
                candidate
                for candidate in (
                    CheckStatus.FAILED,
                    CheckStatus.BLOCKED,
                    CheckStatus.MISSING,
                    CheckStatus.NOT_RUN,
                    CheckStatus.NOT_APPLICABLE,
                )
                if candidate in non_pass
            )
        return cls(status=status, exit_code=_EXIT_BY_STATUS[status], checks=ordered)

    def to_public_dict(self) -> dict[str, object]:
        """Return one stable JSON object with no ambient or source data."""
        return {
            "schema_version": 1,
            "command": "preflight",
            "status": self.status.value,
            "exit_code": self.exit_code,
            "checks": [check.to_public_dict() for check in self.checks],
        }


def _default_command_probe(command: tuple[str, ...], timeout: float) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, PermissionError):
        return CommandResult(returncode=127)
    except (OSError, subprocess.TimeoutExpired):
        return CommandResult(returncode=126)
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout[:256],
    )


def _default_port_probe(host: str, port: int) -> bool:
    try:
        addresses = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
            flags=socket.AI_PASSIVE,
        )
    except OSError:
        return False
    for family, socktype, protocol, _canonical, address in addresses:
        candidate = socket.socket(family, socktype, protocol)
        try:
            candidate.bind(address)
        except OSError:
            continue
        finally:
            candidate.close()
        return True
    return False


def _default_storage_probe(path: Path) -> StorageObservation:
    """Inspect existing directory permissions without opening or writing content."""
    try:
        exists = path.is_dir()
        writable = exists and os.access(path, os.W_OK | os.X_OK)
    except OSError:
        return StorageObservation(exists=False, writable=False)
    return StorageObservation(exists=exists, writable=writable)


async def _observe_provider(settings: RuntimeSettings) -> ProviderHealth:
    from aura_backend.providers.factory import ModelProviderFactory

    provider = ModelProviderFactory.create_provider(settings.provider)
    try:
        async with asyncio.timeout(settings.preflight_timeout_seconds):
            return await provider.health()
    finally:
        await provider.aclose()


def _default_provider_probe(settings: RuntimeSettings) -> ProviderHealth:
    return asyncio.run(_observe_provider(settings))


def _default_app_factory_probe() -> bool:
    """Construct only the resource-free FastAPI shell and inspect its route table."""
    from aura_backend.main import create_app

    application = create_app()
    paths = {getattr(route, "path", None) for route in application.routes}
    return "/live" in paths and "/ready" in paths


def default_preflight_probes() -> PreflightProbes:
    """Return production probes, all bounded and non-mutating."""
    return PreflightProbes(
        command=_default_command_probe,
        port_available=_default_port_probe,
        storage=_default_storage_probe,
        provider=_default_provider_probe,
        app_factory=_default_app_factory_probe,
    )


def _pass(name: str, *, safe_value: str | None = None) -> PreflightCheck:
    return PreflightCheck(
        name=name,
        required=True,
        status=CheckStatus.PASS,
        safe_value=safe_value,
    )


def _non_pass(
    name: str,
    status: CheckStatus,
    code: str,
    remediation: str,
    *,
    safe_value: str | None = None,
) -> PreflightCheck:
    return PreflightCheck(
        name=name,
        required=True,
        status=status,
        code=code,
        remediation=remediation,
        safe_value=safe_value,
    )


def _version_check(
    name: str,
    command: tuple[str, ...],
    probes: PreflightProbes,
) -> PreflightCheck:
    try:
        result = probes.command(command, 5.0)
    except Exception:
        result = CommandResult(returncode=126)
    if result.returncode == 127:
        return _non_pass(name, CheckStatus.MISSING, f"{name}_missing", f"install_{name}")
    if result.returncode != 0:
        return _non_pass(name, CheckStatus.FAILED, f"{name}_unavailable", f"verify_{name}")
    match = _VERSION.search(result.stdout)
    if match is None:
        return _non_pass(name, CheckStatus.FAILED, f"{name}_version_unknown", f"verify_{name}")
    return _pass(name, safe_value=match.group(1))


def _python_lock_check(root: Path, probes: PreflightProbes, uv_ready: bool) -> PreflightCheck:
    if not (root / "uv.lock").is_file():
        return _non_pass(
            "python_lock",
            CheckStatus.MISSING,
            "python_lock_missing",
            "run_uv_lock_explicitly",
        )
    if not (root / "pyproject.toml").is_file():
        return _non_pass(
            "python_lock",
            CheckStatus.MISSING,
            "python_manifest_missing",
            "restore_python_manifest",
        )
    if not uv_ready:
        return _non_pass(
            "python_lock",
            CheckStatus.NOT_RUN,
            "uv_not_available",
            "install_uv",
        )
    try:
        result = probes.command(("uv", "lock", "--check", "--offline"), 30.0)
    except Exception:
        result = CommandResult(returncode=126)
    if result.returncode != 0:
        return _non_pass(
            "python_lock",
            CheckStatus.FAILED,
            "python_lock_stale",
            "run_uv_lock_explicitly",
        )
    return _pass("python_lock")


def _read_json_object(path: Path) -> dict[str, object] | None:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _node_lock_check(root: Path) -> PreflightCheck:
    package_path = root / "package.json"
    lock_path = root / "package-lock.json"
    if not package_path.is_file() or not lock_path.is_file():
        return _non_pass(
            "node_lock",
            CheckStatus.MISSING,
            "node_lock_missing",
            "run_npm_install_explicitly",
        )
    package = _read_json_object(package_path)
    lock = _read_json_object(lock_path)
    if package is None or lock is None:
        return _non_pass(
            "node_lock",
            CheckStatus.FAILED,
            "node_lock_invalid",
            "regenerate_node_lock_explicitly",
        )
    packages = lock.get("packages")
    locked_root = packages.get("") if isinstance(packages, dict) else None
    if not isinstance(locked_root, dict):
        return _non_pass(
            "node_lock",
            CheckStatus.FAILED,
            "node_lock_invalid",
            "regenerate_node_lock_explicitly",
        )
    fields = ("name", "version", "dependencies", "devDependencies")
    if any(package.get(field, {}) != locked_root.get(field, {}) for field in fields):
        return _non_pass(
            "node_lock",
            CheckStatus.FAILED,
            "node_lock_stale",
            "regenerate_node_lock_explicitly",
        )
    return _pass("node_lock")


def _provider_checks(
    settings: RuntimeSettings | None,
    probes: PreflightProbes,
) -> tuple[PreflightCheck, PreflightCheck]:
    if settings is None:
        return (
            _non_pass(
                "provider_service",
                CheckStatus.NOT_RUN,
                "provider_config_blocked",
                "review_provider_configuration",
            ),
            _non_pass(
                "provider_model",
                CheckStatus.NOT_RUN,
                "provider_config_blocked",
                "review_provider_configuration",
            ),
        )
    try:
        observation = probes.provider(settings)
    except Exception:
        return (
            _non_pass(
                "provider_service",
                CheckStatus.FAILED,
                "provider_probe_failed",
                "verify_selected_provider_service",
            ),
            _non_pass(
                "provider_model",
                CheckStatus.NOT_RUN,
                "provider_service_unavailable",
                "verify_selected_provider_model",
            ),
        )
    if (
        not isinstance(observation, ProviderHealth)
        or observation.provider != settings.provider.kind.value
        or observation.model != settings.provider.model
    ):
        blocked = _non_pass(
            "provider_service",
            CheckStatus.BLOCKED,
            "provider_identity_mismatch",
            "verify_selected_provider_service",
        )
        return (
            blocked,
            _non_pass(
                "provider_model",
                CheckStatus.BLOCKED,
                "provider_identity_mismatch",
                "verify_selected_provider_model",
            ),
        )
    if observation.status is ProviderHealthStatus.READY:
        return _pass("provider_service"), _pass(
            "provider_model", safe_value=settings.provider.model
        )
    if observation.status is ProviderHealthStatus.MODEL_NOT_FOUND:
        return _pass("provider_service"), _non_pass(
            "provider_model",
            CheckStatus.MISSING,
            "provider_model_missing",
            "install_selected_model_explicitly",
            safe_value=settings.provider.model,
        )
    if observation.status is ProviderHealthStatus.UNAVAILABLE:
        return (
            _non_pass(
                "provider_service",
                CheckStatus.FAILED,
                "provider_service_unavailable",
                "start_selected_provider_service",
            ),
            _non_pass(
                "provider_model",
                CheckStatus.NOT_RUN,
                "provider_service_unavailable",
                "verify_selected_provider_model",
            ),
        )
    if observation.status is ProviderHealthStatus.NOT_CONFIGURED:
        return (
            _non_pass(
                "provider_service",
                CheckStatus.NOT_RUN,
                "provider_not_configured",
                "review_provider_configuration",
            ),
            _non_pass(
                "provider_model",
                CheckStatus.NOT_RUN,
                "provider_not_configured",
                "review_provider_configuration",
            ),
        )
    return (
        _non_pass(
            "provider_service",
            CheckStatus.BLOCKED,
            "provider_status_unknown",
            "verify_selected_provider_service",
        ),
        _non_pass(
            "provider_model",
            CheckStatus.BLOCKED,
            "provider_status_unknown",
            "verify_selected_provider_model",
        ),
    )


def build_preflight_report(
    *,
    environment: Mapping[str, str | None],
    repository_root: Path,
    probes: PreflightProbes | None = None,
) -> PreflightReport:
    """Run the complete bounded check registry without mutating project or machine."""
    selected_probes = probes or default_preflight_probes()
    root = repository_root.resolve(strict=False)
    checks: list[PreflightCheck] = []

    for name, command in (
        ("python", (sys.executable, "--version")),
        ("uv", ("uv", "--version")),
        ("node", ("node", "--version")),
        ("npm", ("npm", "--version")),
    ):
        checks.append(_version_check(name, command, selected_probes))

    uv_ready = checks[1].status is CheckStatus.PASS
    checks.append(_python_lock_check(root, selected_probes, uv_ready))
    checks.append(_node_lock_check(root))

    try:
        settings = RuntimeSettings.from_mapping(environment)
    except (RuntimeConfigurationError, TypeError, ValueError):
        settings = None
        checks.append(
            _non_pass(
                "provider_config",
                CheckStatus.BLOCKED,
                "provider_configuration_invalid",
                "review_provider_configuration",
            )
        )
    else:
        checks.append(
            _pass(
                "provider_config",
                safe_value=settings.provider.kind.value,
            )
        )

    if settings is None:
        checks.append(
            _non_pass(
                "port",
                CheckStatus.NOT_RUN,
                "runtime_configuration_invalid",
                "review_runtime_configuration",
            )
        )
        checks.append(
            _non_pass(
                "storage",
                CheckStatus.NOT_RUN,
                "runtime_configuration_invalid",
                "review_runtime_configuration",
            )
        )
    else:
        try:
            port_available = selected_probes.port_available(settings.host, settings.port)
        except Exception:
            port_available = False
        checks.append(
            _pass("port", safe_value=str(settings.port))
            if port_available
            else _non_pass(
                "port",
                CheckStatus.BLOCKED,
                "port_unavailable",
                "choose_an_available_port",
                safe_value=str(settings.port),
            )
        )

        paths = [settings.storage_root]
        chroma_path = environment.get("CHROMA_PERSIST_DIRECTORY")
        if isinstance(chroma_path, str) and chroma_path.strip():
            paths.append(Path(chroma_path.strip()))
        observations: list[StorageObservation] = []
        try:
            for path in dict.fromkeys(paths):
                observations.append(selected_probes.storage(path))
        except Exception:
            observations = [StorageObservation(exists=False, writable=False)]
        if observations and all(item.exists and item.writable for item in observations):
            checks.append(_pass("storage"))
        elif any(not item.exists for item in observations):
            checks.append(
                _non_pass(
                    "storage",
                    CheckStatus.MISSING,
                    "storage_path_missing",
                    "create_storage_path_explicitly",
                )
            )
        else:
            checks.append(
                _non_pass(
                    "storage",
                    CheckStatus.BLOCKED,
                    "storage_not_writable",
                    "choose_writable_storage_path",
                )
            )

    provider_service, provider_model = _provider_checks(settings, selected_probes)
    checks.extend((provider_service, provider_model))

    try:
        factory_ready = selected_probes.app_factory()
    except Exception:
        factory_ready = False
    prerequisites_ready = all(
        check.status is CheckStatus.PASS for check in checks if check.required
    )
    checks.append(
        _pass("app_readiness")
        if factory_ready and prerequisites_ready
        else _non_pass(
            "app_readiness",
            CheckStatus.BLOCKED,
            "startup_prerequisite_failed" if factory_ready else "app_factory_unavailable",
            "resolve_preflight_failures",
        )
    )
    return PreflightReport.from_checks(checks)


def build_parser() -> argparse.ArgumentParser:
    """Build the cross-platform runtime parser without reading ambient state."""
    parser = argparse.ArgumentParser(prog="aura-runtime")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="report startup readiness without changes")
    serve = commands.add_parser("serve", help="preflight and run owned local services")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    modes = serve.add_mutually_exclusive_group()
    modes.add_argument("--backend-only", action="store_true")
    modes.add_argument("--frontend-only", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str | None] | None = None,
    repository_root: Path | None = None,
    probes: PreflightProbes | None = None,
    stdout: IO[str] | None = None,
) -> int:
    """Run one runtime command and return its documented integer status."""
    arguments = build_parser().parse_args(argv)
    output = stdout or sys.stdout
    selected_environment: Mapping[str, str | None] = (
        dict(os.environ) if environment is None else environment
    )
    root = repository_root or Path(__file__).resolve().parents[2]
    if arguments.command == "preflight":
        report = build_preflight_report(
            environment=selected_environment,
            repository_root=root,
            probes=probes,
        )
        print(json.dumps(report.to_public_dict(), sort_keys=True), file=output)
        return report.exit_code
    # Implemented by the serve TDD cycle below.  Keeping the parser complete now
    # makes the public module entry point testable without starting any service.
    print(
        json.dumps(
            {
                "schema_version": 1,
                "command": "serve",
                "status": "not_run",
                "exit_code": EXIT_NOT_RUN,
                "code": "serve_not_implemented",
            },
            sort_keys=True,
        ),
        file=output,
    )
    return EXIT_NOT_RUN

