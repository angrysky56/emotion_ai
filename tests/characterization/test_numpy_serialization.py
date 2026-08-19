"""Characterize Aura's pure NumPy-to-JSON conversion helpers."""

import json
from typing import Any

import numpy as np
import pytest

from aura_backend.scripts.json_serialization_fix import (
    clean_tool_result,
    convert_numpy_to_python,
    safe_json_dumps,
)


@pytest.mark.parametrize(
    ("value", "expected", "expected_type"),
    [
        pytest.param(np.int64(42), 42, int, id="integer"),
        pytest.param(np.float32(1.25), 1.25, float, id="floating"),
        pytest.param(np.bool_(True), True, bool, id="boolean"),
        pytest.param(
            np.complex64(1 + 2j),
            {"real": 1.0, "imag": 2.0},
            dict,
            id="complex",
        ),
    ],
)
def test_numpy_scalars_convert_to_native_values(
    value: Any,
    expected: Any,
    expected_type: type[Any],
) -> None:
    converted = convert_numpy_to_python(value)

    assert converted == expected
    assert type(converted) is expected_type


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            np.array([[1, 2], [3, 4]], dtype=np.int32),
            [[1, 2], [3, 4]],
            id="array",
        ),
        pytest.param(
            {
                "count": np.int64(2),
                "scores": [np.float32(0.5), np.float64(0.75)],
            },
            {"count": 2, "scores": [0.5, 0.75]},
            id="nested-dict-and-list",
        ),
        pytest.param(
            (np.int32(7), {"available": np.bool_(False)}),
            (7, {"available": False}),
            id="tuple",
        ),
    ],
)
def test_arrays_and_nested_containers_convert_recursively(
    value: Any,
    expected: Any,
) -> None:
    converted = convert_numpy_to_python(value)

    assert converted == expected
    json.dumps(converted)


def test_safe_json_dumps_emits_parseable_native_values() -> None:
    value = {
        "count": np.int64(3),
        "scores": np.array([0.25, 0.5], dtype=np.float32),
        "phase": np.complex128(2 + 4j),
    }

    serialized = safe_json_dumps(value, sort_keys=True)

    assert json.loads(serialized) == {
        "count": 3,
        "phase": {"imag": 4.0, "real": 2.0},
        "scores": [0.25, 0.5],
    }


def test_clean_tool_result_preserves_ordinary_values_and_converts_arrays() -> None:
    result = {
        "status": "success",
        "count": 2,
        "embeddings": np.array([[0.1, 0.2], [0.3, 0.4]]),
        "metadata": {
            "source": "synthetic",
            "features": [np.int32(1), np.int32(2)],
        },
    }

    cleaned = clean_tool_result(result)

    assert cleaned["status"] == "success"
    assert cleaned["count"] == 2
    assert cleaned["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]
    assert cleaned["metadata"] == {
        "source": "synthetic",
        "features": [1, 2],
    }
    assert json.loads(json.dumps(cleaned)) == cleaned
