from asyncio import gather
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from httpx import AsyncClient, AsyncHTTPTransport
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, get_ondemand_file_url

from ._base import BaseXTwitterThreadDumpClient
from .browser import html_to_image_async
from .consts import DEFAULT_BEARER_TOKEN, DEFAULT_RETRIES, DEFAULT_TIMEOUT
from .entities import Thread, Tweet
from .render import render_thread_html
from .types import Img
from .utils import alimited, parse_guest_token, response_to_bs4


async def _get_client_transaction_client(
    *,
    timeout: float | None = None,
    retries: int | None = None,
) -> ClientTransaction:
    async with AsyncClient(
        headers=generate_headers(),
        timeout=timeout or DEFAULT_TIMEOUT,
        transport=AsyncHTTPTransport(
            retries=retries or DEFAULT_RETRIES,
        ),
    ) as client:
        home_page = await client.get(url="https://x.com")
        home_page_response = response_to_bs4(home_page)

        ondemand_file_url = get_ondemand_file_url(home_page_response)
        ondemand_file = await client.get(url=ondemand_file_url)
        ondemand_file_response = response_to_bs4(ondemand_file)

        return ClientTransaction(home_page_response, ondemand_file_response)


async def _get_guest_token(client: AsyncClient) -> str:
    response = await client.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers={
            "Authorization": f"Bearer {DEFAULT_BEARER_TOKEN}",
        },
    )

    return parse_guest_token(response)


@dataclass(kw_only=True)
class XTwitterThreadDumpAsyncClient(BaseXTwitterThreadDumpClient):
    client: AsyncClient

    async def get_thread(
        self,
        tweet_id: str,
        *,
        limit: int | None = None,
    ) -> Thread:
        thread = [tweet async for tweet in alimited(self._iter_thread(tweet_id), limit=limit)]
        thread.reverse()

        return thread

    async def _get_tweet(self, tweet_id: str, /) -> Tweet:
        response = await self.client.get(**self._prepare_get_tweet_request(tweet_id))
        response.raise_for_status()

        return Tweet.from_raw_response(response.json())

    async def _iter_thread(self, tweet_id: str, /) -> AsyncIterator[Tweet]:
        node: str | None = tweet_id
        while node:
            tweet = await self._get_tweet(node)
            yield tweet
            node = tweet.parent_id

    async def thread_to_image(
        self,
        thread: list[Tweet],
        *,
        tweets_per_image: int | None = None,
        max_tweet_height: int | None = None,
        mobile: bool = False,
    ) -> list[Img]:
        await self.download_previews(thread)

        html = render_thread_html(thread)
        result = await html_to_image_async(html, mobile=mobile)

        return self._prepare_result_img(
            result,
            tweets_per_image=tweets_per_image,
            max_tweet_height=max_tweet_height,
        )

    async def download_previews(self, thread: Thread, /) -> None:
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
async def x_twitter_thread_dump_async_client(
    *,
    timeout: float | None = None,
    retries: int | None = None,
) -> AsyncIterator[XTwitterThreadDumpAsyncClient]:
    async with AsyncClient(
        base_url="https://x.com/",
        follow_redirects=True,
        headers={
            **generate_headers(),
            "Authorization": f"Bearer {DEFAULT_BEARER_TOKEN}",
        },
        timeout=timeout or DEFAULT_TIMEOUT,
        transport=AsyncHTTPTransport(
            retries=retries or DEFAULT_RETRIES,
        ),
    ) as client:
        transaction_client = await _get_client_transaction_client(
            timeout=timeout,
            retries=retries,
        )

        guest_token = await _get_guest_token(client)
        client.headers["x-guest-token"] = guest_token

        yield XTwitterThreadDumpAsyncClient(
            client=client,
            transaction_client=transaction_client,
        )


__all__ = [
    "XTwitterThreadDumpAsyncClient",
    "x_twitter_thread_dump_async_client",
]
