"""Characterize Aura's user-visible companion contract without a live model."""

from __future__ import annotations

import pytest

from tests.support.main_subprocess_probe import run_probe


EXPECTED_RESPONSE_KEYS = {
    "cognitive_state",
    "emotional_state",
    "has_thinking",
    "response",
    "session_id",
    "thinking_content",
    "thinking_metrics",
}


def test_fake_provider_conversation_preserves_stable_visible_response_shape() -> None:
    """The real route returns useful typed fields without freezing model prose."""
    result = run_probe("companion_success")

    assert result["status_code"] == 200
    assert set(result["response_schema"]) == EXPECTED_RESPONSE_KEYS
    assert result["response_schema"] == {
        "cognitive_state": "dict",
        "emotional_state": "dict",
        "has_thinking": "bool",
        "response": "str",
        "session_id": "str",
        "thinking_content": "none",
        "thinking_metrics": "none",
    }
    assert result["visible_answer_nonempty"] is True
    assert result["normalized_fields"] == {
        "cognitive_description": "Synthetic local processing",
        "cognitive_focus": "Learning",
        "emotion_intensity": "Medium",
        "emotion_name": "Calm",
        "session_id": "<session>",
    }
    assert result["provider_input"] == {
        "message_count": 1,
        "system_instruction_nonempty": True,
        "user_message_present": True,
    }
    assert result["hidden_reasoning_present"] is False
    assert result["repository_data_roots_unchanged"] is True


@pytest.mark.parametrize("scenario", ("provider_error", "provider_empty"))
def test_provider_failure_currently_degrades_to_an_http_200_fallback(
    scenario: str,
) -> None:
    """Pin the legacy fallback honestly instead of inventing a non-2xx response."""
    result = run_probe(scenario)

    assert result["status_code"] == 200
    assert result["returned_fallback_response"] is True
    assert result["visible_answer_nonempty"] is True
    assert result["provider_error_exposed"] is False
    assert result["provider_calls"] == 1
    assert result["provider_clear_session_calls"] == 1
    assert result["persistence_calls"] == 0
    assert result["hidden_reasoning_present"] is False
    assert set(result["response_schema"]) == EXPECTED_RESPONSE_KEYS
    assert result["repository_data_roots_unchanged"] is True
