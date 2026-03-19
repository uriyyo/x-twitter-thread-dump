import json
import re
from asyncio import gather
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient, AsyncHTTPTransport

from x_twitter_thread_dump._base import BaseXTwitterThreadDumpClient
from x_twitter_thread_dump.browser import AsyncBrowser, html_to_image_async
from x_twitter_thread_dump.consts import DEFAULT_RETRIES, DEFAULT_TIMEOUT
from x_twitter_thread_dump.types import BrowserCtxConfig, Img

from .consts import IG_APP_ID, QUERY_VARS
from .entities import ThreadPost
from .render import render_thread_html

_QUERY_ID_REGEX = re.compile(r'"queryID":\s*?"(\d+)"')
_LSD_REGEX = re.compile(r'"LSD",\[\],\{"token":"([^"]+)"')
_SSR_PRELOADER_REGEX = re.compile(r'adp_BarcelonaPostPageDirectQueryRelayPreloader_\w+",')
_SHORTCODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _shortcode_to_pk(shortcode: str) -> str:
    n = 0
    for c in shortcode:
        n = n * 64 + _SHORTCODE_ALPHABET.index(c)
    return str(n)


def _extract_ssr_data(html: str) -> dict[Any, Any] | None:
    pos = 0
    while match := _SSR_PRELOADER_REGEX.search(html, pos):
        pos = match.end()

        with suppress(json.JSONDecodeError, KeyError, ValueError):
            data, _ = json.JSONDecoder().raw_decode(html, match.end())

            match data:
                case {
                    "__bbox": {
                        "complete": True,
                        "result": {**result},
                    },
                }:
                    return result

    return None


@dataclass
class ThreadsAsyncClient:
    client: AsyncClient

    async def get_thread(
        self,
        post_id: str,
    ) -> list[ThreadPost]:
        response = await self.client.get(
            f"/_/post/{post_id}",
            headers={
                "accept": "text/html",
                "accept-encoding": "gzip",
            },
        )
        response.raise_for_status()

        if ssr_data := _extract_ssr_data(response.text):
            return ThreadPost.thread_from_raw_response(ssr_data)

        if match := _QUERY_ID_REGEX.search(response.text):
            query_id = match.group(1)
        else:
            raise ValueError("Could not find queryID in the response.")

        if match := _LSD_REGEX.search(response.text):
            lsd = match.group(1)
        else:
            raise ValueError("Could not find LSD token in the response.")

        pk = _shortcode_to_pk(post_id)

        response = await self.client.post(
            "/graphql/query",
            data={
                "variables": json.dumps(QUERY_VARS | {"postID": pk}),
                "server_timestamps": True,
                "doc_id": int(query_id),
                "lsd": lsd,
            },
            headers={
                "x-ig-app-id": IG_APP_ID,
                "x-csrftoken": self.client.cookies["csrftoken"],
                "x-fb-lsd": lsd,
                "accept": "*/*",
            },
        )
        response.raise_for_status()

        data = response.json()
        return ThreadPost.thread_from_raw_response(data)

    async def thread_to_image(
        self,
        thread: list[ThreadPost],
        *,
        tweets_per_image: int | None = None,
        max_tweet_height: int | None = None,
        config: BrowserCtxConfig | None = None,
        browser: AsyncBrowser | None = None,
    ) -> list[Img]:
        await self.download_previews(thread)

        html = render_thread_html(thread)
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

    async def download_previews(self, thread: list[ThreadPost], /) -> None:
        medias = [media for tweet in thread for media in tweet.all_preview_media() if not media.raw_preview_bytes]

        urls = defaultdict(list)
        for media in medias:
            urls[media.preview_url].append(media)

        async def _worker(url: str, /) -> None:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                content = await response.aread()

                for media in urls[url]:
                    media.raw_preview_bytes = content

        await gather(*[_worker(url) for url in urls])


@asynccontextmanager
async def threads_async_client(
    *,
    timeout: float | None = None,
    retries: int | None = None,
    cookies: dict[str, Any] | None = None,
) -> AsyncIterator[ThreadsAsyncClient]:
    async with AsyncClient(
        base_url="https://www.threads.com/",
        follow_redirects=True,
        timeout=timeout or DEFAULT_TIMEOUT,
        transport=AsyncHTTPTransport(
            retries=retries or DEFAULT_RETRIES,
        ),
        cookies=cookies,
    ) as client:
        yield ThreadsAsyncClient(client=client)


__all__ = [
    "ThreadsAsyncClient",
    "threads_async_client",
]
