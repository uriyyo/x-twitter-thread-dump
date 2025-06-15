from collections.abc import AsyncIterator
from typing import Annotated, TypeAlias

from fastapi import Depends

from x_twitter_thread_dump._threads import ThreadsAsyncClient, threads_async_client
from x_twitter_thread_dump._threads.entities import ThreadPost


async def get_threads_async_client() -> AsyncIterator[ThreadsAsyncClient]:
    async with threads_async_client() as client:
        yield client


CurrentThreadsClient: TypeAlias = Annotated[
    ThreadsAsyncClient,
    Depends(get_threads_async_client),
]


async def current_thread(
    client: CurrentThreadsClient,
    post_id: str,
) -> list[ThreadPost]:
    return await client.get_thread(post_id)


CurrentThread: TypeAlias = Annotated[
    list[ThreadPost],
    Depends(current_thread),
]


async def current_thread_with_previews(
    client: CurrentThreadsClient,
    thread: CurrentThread,
) -> list[ThreadPost]:
    await client.download_previews(thread)
    return thread


CurrentThreadWithPreviews: TypeAlias = Annotated[
    list[ThreadPost],
    Depends(current_thread_with_previews),
]

__all__ = [
    "CurrentThread",
    "CurrentThreadWithPreviews",
    "CurrentThreadsClient",
    "current_thread",
    "current_thread_with_previews",
    "get_threads_async_client",
]
