"""Static drift checks for Aura's supported startup documentation.

These tests read checked-in examples only. They do not read ``.env``, start Aura,
contact a provider, install dependencies, or mutate the project environment.
"""

from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
README = REPOSITORY_ROOT / "README.md"
STARTUP_GUIDE = REPOSITORY_ROOT / "aura_backend" / "STARTUP_GUIDE.md"
STARTUP_START = "<!-- aura-startup:start -->"
STARTUP_END = "<!-- aura-startup:end -->"
CANONICAL_RUNTIME_COMMANDS = (
    "uv run --locked --no-sync python -m aura_backend.runtime preflight",
    "uv run --locked --no-sync python -m aura_backend.runtime serve",
)
CANONICAL_SETUP_COMMANDS = ("uv sync --locked", "npm ci")


def _startup_section(path: Path) -> str:
    """Return the one explicitly supported startup section from a guide."""
    text = path.read_text(encoding="utf-8")
    assert text.count(STARTUP_START) == 1
    assert text.count(STARTUP_END) == 1
    return text.split(STARTUP_START, 1)[1].split(STARTUP_END, 1)[0]


def _marked_commands(section: str, marker: str) -> tuple[str, ...]:
    """Extract single-line commands that are intentionally drift-gated."""
    pattern = rf"<!-- {re.escape(marker)} -->\s*```(?:bash|powershell)\s*([^\n]+)\s*```"
    return tuple(re.findall(pattern, section))


def test_supported_guides_name_the_exact_runtime_contract() -> None:
    for path in (README, STARTUP_GUIDE):
        section = _startup_section(path)
        assert _marked_commands(section, "aura-runtime-command") == (
            CANONICAL_RUNTIME_COMMANDS
        )
        assert _marked_commands(section, "aura-setup-command") == (
            CANONICAL_SETUP_COMMANDS
        )


def test_supported_startup_sections_reject_legacy_or_mutating_instructions() -> None:
    forbidden = (
        r"python\s+main\.py",
        r"pip\s+install",
        r"npm\s+install",
        r"uv\s+venv",
        r"uv\s+sync(?!\s+--locked)",
        r"fuser\s+-k|pkill|taskkill|kill-port",
        r"--reload|0\.0\.0\.0",
        r"start_complete\.sh|start_mcp_background\.sh",
        r"automatic(?:ally)?\s+(?:install|download)",
        r"(?:uses?|falls?\s+back\s+to)\s+(?:a\s+)?cloud\s+provider",
    )
    for path in (README, STARTUP_GUIDE):
        section = _startup_section(path)
        for pattern in forbidden:
            assert re.search(pattern, section, re.IGNORECASE) is None, (
                f"{path} contains unsupported startup claim {pattern!r}"
            )


def test_supported_guides_state_runtime_truth_boundaries() -> None:
    required_terms = (
        "127.0.0.1",
        "no sign-in",
        "explicit LAN",
        "selected model",
        "pass",
        "missing",
        "failed",
        "blocked",
        "not_run",
        "not_applicable",
        "live provider check",
        "remote compute or billing",
    )
    for path in (README, STARTUP_GUIDE):
        section = re.sub(r"\s+", " ", _startup_section(path).lower())
        for term in required_terms:
            assert term.lower() in section, f"{path} is missing {term!r}"


def test_supported_guides_describe_wrappers_as_delegates() -> None:
    expected_wrappers = (
        "./start_full_system.sh",
        "start_full_system.bat",
        "./aura_backend/start_api.sh",
        "./aura_backend/start_frontend.sh",
        "./aura_backend/start_mcp.sh",
    )
    for path in (README, STARTUP_GUIDE):
        section = _startup_section(path)
        assert "delegate" in section.lower()
        for wrapper in expected_wrappers:
            assert wrapper in section
