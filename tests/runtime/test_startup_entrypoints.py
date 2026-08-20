"""Offline contracts for Aura's supported startup wrapper scripts.

The tests use command spies and static inspection only.  They never start Aura,
install packages, modify the active environment, or contact a network service.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROOT_LINUX = REPOSITORY_ROOT / "start_full_system.sh"
ROOT_WINDOWS = REPOSITORY_ROOT / "start_full_system.bat"
CANONICAL_SERVE = (
    "run",
    "--locked",
    "--no-sync",
    "python",
    "-m",
    "aura_backend.runtime",
    "serve",
)


def _executable_text(path: Path) -> str:
    """Return executable-looking lines while excluding comments."""
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith("rem "):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def _assert_non_mutating(path: Path) -> None:
    executable = _executable_text(path)
    without_required_flag = executable.replace("--no-sync", "--NO_SYNC")
    forbidden_patterns = (
        r"\b(?:install|sync|download|curl|wget|chmod)\b",
        r"\b(?:kill|pkill|taskkill|fuser|lsof)\b",
        r"\b(?:source|activate|pause|timeout|sleep)\b",
        r"\b(?:start|gnome-terminal|konsole|xterm|terminator)\b",
        r"(?:^|\s)(?:cmd\s+/k|npm\s+install|uv\s+venv)(?:\s|$)",
        r"0\.0\.0\.0|--reload|\.env(?:\s|$|\")",
    )
    for pattern in forbidden_patterns:
        assert re.search(pattern, without_required_flag, re.IGNORECASE) is None, (
            f"{path.name} contains forbidden startup behavior matching {pattern!r}"
        )


def _write_uv_spy(directory: Path, *, exit_code: int) -> Path:
    """Create a fake uv executable that records cwd/argv and returns a fixed code."""
    spy = directory / "uv"
    spy.write_text(
        "#!/bin/sh\n"
        ': "${AURA_SPY_OUTPUT:?missing AURA_SPY_OUTPUT}"\n'
        '{ printf "%s\\n" "$PWD"; printf "%s\\n" "$@"; } '
        '> "$AURA_SPY_OUTPUT"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    spy.chmod(0o755)
    return spy


@pytest.mark.parametrize("launcher", (ROOT_LINUX, ROOT_WINDOWS))
def test_root_launchers_are_static_non_mutating_delegates(launcher: Path) -> None:
    _assert_non_mutating(launcher)


def test_root_linux_delegates_exact_command_arguments_and_exit(
    tmp_path: Path,
) -> None:
    _assert_non_mutating(ROOT_LINUX)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_uv_spy(fake_bin, exit_code=23)
    output = tmp_path / "spy.txt"
    environment = {
        **os.environ,
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "AURA_SPY_OUTPUT": str(output),
    }

    completed = subprocess.run(
        ["/bin/sh", str(ROOT_LINUX), "--port", "8123"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )

    assert completed.returncode == 23
    assert output.read_text(encoding="utf-8").splitlines() == [
        str(REPOSITORY_ROOT),
        *CANONICAL_SERVE,
        "--port",
        "8123",
    ]


def test_root_linux_missing_uv_is_truthful_and_nonzero(tmp_path: Path) -> None:
    _assert_non_mutating(ROOT_LINUX)
    completed = subprocess.run(
        ["/bin/sh", str(ROOT_LINUX)],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )

    assert completed.returncode != 0
    assert "uv" in completed.stderr.lower()
    assert "https://docs.astral.sh/uv/" in completed.stderr


def test_root_windows_matches_canonical_delegate_and_exit_contract() -> None:
    _assert_non_mutating(ROOT_WINDOWS)
    executable = _executable_text(ROOT_WINDOWS).lower()

    assert (
        "uv run --locked --no-sync python -m aura_backend.runtime serve %*"
        in executable
    )
    assert "exit /b %errorlevel%" in executable
    assert 'cd /d "%~dp0"' in executable

