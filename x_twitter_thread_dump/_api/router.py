from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, Response

from x_twitter_thread_dump import Tweet
from x_twitter_thread_dump.browser import HTMLToImageResult, html_to_image_async
from x_twitter_thread_dump.images import image_to_base64str, image_to_bytes
from x_twitter_thread_dump.render import render_thread_html
from x_twitter_thread_dump.types import BrowserCtxConfig

from .dependencies import (
    CurrentBrowserCtxConfig,
    CurrentSharableBrowserCtx,
    CurrentThread,
    CurrentThreadClient,
    CurrentThreadWithPreviews,
)
from .schemas import Base64ImageSchema, MediaSchema, TweetImagesSchema, TweetSchema
from .settings import settings
from .utils import limit_concurrency

router = APIRouter()


@router.get(
    "/json/{tweet_id}",
    response_model=list[TweetSchema],
)
async def get_tweet_json(
    thread: CurrentThread,
) -> list[Tweet]:
    return thread


@router.get("/raw-json/{tweet_id}")
async def get_tweet_raw_json(
    thread: CurrentThread,
) -> list[dict[str, Any] | None]:
    return [tweet.raw_data for tweet in thread]


@router.get("/html/{tweet_id}")
async def get_tweet_html(
    thread: CurrentThreadWithPreviews,
    *,
    show_connector_on_last: Annotated[bool, Query()] = False,
    is_single_tweet: Annotated[bool, Query()] = False,
) -> HTMLResponse:
    html = render_thread_html(
        thread,
        show_connector_on_last=show_connector_on_last,
        is_single_tweet=is_single_tweet,
    )

    return HTMLResponse(content=html)


@limit_concurrency(settings.IMAGE_RENDERING_CONCURRENCY)
async def render_html(
    browser_ctx: CurrentSharableBrowserCtx,
    chunk: str,
    config: BrowserCtxConfig | None = None,
) -> HTMLToImageResult:
    async with browser_ctx.acquire() as browser:
        return await html_to_image_async(
            chunk,
            browser=browser,
            config=config,
        )


@router.get("/imgs/{tweet_id}")
async def get_tweet_imgs(  # noqa: PLR0913
    thread: CurrentThreadWithPreviews,
    client: CurrentThreadClient,
    browser_ctx: CurrentSharableBrowserCtx,
    config: CurrentBrowserCtxConfig,
    *,
    include_media: Annotated[bool, Query()] = False,
    tweets_per_image: Annotated[int | None, Query(ge=1, le=10)] = None,
    max_tweet_height: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> TweetImagesSchema:
    html = render_thread_html(thread)
    result = await render_html(browser_ctx, chunk=html, config=config)

    imgs = client.prepare_result_img(
        result,
        tweets_per_image=tweets_per_image,
        max_tweet_height=max_tweet_height,
    )

    media = None
    if include_media:
        media = [MediaSchema.model_validate(media) for tweet in thread for media in tweet.all_media()]

    images = [Base64ImageSchema(content=image_to_base64str(img)) for img in imgs]

    return TweetImagesSchema(
        images=images,
        media=media,
    )


@router.get("/raw-img/{tweet_id}")
async def get_tweet_raw_img(
    thread: CurrentThreadWithPreviews,
    browser_ctx: CurrentSharableBrowserCtx,
    config: CurrentBrowserCtxConfig,
) -> Response:
    html = render_thread_html(thread)
    result = await render_html(browser_ctx, chunk=html, config=config)

    return Response(
        content=image_to_bytes(result.img),
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=thread.png",
        },
    )


__all__ = [
    "router",
]
