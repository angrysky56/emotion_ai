"""Request-level characterization of Aura's private localhost boundary."""

from __future__ import annotations

import pytest

from aura_backend.runtime_security import server_host
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


def test_server_host_is_loopback_by_default_and_lan_is_explicit() -> None:
    """Aura is private by default while preserving an explicit LAN opt-in."""
    assert server_host(None) == "127.0.0.1"
    assert server_host(" 192.168.1.25 ") == "192.168.1.25"


def test_configured_local_origin_preflight_is_allowed_without_credentials() -> None:
    """The bundled browser may preflight JSON without enabling cookies."""
    result = run_probe("preflight_allowed")

    assert result["status_code"] == 200
    assert result["headers"]["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert "access-control-allow-credentials" not in result["headers"]
    assert result["lifespan_started"] is False


def test_untrusted_origin_preflight_is_denied() -> None:
    """An unrelated website receives no permission to call localhost Aura."""
    result = run_probe("preflight_denied")

    assert result["status_code"] == 400
    assert "access-control-allow-origin" not in result["headers"]
    assert result["provider_calls"] == 0
    assert result["persistence_calls"] == 0
    assert result["lifespan_started"] is False


def test_wildcard_origin_configuration_is_rejected_before_app_creation() -> None:
    """Aura cannot be configured to trust every website."""
    result = run_probe("wildcard_origin")

    assert result["wildcard_rejected"] is True
    assert "wildcard" in result["error"]
    assert result["production_initializers_called"] == []


@pytest.mark.parametrize(
    "scenario",
    ("conversation_missing_content_type", "conversation_text_plain"),
)
def test_non_json_conversation_is_rejected_before_business_behavior(
    scenario: str,
) -> None:
    """Simple cross-origin requests cannot drive the local companion route."""
    result = run_probe(scenario)

    assert result["status_code"] == 422
    assert result["body"]["detail"][0]["loc"] == ["body"]
    assert result["body"]["detail"][0]["type"] == "model_attributes_type"
    assert "access-control-allow-origin" not in result["headers"]
    assert result["provider_calls"] == 0
    assert result["persistence_calls"] == 0
    assert result["lifespan_started"] is False


def test_allowed_local_json_conversation_succeeds_without_sign_in() -> None:
    """The normal single-user flow needs no account, cookie, token, or session auth."""
    result = run_probe("conversation_json")

    assert result["status_code"] == 200
    assert result["headers"]["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert "access-control-allow-credentials" not in result["headers"]
    assert result["provider_calls"] == 1
    assert result["persistence_calls"] == 1
    assert result["credential_headers_sent"] == []
    assert result["lifespan_started"] is False
    assert result["body"] == {
        "cognitive_state": {
            "description": "Synthetic local processing",
            "focus": "Learning",
        },
        "emotional_state": {
            "brainwave": "Alpha",
            "intensity": "Medium",
            "name": "Calm",
            "neurotransmitter": "Serotonin",
        },
        "has_thinking": False,
        "response": "Synthetic local reply.",
        "session_id": "probe-session",
        "thinking_content": None,
        "thinking_metrics": None,
    }
