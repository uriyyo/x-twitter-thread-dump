from asyncio import timeout
from typing import Annotated, Any

import logfire
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, Response
from playwright._impl._errors import TargetClosedError

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
from .metrics import measure_html_render_duration
from .schemas import Base64ImageSchema, ImagesSchema, MediaSchema, TweetID, TweetSchema
from .settings import settings
from .utils import limit_concurrency, retry

router = APIRouter(
    prefix="/twitter",
)


@router.get("/")
def main_route() -> dict[str, str]:
    return {
        "message": "Welcome to the X Twitter Thread Dump API!",
    }


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
    client: CurrentThreadClient,
    thread: CurrentThread,
    *,
    download_previews: Annotated[bool, Query()] = True,
    show_connector_on_last: Annotated[bool, Query()] = False,
    is_single_tweet: Annotated[bool, Query()] = False,
) -> HTMLResponse:
    if download_previews:
        await client.download_previews(thread)

    html = render_thread_html(
        thread,
        show_connector_on_last=show_connector_on_last,
        is_single_tweet=is_single_tweet,
    )

    return HTMLResponse(content=html)


@retry(
    retries=settings.IMAGE_RENDERING_RETRIES,
    excs=(TargetClosedError,),
)
@limit_concurrency(settings.IMAGE_RENDERING_CONCURRENCY)
@logfire.instrument()
async def render_html(
    browser_ctx: CurrentSharableBrowserCtx,
    chunk: str,
    config: BrowserCtxConfig | None = None,
) -> HTMLToImageResult:
    async with timeout(settings.IMAGE_RENDERING_TIMEOUT), browser_ctx.acquire() as browser:
        with measure_html_render_duration():
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
) -> ImagesSchema:
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

    return ImagesSchema(
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


@router.get("/preview/{tweet_id}")
async def get_preview(
    client: CurrentThreadClient,
    tweet_id: TweetID,
) -> HTMLResponse:
    (last_tweet,) = await client.get_thread(tweet_id, limit=1)

    title = last_tweet.user.name
    description = "Check out this tweet thread!"

    self_link = f"https://x-twitter-thread-dump-api.uriyyo.com/html/{last_tweet.id}?download_previews=false"
    img_link = f"https://x-twitter-thread-dump-api.uriyyo.com/raw-img/{last_tweet.id}?limit=2&device_scale=0.5"

    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tweet Preview</title>

    <!-- Open Graph Meta Tags for social sharing -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="image">
    <meta property="og:url" content="{self_link}">
    <meta property="og:image" content="{img_link}">
    <meta property="og:image:alt" content="{description}">

    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{img_link}">

    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background-color: black;
        }}

        iframe {{
            width: 100%;
            height: 100vh;
            border: none;
            scrollbar-width: none;
        }}
    </style>
</head>
<body>
<iframe src="{self_link}"></iframe>
</body>
        """.strip(),
        headers={"Content-Type": "text/html; charset=utf-8"},
    )


__all__ = [
    "router",
]
