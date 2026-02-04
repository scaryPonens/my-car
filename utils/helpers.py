"""
Functional programming utilities for Smart Car VA.

Provides pure functions for composition, error handling, and data manipulation.
All functions are designed to be side-effect free and composable.
"""

import asyncio
import logging
import time
from functools import reduce, wraps
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Optional,
    TypeVar,
)

logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


def identity(x: T) -> T:
    """
    Identity function - returns its argument unchanged.

    Useful as a default function in compositions.

    Args:
        x: Any value.

    Returns:
        The same value unchanged.
    """
    return x


def pipe(*functions: Callable) -> Callable:
    """
    Compose functions left-to-right (pipe style).

    Creates a pipeline where each function's output becomes
    the next function's input.

    Args:
        *functions: Functions to compose.

    Returns:
        A new function that applies all functions in sequence.

    Example:
        >>> add_one = lambda x: x + 1
        >>> double = lambda x: x * 2
        >>> pipeline = pipe(add_one, double)
        >>> pipeline(5)  # (5 + 1) * 2 = 12
        12
    """
    def piped(initial: Any) -> Any:
        return reduce(lambda acc, fn: fn(acc), functions, initial)
    return piped


def compose(*functions: Callable) -> Callable:
    """
    Compose functions right-to-left (traditional composition).

    Creates a composition where the rightmost function is applied first.

    Args:
        *functions: Functions to compose.

    Returns:
        A new function that applies all functions in reverse sequence.

    Example:
        >>> add_one = lambda x: x + 1
        >>> double = lambda x: x * 2
        >>> composed = compose(add_one, double)
        >>> composed(5)  # (5 * 2) + 1 = 11
        11
    """
    return pipe(*reversed(functions))


class Maybe(Generic[T]):
    """
    Maybe monad for handling optional values.

    Provides a safe way to chain operations that might return None,
    without explicit null checks at each step.

    Example:
        >>> result = Maybe(user).map(lambda u: u.name).map(str.upper).get_or("Unknown")
    """

    def __init__(self, value: Optional[T]) -> None:
        """Initialize with an optional value."""
        self._value = value

    @property
    def is_nothing(self) -> bool:
        """Check if the Maybe contains Nothing (None)."""
        return self._value is None

    @property
    def is_just(self) -> bool:
        """Check if the Maybe contains Just (a value)."""
        return self._value is not None

    def map(self, fn: Callable[[T], U]) -> "Maybe[U]":
        """
        Apply a function to the value if present.

        Args:
            fn: Function to apply.

        Returns:
            A new Maybe with the transformed value, or Nothing.
        """
        if self._value is None:
            return Maybe(None)
        try:
            return Maybe(fn(self._value))
        except Exception:
            return Maybe(None)

    def flat_map(self, fn: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        """
        Apply a function that returns a Maybe.

        Args:
            fn: Function that returns a Maybe.

        Returns:
            The Maybe returned by fn, or Nothing.
        """
        if self._value is None:
            return Maybe(None)
        try:
            return fn(self._value)
        except Exception:
            return Maybe(None)

    def get_or(self, default: T) -> T:
        """
        Get the value or a default if Nothing.

        Args:
            default: Value to return if Nothing.

        Returns:
            The contained value or the default.
        """
        return self._value if self._value is not None else default

    def get_or_else(self, fn: Callable[[], T]) -> T:
        """
        Get the value or compute a default if Nothing.

        Args:
            fn: Function to compute default value.

        Returns:
            The contained value or the computed default.
        """
        return self._value if self._value is not None else fn()

    def filter(self, predicate: Callable[[T], bool]) -> "Maybe[T]":
        """
        Filter the value based on a predicate.

        Args:
            predicate: Function that returns True to keep the value.

        Returns:
            Self if predicate passes, Nothing otherwise.
        """
        if self._value is None:
            return self
        return self if predicate(self._value) else Maybe(None)

    def __repr__(self) -> str:
        """String representation."""
        if self._value is None:
            return "Nothing"
        return f"Just({self._value!r})"


def maybe(value: Optional[T]) -> Maybe[T]:
    """
    Create a Maybe from an optional value.

    Convenience function for creating Maybe instances.

    Args:
        value: An optional value.

    Returns:
        A Maybe wrapping the value.
    """
    return Maybe(value)


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.

    Args:
        data: The dictionary to traverse.
        *keys: Keys to follow in sequence.
        default: Value to return if any key is missing.

    Returns:
        The value at the nested path, or the default.

    Example:
        >>> data = {"user": {"profile": {"name": "Alice"}}}
        >>> safe_get(data, "user", "profile", "name")
        'Alice'
        >>> safe_get(data, "user", "settings", "theme", default="dark")
        'dark'
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def filter_dict(
    predicate: Callable[[str, Any], bool],
    d: dict[str, Any],
) -> dict[str, Any]:
    """
    Filter a dictionary by key-value pairs.

    Args:
        predicate: Function taking (key, value) returning bool.
        d: Dictionary to filter.

    Returns:
        A new dictionary with only matching pairs.

    Example:
        >>> filter_dict(lambda k, v: v is not None, {"a": 1, "b": None})
        {'a': 1}
    """
    return {k: v for k, v in d.items() if predicate(k, v)}


def map_dict(
    fn: Callable[[str, Any], tuple[str, Any]],
    d: dict[str, Any],
) -> dict[str, Any]:
    """
    Map over a dictionary's key-value pairs.

    Args:
        fn: Function taking (key, value) returning (new_key, new_value).
        d: Dictionary to map over.

    Returns:
        A new dictionary with transformed pairs.

    Example:
        >>> map_dict(lambda k, v: (k.upper(), v * 2), {"a": 1, "b": 2})
        {'A': 2, 'B': 4}
    """
    return dict(fn(k, v) for k, v in d.items())


def filter_none(d: dict[str, Any]) -> dict[str, Any]:
    """
    Remove None values from a dictionary.

    Args:
        d: Dictionary to filter.

    Returns:
        A new dictionary without None values.
    """
    return filter_dict(lambda k, v: v is not None, d)


def flatten(nested: Iterable[Iterable[T]]) -> list[T]:
    """
    Flatten a nested iterable one level deep.

    Args:
        nested: An iterable of iterables.

    Returns:
        A flat list containing all elements.

    Example:
        >>> flatten([[1, 2], [3, 4], [5]])
        [1, 2, 3, 4, 5]
    """
    return [item for sublist in nested for item in sublist]


def partition(
    predicate: Callable[[T], bool],
    items: Iterable[T],
) -> tuple[list[T], list[T]]:
    """
    Partition items into two lists based on a predicate.

    Args:
        predicate: Function that returns True for first group.
        items: Items to partition.

    Returns:
        Tuple of (matching, non_matching) lists.

    Example:
        >>> partition(lambda x: x % 2 == 0, [1, 2, 3, 4, 5])
        ([2, 4], [1, 3, 5])
    """
    matching: list[T] = []
    non_matching: list[T] = []
    for item in items:
        if predicate(item):
            matching.append(item)
        else:
            non_matching.append(item)
    return matching, non_matching


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries.
        exponential_base: Base for exponential backoff calculation.
        exceptions: Tuple of exception types to catch and retry.

    Returns:
        A decorator function.

    Example:
        >>> @retry_with_backoff(max_retries=3)
        ... def flaky_api_call():
        ...     # might fail sometimes
        ...     pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay,
                        )
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
            raise last_exception  # type: ignore

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay,
                        )
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
            raise last_exception  # type: ignore

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Simple memoization decorator for pure functions.

    Caches results based on arguments. Only works with
    hashable arguments.

    Args:
        func: A pure function to memoize.

    Returns:
        A memoized version of the function.

    Example:
        >>> @memoize
        ... def expensive_computation(n):
        ...     return sum(range(n))
    """
    cache: dict[tuple, Any] = {}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        # Create a hashable key from args and kwargs
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    # Attach cache for testing/debugging
    wrapper.cache = cache  # type: ignore
    wrapper.clear_cache = lambda: cache.clear()  # type: ignore

    return wrapper


def safe_api_call(
    func: Callable[..., T],
    default: T,
) -> Callable[..., T]:
    """
    Wrap a function to return a default on any exception.

    Args:
        func: Function to wrap.
        default: Default value to return on exception.

    Returns:
        A wrapped function that never raises.

    Example:
        >>> safe_divide = safe_api_call(lambda a, b: a / b, default=0)
        >>> safe_divide(10, 0)
        0
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"safe_api_call caught exception: {e}")
            return default

    return wrapper


def async_safe_api_call(
    func: Callable[..., T],
    default: T,
) -> Callable[..., T]:
    """
    Wrap an async function to return a default on any exception.

    Args:
        func: Async function to wrap.
        default: Default value to return on exception.

    Returns:
        A wrapped async function that never raises.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"async_safe_api_call caught exception: {e}")
            return default

    return wrapper


def partial_right(func: Callable, *args: Any, **kwargs: Any) -> Callable:
    """
    Partial application from the right side.

    Like functools.partial but applies arguments from the right.

    Args:
        func: Function to partially apply.
        *args: Arguments to apply from the right.
        **kwargs: Keyword arguments to apply.

    Returns:
        A partially applied function.

    Example:
        >>> def greet(greeting, name):
        ...     return f"{greeting}, {name}!"
        >>> say_hello = partial_right(greet, "Alice")
        >>> say_hello("Hello")
        'Hello, Alice!'
    """
    @wraps(func)
    def wrapper(*left_args: Any, **extra_kwargs: Any) -> Any:
        return func(*left_args, *args, **{**kwargs, **extra_kwargs})
    return wrapper


def tap(fn: Callable[[T], Any]) -> Callable[[T], T]:
    """
    Create a function that calls fn for side effects but returns input.

    Useful for inserting logging or debugging into pipelines.

    Args:
        fn: Function to call for side effects.

    Returns:
        A function that calls fn then returns its input unchanged.

    Example:
        >>> pipeline = pipe(
        ...     lambda x: x + 1,
        ...     tap(print),  # prints intermediate value
        ...     lambda x: x * 2,
        ... )
    """
    def tapped(value: T) -> T:
        fn(value)
        return value
    return tapped
