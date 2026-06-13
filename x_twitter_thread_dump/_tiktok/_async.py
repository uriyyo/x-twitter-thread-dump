import asyncio
import re
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient, AsyncHTTPTransport, HTTPError

from x_twitter_thread_dump._base import BaseXTwitterThreadDumpClient
from x_twitter_thread_dump.browser import AsyncBrowser, html_to_image_async
from x_twitter_thread_dump.consts import DEFAULT_RETRIES, DEFAULT_TIMEOUT
from x_twitter_thread_dump.types import AnyDict, BrowserCtxConfig, Img

from .consts import (
    DEFAULT_USER_AGENT,
    PAGE_SIZE,
    SCAN_DELAY,
    TIKTOK_API_PREFIX,
    TIKTOK_WEB_AID,
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
    ) -> list[TikTokComment]:
        """Resolve a shared-comment link to the conversation chain ending at it.

        Returns the comments oldest-first: the top-level comment followed by the
        replies on the concrete reply-to-reply path that ends at the shared
        comment. If the shared comment is itself top-level, the list holds just
        that comment.

        There is no "fetch comment by id" endpoint, so this pages through the
        top-level comments and, for any comment that has replies, scans its
        reply list for the target. The conversation path (which replies actually
        answer which) is rebuilt in :meth:`_reply_chain`.
        """
        # 1) resolve the short link -> ids carried in the query string
        response = await self.client.head(url, follow_redirects=True)
        resolved_url = str(response.url)
        query = parse_qs(urlparse(resolved_url).query)
        aweme_id = query["share_item_id"][0]
        comment_id = query["share_comment_id"][0]
        creator = self._creator_handle(resolved_url)

        # 2) page top-level comments, scanning replies for the target
        cursor = 0
        while True:
            data = await self._tikwm("comment/list", url=aweme_id, count=PAGE_SIZE, cursor=cursor)

            for top in data["comments"]:
                if top["id"] == comment_id:  # target is a top-level comment
                    return self._mark_creator([TikTokComment.from_raw_response(top)], creator)

                if top.get("reply_total", 0) > 0:
                    chain = await self._reply_chain(aweme_id, top, comment_id)
                    if chain is not None:  # target lives in this comment's replies
                        return self._mark_creator(chain, creator)

                    await asyncio.sleep(SCAN_DELAY)

            if not data.get("hasMore"):
                break

            cursor = data.get("cursor", cursor + PAGE_SIZE)
            await asyncio.sleep(SCAN_DELAY)

        raise LookupError(f"comment {comment_id} not found on video {aweme_id}")

    @staticmethod
    def _creator_handle(resolved_url: str) -> str:
        """Pull the video author's ``unique_id`` from the resolved video URL.

        The short link redirects to ``.../@<handle>/video/<id>``; the handle lets
        the renderer flag the creator's own comments with a "Creator" badge.
        """
        match = re.search(r"/@([^/?#]+)", urlparse(resolved_url).path)
        return match.group(1) if match else ""

    @staticmethod
    def _mark_creator(chain: list[TikTokComment], creator: str, /) -> list[TikTokComment]:
        for comment in chain:
            comment.is_creator = bool(creator) and comment.user.unique_id == creator
        return chain

    async def _reply_chain(
        self,
        aweme_id: str,
        top: AnyDict,
        comment_id: str,
    ) -> list[TikTokComment] | None:
        """Build the concrete conversation chain ending at the shared reply.

        Returns ``[top, ...replies on the reply-to-reply path]`` oldest-first, or
        ``None`` when the target is not among ``top``'s replies. tikwm gives the
        reply bodies but no threading, so the path is rebuilt from TikTok's own
        web API (``reply_to_reply_id``). If that lookup yields nothing the chain
        degrades to just the top comment and the shared reply.
        """
        cursor = 0
        raw_replies: list[AnyDict] = []
        while True:
            data = await self._tikwm(
                "comment/reply",
                video_id=aweme_id,
                comment_id=top["id"],
                count=PAGE_SIZE,
                cursor=cursor,
            )
            raw_replies.extend(data["comments"])

            if not data.get("hasMore"):
                break

            cursor = data.get("cursor", cursor + PAGE_SIZE)
            await asyncio.sleep(SCAN_DELAY)

        by_id = {reply["id"]: reply for reply in raw_replies}
        if comment_id not in by_id:
            return None

        # `parents` maps a reply id to the id it answers ("0" == the top comment).
        # Walk it from the shared reply up to the root, then reverse to oldest-first.
        parents = await self._reply_parents(aweme_id, top["id"])

        path: list[AnyDict] = []
        seen: set[str] = set()
        current = comment_id
        while current and current != "0" and current in by_id and current not in seen:
            seen.add(current)
            path.append(by_id[current])
            current = parents.get(current, "0")
        path.reverse()

        return [
            TikTokComment.from_raw_response(top),
            *(TikTokComment.from_raw_response(reply) for reply in path),
        ]

    async def _reply_parents(self, aweme_id: str, comment_id: str) -> dict[str, str]:
        """Map each reply id to the id it answers (``"0"`` for the top comment).

        Uses TikTok's web API, the only source that exposes ``reply_to_reply_id``.
        Best-effort: returns whatever it managed to collect, so a failed or
        partial fetch lets the caller fall back gracefully.
        """
        parents: dict[str, str] = {}
        cursor = 0
        while True:
            try:
                response = await self.client.get(
                    f"{TIKTOK_API_PREFIX}/comment/list/reply/",
                    params={
                        "aweme_id": aweme_id,
                        "comment_id": comment_id,
                        "count": PAGE_SIZE,
                        "cursor": cursor,
                        "aid": TIKTOK_WEB_AID,
                    },
                )
                response.raise_for_status()
                data = response.json()
            except (HTTPError, ValueError):
                break

            for reply in data.get("comments") or []:
                parents[str(reply["cid"])] = str(reply.get("reply_to_reply_id") or "0")

            if not data.get("has_more"):
                break

            cursor = data.get("cursor", cursor + PAGE_SIZE)
            await asyncio.sleep(SCAN_DELAY)

        return parents

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
