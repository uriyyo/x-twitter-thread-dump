from collections.abc import AsyncIterator
from typing import Annotated, TypeAlias

from fastapi import Depends, Query

from x_twitter_thread_dump._api.schemas import TikTokShareURL
from x_twitter_thread_dump._tiktok import TikTokAsyncClient, tiktok_async_client
from x_twitter_thread_dump._tiktok.entities import TikTokComment


async def get_tiktok_async_client() -> AsyncIterator[TikTokAsyncClient]:
    async with tiktok_async_client() as client:
        yield client


CurrentTikTokClient: TypeAlias = Annotated[
    TikTokAsyncClient,
    Depends(get_tiktok_async_client),
]


async def current_comments(
    client: CurrentTikTokClient,
    url: Annotated[TikTokShareURL, Query()],
) -> list[TikTokComment]:
    comment, parent = await client.resolve_comment(url)
    return [parent, comment] if parent else [comment]


CurrentComments: TypeAlias = Annotated[
    list[TikTokComment],
    Depends(current_comments),
]


async def current_comments_with_previews(
    client: CurrentTikTokClient,
    comments: CurrentComments,
) -> list[TikTokComment]:
    await client.download_previews(comments)
    return comments


CurrentCommentsWithPreviews: TypeAlias = Annotated[
    list[TikTokComment],
    Depends(current_comments_with_previews),
]

__all__ = [
    "CurrentComments",
    "CurrentCommentsWithPreviews",
    "CurrentTikTokClient",
    "current_comments",
    "current_comments_with_previews",
    "get_tiktok_async_client",
]
