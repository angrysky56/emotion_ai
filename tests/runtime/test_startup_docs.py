"""Static drift checks for Aura's supported startup documentation.

These tests read checked-in examples only. They do not read ``.env``, start Aura,
contact a provider, install dependencies, or mutate the project environment.
"""

from __future__ import annotations

import re
from pathlib import Path

from aura_backend.providers.config import ProviderKind
from aura_backend.runtime.config import RuntimeSettings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
README = REPOSITORY_ROOT / "README.md"
STARTUP_GUIDE = REPOSITORY_ROOT / "aura_backend" / "STARTUP_GUIDE.md"
ENV_EXAMPLE = REPOSITORY_ROOT / ".env.example"
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


def _example_assignments(*, include_commented: bool) -> list[tuple[str, str]]:
    """Parse simple example assignments without loading dotenv or ambient state."""
    assignments: list[tuple[str, str]] = []
    for raw_line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        commented = line.startswith("#")
        if commented:
            line = line[1:].strip()
        if "=" not in line or (commented and not include_commented):
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            assignments.append((key, value.strip()))
    return assignments


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


def test_env_example_has_no_duplicate_keys_or_active_cloud_credentials() -> None:
    assignments = _example_assignments(include_commented=True)
    keys = [key for key, _value in assignments]
    assert len(keys) == len(set(keys))

    active = dict(_example_assignments(include_commented=False))
    assert "GEMINI_API_KEY" not in active
    assert "OPENROUTER_API_KEY" not in active
    assert "OPENAI_API_KEY" not in active


def test_env_example_is_parsed_as_local_ollama_on_loopback() -> None:
    active = dict(_example_assignments(include_commented=False))
    settings = RuntimeSettings.from_mapping(active)

    assert settings.host == "127.0.0.1"
    assert settings.provider.kind is ProviderKind.OLLAMA
    assert settings.provider.model == "llama3.1"
    assert settings.provider.api_key is None
    assert settings.provider.base_url == "http://127.0.0.1:11434/v1"


def test_env_example_contains_only_obvious_non_secret_key_sentinels() -> None:
    assignments = dict(_example_assignments(include_commented=True))
    secret_keys = ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")
    for key in secret_keys:
        assert assignments[key] == "<set-in-private-environment>"

    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert re.search(r"AIza[0-9A-Za-z_-]{20,}", text) is None
    assert re.search(r"sk-(?:or-v1-)?[0-9A-Za-z_-]{16,}", text) is None


def test_ornith_is_not_the_normal_example_provider_model() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    active = dict(_example_assignments(include_commented=False))

    assert active["OLLAMA_MODEL"] == "llama3.1"
    assert "ornith:latest" not in text
