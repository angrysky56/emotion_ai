"""Characterize Aura's route-to-persistence contract with synthetic data only."""

from __future__ import annotations

from tests.support.main_subprocess_probe import run_probe


def test_conversation_passes_one_normalized_exchange_to_immediate_persistence() -> None:
    """The real route supplies the expected exchange shape and persistence options."""
    result = run_probe("persistence_success")

    assert result["status_code"] == 200
    assert result["persistence"] == {
        "background_calls": 0,
        "exchange": {
            "aura_message_nonempty": True,
            "aura_sender": "aura",
            "aura_user_matches": True,
            "session_ids": ["<session>", "<session>", "<session>"],
            "user_message_matches": True,
            "user_sender": "user",
            "user_user_matches": True,
        },
        "immediate_calls": 1,
        "method": "persist_conversation_exchange_immediate",
        "result": {
            "error_count": 0,
            "method": "fake_immediate",
            "stored_component_count": 1,
            "success": True,
        },
        "timeout": 4.25,
        "update_profile": True,
    }
    assert result["filesystem_write_attempts"] == 0
    assert result["repository_data_roots_unchanged"] is True


def test_persistence_failure_is_visible_as_degraded_storage_not_route_failure() -> None:
    """A structured write failure retains today's response and bounded retry behavior."""
    result = run_probe("persistence_failure")

    assert result["status_code"] == 200
    assert result["visible_provider_answer_preserved"] is True
    assert result["persistence"]["immediate_calls"] == 1
    assert result["persistence"]["background_calls"] == 1
    assert result["persistence"]["result"] == {
        "error_count": 1,
        "method": "fake_immediate_failure",
        "stored_component_count": 0,
        "success": False,
    }
    assert result["filesystem_write_attempts"] == 0
    assert result["repository_data_roots_unchanged"] is True
