"""Shared decorators for routes or services."""

from functools import wraps
from typing import Callable


def noop_decorator(func: Callable):
    """Placeholder decorator for future cross-cutting concerns."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
