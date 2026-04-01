"""Performance helpers for cached responses and payload trimming."""
from __future__ import annotations

import inspect
import os
from functools import lru_cache, wraps
from typing import Any, Callable

from backend.services.loaders import DATA_DIR

MAX_TABLE_ROWS = 120


def _freeze_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple, set)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze_value(val)) for key, val in value.items()))
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def data_version(*filenames: str) -> tuple[tuple[str, float], ...]:
    return tuple(
        (filename, os.path.getmtime(os.path.join(DATA_DIR, filename))) for filename in filenames
    )


def cache_response(*filenames: str, maxsize: int = 128) -> Callable:
    """Cache pure response builders using the source CSV mtimes as version key."""

    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)

        @lru_cache(maxsize=maxsize)
        def _cached(version_key: tuple[tuple[str, float], ...], frozen_args: tuple[tuple[str, Any], ...]):
            return func(**dict(frozen_args))

        @wraps(func)
        def wrapper(*args, **kwargs):
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            frozen_args = tuple(
                sorted((key, _freeze_value(value)) for key, value in bound.arguments.items())
            )
            return _cached(data_version(*filenames), frozen_args)

        wrapper.cache_clear = _cached.cache_clear  # type: ignore[attr-defined]
        wrapper.cache_info = _cached.cache_info  # type: ignore[attr-defined]
        return wrapper

    return decorator


def limit_records(records: list[dict], max_rows: int = MAX_TABLE_ROWS) -> list[dict]:
    if max_rows <= 0 or len(records) <= max_rows:
        return records
    return records[:max_rows]
