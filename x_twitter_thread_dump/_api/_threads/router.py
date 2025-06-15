from typing import Annotated

from fastapi import APIRouter, Query
from starlette.responses import HTMLResponse

from x_twitter_thread_dump._api.dependencies import CurrentBrowserCtxConfig, CurrentSharableBrowserCtx
from x_twitter_thread_dump._api.router import render_html
from x_twitter_thread_dump._api.schemas import Base64ImageSchema, ImagesSchema, MediaSchema
from x_twitter_thread_dump._base import BaseXTwitterThreadDumpClient
from x_twitter_thread_dump._threads.render import render_thread_html
from x_twitter_thread_dump.images import image_to_base64str

from .dependencies import CurrentThread, CurrentThreadsClient, CurrentThreadWithPreviews

router = APIRouter(
    prefix="/threads",
)


@router.get("/html/{post_id}")
async def get_threads_post_html(
    client: CurrentThreadsClient,
    thread: CurrentThread,
    *,
    download_previews: Annotated[bool, Query()] = True,
) -> HTMLResponse:
    if download_previews:
        await client.download_previews(thread)

    html = render_thread_html(thread)

    return HTMLResponse(content=html)


@router.get("/imgs/{post_id}")
async def get_threads_imgs(  # noqa: PLR0913
    thread: CurrentThreadWithPreviews,
    browser_ctx: CurrentSharableBrowserCtx,
    config: CurrentBrowserCtxConfig,
    *,
    include_media: Annotated[bool, Query()] = False,
    tweets_per_image: Annotated[int | None, Query(ge=1, le=10)] = None,
    max_tweet_height: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> ImagesSchema:
    html = render_thread_html(thread)
    result = await render_html(browser_ctx, chunk=html, config=config)

    imgs = BaseXTwitterThreadDumpClient.prepare_result_img(
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


__all__ = [
    "router",
]
