import asyncio
import math
import re
from collections.abc import AsyncIterable, Callable, Coroutine, Iterable
from functools import wraps
from typing import Any, cast
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from httpx import Response


def response_to_bs4(response: Response, /) -> BeautifulSoup:
    return BeautifulSoup(response.content, "html.parser")


def parse_guest_token(response: Response, /) -> str:
    response.raise_for_status()

    match response.json():
        case {"guest_token": str() as guest_token}:
            return guest_token
        case _:
            raise ValueError("Invalid response format for guest token extraction.")


def limited[T](
    it: Iterable[T],
    /,
    *,
    limit: int | None = None,
) -> Iterable[T]:
    if limit is None:
        yield from it
        return

    for i, _ in zip(it, range(limit), strict=False):
        yield i


async def alimited[T](
    ait: AsyncIterable[T],
    /,
    *,
    limit: int | None = None,
) -> AsyncIterable[T]:
    if limit is None:
        limit = cast(int, math.inf)

    count = 0
    async for i in ait:
        if count >= limit:
            break

        yield i
        count += 1


TWEET_ID_PATH_REGEX = re.compile(r"^/[a-zA-Z0-9_]+/status/(\d+)/?$")


def get_tweet_id_from_url(url: str) -> str:
    parsed = urlparse(url, scheme="https")

    if parsed.netloc not in {"x.com", "twitter.com", "www.x.com", "www.twitter.com"}:
        raise ValueError(f"Invalid Twitter URL: {url}")

    if match := TWEET_ID_PATH_REGEX.match(parsed.path):
        return match.group(1)

    raise ValueError(f"Invalid Twitter URL: {url} (no tweet ID found)")


def async_to_sync[**P, R](func: Callable[P, Coroutine[Any, Any, R]], /) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return asyncio.run(func(*args, **kwargs))

    return cast(Callable[P, R], wrapper)


__all__ = [
    "alimited",
    "get_tweet_id_from_url",
    "limited",
    "parse_guest_token",
    "response_to_bs4",
    "async_to_sync",
]
