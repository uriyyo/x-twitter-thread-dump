from typing import Annotated

from fastapi import APIRouter, Query, Response
from starlette.responses import HTMLResponse

from x_twitter_thread_dump._api.dependencies import CurrentBrowserCtxConfig, CurrentSharableBrowserCtx
from x_twitter_thread_dump._api.router import render_html
from x_twitter_thread_dump._api.schemas import Base64ImageSchema, ImagesSchema, TikTokCommentSchema
from x_twitter_thread_dump._base import BaseXTwitterThreadDumpClient
from x_twitter_thread_dump._tiktok.entities import TikTokComment
from x_twitter_thread_dump._tiktok.render import render_comments_html
from x_twitter_thread_dump.images import image_to_base64str, image_to_bytes

from .dependencies import CurrentComments, CurrentCommentsWithPreviews, CurrentTikTokClient

router = APIRouter(
    prefix="/tiktok",
)


@router.get(
    "/json",
    response_model=list[TikTokCommentSchema],
)
async def get_tiktok_comments_json(
    comments: CurrentComments,
) -> list[TikTokComment]:
    return comments


@router.get("/html")
async def get_tiktok_comments_html(
    client: CurrentTikTokClient,
    comments: CurrentComments,
    *,
    download_previews: Annotated[bool, Query()] = True,
) -> HTMLResponse:
    if download_previews:
        await client.download_previews(comments)

    html = render_comments_html(comments)

    return HTMLResponse(content=html)


@router.get("/imgs")
async def get_tiktok_comments_imgs(
    comments: CurrentCommentsWithPreviews,
    browser_ctx: CurrentSharableBrowserCtx,
    config: CurrentBrowserCtxConfig,
    *,
    comments_per_image: Annotated[int | None, Query(ge=1, le=10)] = None,
    max_comment_height: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> ImagesSchema:
    html = render_comments_html(comments)
    result = await render_html(browser_ctx, chunk=html, config=config)

    imgs = BaseXTwitterThreadDumpClient.prepare_result_img(
        result,
        tweets_per_image=comments_per_image,
        max_tweet_height=max_comment_height,
    )

    images = [Base64ImageSchema(content=image_to_base64str(img)) for img in imgs]

    return ImagesSchema(
        images=images,
    )


@router.get("/raw-img")
async def get_tiktok_comments_raw_img(
    comments: CurrentCommentsWithPreviews,
    browser_ctx: CurrentSharableBrowserCtx,
    config: CurrentBrowserCtxConfig,
) -> Response:
    html = render_comments_html(comments)
    result = await render_html(browser_ctx, chunk=html, config=config)

    return Response(
        content=image_to_bytes(result.img),
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=tiktok_comment.png",
        },
    )


__all__ = [
    "router",
]
