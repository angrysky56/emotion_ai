"""
JSON Serialization Fix for NumPy Types
======================================

This module provides utilities to handle JSON serialization of NumPy types
that commonly cause "Object of type int64 is not JSON serializable" errors.

Compatible with both NumPy 1.x and 2.x versions.
"""

import numpy as np
import json
from typing import Any
import logging

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NumPy types"""

    def default(self, o: Any) -> Any:
        if isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, np.bool_):
            return bool(o)
        elif isinstance(o, np.complexfloating):
            # Handle complex numbers (works with both NumPy 1.x and 2.x)
            return {'real': float(o.real), 'imag': float(o.imag)}
        return super().default(o)


def convert_numpy_to_python(obj: Any) -> Any:
    """
    Recursively convert NumPy types to native Python types.

    This handles nested structures like dicts and lists that might contain
    NumPy types at any level.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_to_python(obj.tolist())
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.complexfloating):
        # Handle complex numbers (works with both NumPy 1.x and 2.x)
        return {'real': float(obj.real), 'imag': float(obj.imag)}
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_python(item) for item in obj)
    else:
        return obj


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely serialize an object to JSON, handling NumPy types.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps

    Returns:
        JSON string
    """
    # First try to convert NumPy types
    converted_obj = convert_numpy_to_python(obj)

    # Then use our custom encoder as a fallback
    if 'cls' not in kwargs:
        kwargs['cls'] = NumpyEncoder

    return json.dumps(converted_obj, **kwargs)


def ensure_json_serializable(data: Any) -> Any:
    """
    Ensure data is JSON serializable by converting all NumPy types.

    This is useful before passing data to APIs or storing in databases.
    """
    try:
        # Test if it's already serializable
        json.dumps(data)
        return data
    except (TypeError, ValueError) as e:
        # If not, convert NumPy types
        logger.debug("Converting non-serializable data: %s", e)
        return convert_numpy_to_python(data)


def clean_tool_result(result: Any) -> Any:
    """
    Clean tool execution results to ensure they're JSON serializable.

    This is specifically for MCP tool results that might contain NumPy types.
    """
    if isinstance(result, dict):
        # Special handling for common result patterns
        cleaned = {}
        for key, value in result.items():
            if key in ['embeddings', 'vectors', 'features'] and isinstance(value, (list, np.ndarray)):
                # These are often large arrays, convert them efficiently
                if isinstance(value, np.ndarray):
                    cleaned[key] = value.tolist()
                else:
                    cleaned[key] = convert_numpy_to_python(value)
            else:
                cleaned[key] = convert_numpy_to_python(value)
        return cleaned
    else:
        return convert_numpy_to_python(result)


# Monkey patch json.dumps to always handle NumPy types
_original_json_dumps = json.dumps

def patched_json_dumps(obj, **kwargs):
    """Patched version of json.dumps that handles NumPy types"""
    try:
        return _original_json_dumps(obj, **kwargs)
    except (TypeError, ValueError) as e:
        if "not JSON serializable" in str(e):
            # Convert and retry
            converted_obj = convert_numpy_to_python(obj)
            return _original_json_dumps(converted_obj, **kwargs)
        raise

# Note: Uncomment the line below to globally patch json.dumps
# json.dumps = patched_json_dumps
