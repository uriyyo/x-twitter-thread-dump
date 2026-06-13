import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient, AsyncHTTPTransport

from x_twitter_thread_dump._base import BaseXTwitterThreadDumpClient
from x_twitter_thread_dump.browser import AsyncBrowser, html_to_image_async
from x_twitter_thread_dump.consts import DEFAULT_RETRIES, DEFAULT_TIMEOUT
from x_twitter_thread_dump.types import AnyDict, BrowserCtxConfig, Img

from .consts import (
    DEFAULT_USER_AGENT,
    PAGE_SIZE,
    SCAN_DELAY,
    TIKWM_API_PREFIX,
    TIKWM_BACKOFF,
    TIKWM_BASE_URL,
    TIKWM_RETRIES,
)
from .entities import TikTokComment
from .render import render_comments_html


@dataclass
class TikTokAsyncClient:
    client: AsyncClient

    async def _tikwm(self, path: str, /, **params: str | int) -> AnyDict:
        data: AnyDict = {}

        for attempt in range(TIKWM_RETRIES):
            response = await self.client.get(f"{TIKWM_API_PREFIX}/{path}/", params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("code") == 0:
                return cast(AnyDict, data["data"])

            await asyncio.sleep(TIKWM_BACKOFF * (attempt + 1))  # rate-limited; back off

        raise RuntimeError(f"tikwm {path} failed: {data!r}")

    async def resolve_comment(
        self,
        url: str,
    ) -> tuple[TikTokComment, TikTokComment | None]:
        """Resolve a shared-comment link to ``(comment, parent_or_None)``.

        There is no "fetch comment by id" endpoint, so this pages through the
        top-level comments and, for any comment that has replies, scans its
        reply list for the target. Whichever comment's reply list contains the
        target is the parent.
        """
        # 1) resolve the short link -> ids carried in the query string
        response = await self.client.head(url, follow_redirects=True)
        query = parse_qs(urlparse(str(response.url)).query)
        aweme_id = query["share_item_id"][0]
        comment_id = query["share_comment_id"][0]

        # 2) page top-level comments, scanning replies for the target
        cursor = 0
        while True:
            data = await self._tikwm("comment/list", url=aweme_id, count=PAGE_SIZE, cursor=cursor)

            for top in data["comments"]:
                if top["id"] == comment_id:  # target is a top-level comment
                    return TikTokComment.from_raw_response(top), None

                if top.get("reply_total", 0) > 0:
                    replies = await self._tikwm(
                        "comment/reply",
                        video_id=aweme_id,
                        comment_id=top["id"],
                        count=PAGE_SIZE,
                        cursor=0,
                    )
                    for reply in replies["comments"]:
                        if reply["id"] == comment_id:  # found as a reply -> top is the parent
                            return TikTokComment.from_raw_response(reply), TikTokComment.from_raw_response(top)

                    await asyncio.sleep(SCAN_DELAY)

            if not data.get("hasMore"):
                break

            cursor = data.get("cursor", cursor + PAGE_SIZE)
            await asyncio.sleep(SCAN_DELAY)

        raise LookupError(f"comment {comment_id} not found on video {aweme_id}")

    async def comment_to_image(
        self,
        comments: list[TikTokComment],
        *,
        tweets_per_image: int | None = None,
        max_tweet_height: int | None = None,
        config: BrowserCtxConfig | None = None,
        browser: AsyncBrowser | None = None,
    ) -> list[Img]:
        await self.download_previews(comments)

        html = render_comments_html(comments)
        result = await html_to_image_async(
            html,
            browser=browser,
            config=config,
        )

        return BaseXTwitterThreadDumpClient.prepare_result_img(
            result,
            tweets_per_image=tweets_per_image,
            max_tweet_height=max_tweet_height,
        )

    async def download_previews(self, comments: list[TikTokComment], /) -> None:
        medias = [media for comment in comments for media in comment.all_preview_media() if not media.raw_preview_bytes]

        urls = defaultdict(list)
        for media in medias:
            urls[media.preview_url].append(media)

        async def _worker(url: str, /) -> None:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                content = await response.aread()

                for media in urls[url]:
                    media.raw_preview_bytes = content

        await asyncio.gather(*[_worker(url) for url in urls])


@asynccontextmanager
async def tiktok_async_client(
    *,
    timeout: float | None = None,
    retries: int | None = None,
    cookies: dict[str, Any] | None = None,
) -> AsyncIterator[TikTokAsyncClient]:
    async with AsyncClient(
        base_url=TIKWM_BASE_URL,
        follow_redirects=True,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=timeout or DEFAULT_TIMEOUT,
        transport=AsyncHTTPTransport(
            retries=retries or DEFAULT_RETRIES,
        ),
        cookies=cookies,
    ) as client:
        yield TikTokAsyncClient(client=client)


__all__ = [
    "TikTokAsyncClient",
    "tiktok_async_client",
]
