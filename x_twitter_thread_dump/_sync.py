from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import cast, overload

from httpx import Client, HTTPTransport
from PIL.Image import Image
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, get_ondemand_file_url

from ._base import BaseXTwitterThreadDumpClient
from .browser import html_to_image
from .consts import DEFAULT_BEARER_TOKEN, DEFAULT_RETRIES, DEFAULT_TIMEOUT
from .entities import Thread, Tweet
from .utils import limited, parse_guest_token, response_to_bs4


def _get_client_transaction_client() -> ClientTransaction:
    with Client(headers=generate_headers()) as client:
        home_page = client.get(url="https://x.com")
        home_page_response = response_to_bs4(home_page)

        ondemand_file_url = get_ondemand_file_url(home_page_response)
        ondemand_file = client.get(url=ondemand_file_url)
        ondemand_file_response = response_to_bs4(ondemand_file)

        return ClientTransaction(home_page_response, ondemand_file_response)


def _get_guest_token(client: Client) -> str:
    response = client.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers={
            "Authorization": f"Bearer {DEFAULT_BEARER_TOKEN}",
        },
    )

    return parse_guest_token(response)


@dataclass(kw_only=True)
class XTwitterThreadDumpClient(BaseXTwitterThreadDumpClient):
    client: Client

    def get_thread(
        self,
        tweet_id: str,
        *,
        limit: int | None = None,
    ) -> list[Tweet]:
        thread = [*limited(self._iter_thread(tweet_id), limit=limit)]
        return [*reversed(thread)]

    def _get_tweet(self, tweet_id: str, /) -> Tweet:
        response = self.client.get(**self._prepare_get_tweet_request(tweet_id))
        response.raise_for_status()

        return Tweet.from_raw_response(response.json())

    def _iter_thread(self, tweet_id: str, /) -> Iterator[Tweet]:
        node: str | None = tweet_id
        while node:
            tweet = self._get_tweet(node)
            yield tweet
            node = tweet.parent_id

    @overload
    def thread_to_image(
        self,
        thread: Thread,
        *,
        tweets_per_image: None = None,
        mobile: bool = False,
    ) -> Image:
        pass

    @overload
    def thread_to_image(
        self,
        thread: Thread,
        *,
        tweets_per_image: int,
        mobile: bool = False,
    ) -> list[Image]:
        pass

    def thread_to_image(
        self,
        thread: list[Tweet],
        *,
        tweets_per_image: int | None = None,
        mobile: bool = False,
    ) -> list[Image] | Image:
        result = self._thread_to_html_chunks(
            thread,
            tweets_per_image=tweets_per_image,
        )

        match result:
            case [*htmls]:
                return [html_to_image(html, mobile=mobile) for html in htmls]
            case html:
                return html_to_image(cast(str, html), mobile=mobile)


@contextmanager
def x_twitter_thread_dump_client(
    *,
    timeout: float | None = None,
    retries: int | None = None,
) -> Iterator[XTwitterThreadDumpClient]:
    with Client(
        base_url="https://x.com/",
        follow_redirects=True,
        headers={
            **generate_headers(),
            "Authorization": f"Bearer {DEFAULT_BEARER_TOKEN}",
        },
        timeout=timeout or DEFAULT_TIMEOUT,
        transport=HTTPTransport(
            retries=retries or DEFAULT_RETRIES,
        ),
    ) as client:
        transaction_client = _get_client_transaction_client()

        guest_token = _get_guest_token(client)
        client.headers["x-guest-token"] = guest_token

        yield XTwitterThreadDumpClient(
            client=client,
            transaction_client=transaction_client,
        )


__all__ = [
    "XTwitterThreadDumpClient",
    "x_twitter_thread_dump_client",
]
