import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import cache, wraps


def limit_concurrency[**P, R](limit: int) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @cache
        def _get_semaphore() -> asyncio.Semaphore:
            return asyncio.Semaphore(limit)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            async with _get_semaphore():
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def retry[**P, R](
    *,
    retries: int = 3,
    delay: float = 0,
    excs: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for _ in range(max(retries - 1, 0)):
                with suppress(*excs):
                    return await func(*args, **kwargs)

                await asyncio.sleep(delay)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "limit_concurrency",
    "retry",
]
