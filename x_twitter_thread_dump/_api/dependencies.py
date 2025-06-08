from collections.abc import AsyncIterator
from typing import Annotated, TypeAlias, cast

from fastapi import Depends, Query, Request

from x_twitter_thread_dump import (
    Thread,
    XTwitterThreadDumpAsyncClient,
    x_twitter_thread_dump_async_client,
)

from .schemas import TweetID
from .sharable_brower_ctx import SharableBrowserCtx


async def get_current_browser_ctx(
    request: Request,
) -> SharableBrowserCtx:
    return cast(SharableBrowserCtx, request.state.browser_ctx)


CurrentSharableBrowserCtx: TypeAlias = Annotated[
    SharableBrowserCtx,
    Depends(get_current_browser_ctx),
]


async def get_x_twitter_thread_dump_async_client() -> AsyncIterator[XTwitterThreadDumpAsyncClient]:
    async with x_twitter_thread_dump_async_client() as client:
        yield client


ThreadClient: TypeAlias = Annotated[
    XTwitterThreadDumpAsyncClient,
    Depends(get_x_twitter_thread_dump_async_client),
]


async def current_thread(
    client: ThreadClient,
    tweet_id: TweetID,
    *,
    limit: Annotated[int, Query(ge=1, le=40)] = 20,
) -> Thread:
    return await client.get_thread(tweet_id, limit=limit)


CurrentThread: TypeAlias = Annotated[
    Thread,
    Depends(current_thread),
]


async def current_thread_with_previews(
    client: ThreadClient,
    thread: CurrentThread,
) -> Thread:
    await client.download_previews(thread)
    return thread


CurrentThreadWithPreviews: TypeAlias = Annotated[
    Thread,
    Depends(current_thread_with_previews),
]

__all__ = [
    "CurrentSharableBrowserCtx",
    "CurrentThread",
    "CurrentThreadWithPreviews",
    "ThreadClient",
]
