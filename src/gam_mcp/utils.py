"""Utility functions for GAM MCP Server."""

from typing import Any, Optional


def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get an attribute from a zeep object or dict.

    Args:
        obj: The object to get the attribute from (zeep object or dict)
        key: The attribute/key name
        default: Default value if not found

    Returns:
        The attribute value or default
    """
    if obj is None:
        return default

    # Try dict-style access first (for plain dicts)
    if isinstance(obj, dict):
        return obj.get(key, default)

    # Try attribute access (for zeep objects)
    try:
        value = getattr(obj, key, None)
        if value is None:
            return default
        return value
    except (AttributeError, KeyError):
        pass

    # Try bracket access (zeep objects support this too)
    try:
        value = obj[key]
        if value is None:
            return default
        return value
    except (KeyError, TypeError, IndexError):
        pass

    return default


def extract_date(datetime_obj: Any) -> Optional[str]:
    """Extract date string from a GAM datetime object.

    Args:
        datetime_obj: A GAM datetime object with date property

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if datetime_obj is None:
        return None

    date_obj = safe_get(datetime_obj, 'date')
    if date_obj is None:
        return None

    year = safe_get(date_obj, 'year')
    month = safe_get(date_obj, 'month', 1)
    day = safe_get(date_obj, 'day', 1)

    if year is None:
        return None

    return f"{year}-{month:02d}-{day:02d}"


def zeep_to_dict(obj: Any) -> Any:
    """Convert a zeep object to a regular Python dict recursively.

    Args:
        obj: A zeep object or any value

    Returns:
        A regular Python dict or the original value
    """
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, (list, tuple)):
        return [zeep_to_dict(item) for item in obj]

    if isinstance(obj, dict):
        return {k: zeep_to_dict(v) for k, v in obj.items()}

    # Try to convert zeep object to dict
    try:
        # Zeep objects have __values__ attribute
        if hasattr(obj, '__values__'):
            return {k: zeep_to_dict(v) for k, v in obj.__values__.items()}
    except Exception:
        pass

    # Fallback: try to get dict representation
    try:
        return dict(obj)
    except (TypeError, ValueError):
        pass

    return str(obj)
