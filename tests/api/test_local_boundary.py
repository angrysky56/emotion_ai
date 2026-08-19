"""Request-level characterization of Aura's private localhost boundary."""

from __future__ import annotations

import pytest

from tests.support.main_subprocess_probe import ProbeFailure, run_probe


def test_probe_imports_real_app_without_starting_production_services() -> None:
    """The child uses the production ASGI app but never enters its lifespan."""
    result = run_probe("probe", timeout=10.0)

    assert result["app_module"] == "aura_backend.main"
    assert result["lifespan_started"] is False
    assert result["production_initializers_called"] == []
    assert result["repository_data_roots_unchanged"] is True


def test_probe_timeout_is_a_distinct_failure() -> None:
    """A wedged child can never be mistaken for a passing characterization."""
    with pytest.raises(ProbeFailure, match="timed out"):
        run_probe("_hang", timeout=0.1)


@pytest.mark.parametrize(
    ("scenario", "diagnostic"),
    (
        ("_crash", "exited with status"),
        ("_malformed", "invalid JSON"),
        ("_partial", "incomplete result"),
    ),
)
def test_probe_rejects_failed_or_incomplete_children(
    scenario: str, diagnostic: str
) -> None:
    """Exit status and the full JSON result contract are mandatory evidence."""
    with pytest.raises(ProbeFailure, match=diagnostic):
        run_probe(scenario, timeout=2.0)
