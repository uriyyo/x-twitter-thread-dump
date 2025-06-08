from collections.abc import AsyncIterator
from typing import Annotated, Literal, TypeAlias, cast

from fastapi import Depends, Query, Request

from x_twitter_thread_dump import (
    Thread,
    XTwitterThreadDumpAsyncClient,
    x_twitter_thread_dump_async_client,
)
from x_twitter_thread_dump.types import BrowserCtxConfig, Viewport

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


CurrentThreadClient: TypeAlias = Annotated[
    XTwitterThreadDumpAsyncClient,
    Depends(get_x_twitter_thread_dump_async_client),
]


async def current_thread(
    client: CurrentThreadClient,
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
    client: CurrentThreadClient,
    thread: CurrentThread,
) -> Thread:
    await client.download_previews(thread)
    return thread


CurrentThreadWithPreviews: TypeAlias = Annotated[
    Thread,
    Depends(current_thread_with_previews),
]


async def get_browser_ctx_config(  # noqa: PLR0913
    is_mobile: Annotated[bool | None, Query()] = None,
    viewport_height: Annotated[int | None, Query(ge=1, le=2_000)] = None,
    viewport_width: Annotated[int | None, Query(ge=1, le=2_000)] = None,
    screen_height: Annotated[int | None, Query(ge=1, le=2_000)] = None,
    screen_width: Annotated[int | None, Query(ge=1, le=2_000)] = None,
    device_scale_factor: Annotated[float | None, Query(ge=0.1, le=5.0)] = None,
    color_scheme: Annotated[Literal["dark", "light", "no-preference", "null"] | None, Query()] = None,
    contrast: Annotated[Literal["more", "no-preference", "null"] | None, Query()] = None,
    forced_colors: Annotated[Literal["active", "none", "null"] | None, Query()] = None,
    locale: Annotated[str | None, Query()] = None,
    timezone_id: Annotated[str | None, Query()] = None,
) -> BrowserCtxConfig:
    config = BrowserCtxConfig()

    if is_mobile is not None:
        config["is_mobile"] = is_mobile
    if viewport_height is not None and viewport_width is not None:
        config["viewport"] = Viewport(width=viewport_width, height=viewport_height)
    if screen_height is not None and screen_width is not None:
        config["screen"] = Viewport(width=screen_width, height=screen_height)
    if device_scale_factor is not None:
        config["device_scale_factor"] = device_scale_factor
    if color_scheme is not None:
        config["color_scheme"] = color_scheme
    if contrast is not None:
        config["contrast"] = contrast
    if forced_colors is not None:
        config["forced_colors"] = forced_colors
    if locale is not None:
        config["locale"] = locale
    if timezone_id is not None:
        config["timezone_id"] = timezone_id

    return config


CurrentBrowserCtxConfig: TypeAlias = Annotated[
    BrowserCtxConfig,
    Depends(get_browser_ctx_config),
]

__all__ = [
    "CurrentBrowserCtxConfig",
    "CurrentSharableBrowserCtx",
    "CurrentThread",
    "CurrentThreadClient",
    "CurrentThreadWithPreviews",
]
