from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import dataclass

from more_itertools import divide
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers

from .consts import TWEET_RESULT_BY_REST_ID_PARAMS, TWEET_RESULT_BY_REST_ID_PATH
from .entities import Thread
from .render import render_thread_html
from .types import AnyDict


@dataclass(kw_only=True)
class BaseXTwitterThreadDumpClient:
    transaction_client: ClientTransaction

    def _prepare_get_tweet_request(self, tweet_id: str, /) -> AnyDict:
        params = deepcopy(TWEET_RESULT_BY_REST_ID_PARAMS)
        params["variables"]["tweetId"] = str(tweet_id)  # type: ignore[index]
        params = {k: json.dumps(v) for k, v in params.items()}

        return {
            "url": f"https://api.x.com/{TWEET_RESULT_BY_REST_ID_PATH.removeprefix('/')}",
            "params": params,
            "headers": {
                **generate_headers(),
                "x-client-transaction-id": self.transaction_client.generate_transaction_id(
                    path=TWEET_RESULT_BY_REST_ID_PATH,
                    method="GET",
                ),
            },
        }

    def _thread_to_html_chunks(
        self,
        thread: Thread,
        /,
        *,
        tweets_per_image: int | None = None,
    ) -> str | list[str]:
        if tweets_per_image is None:
            return render_thread_html(
                thread,
                is_single_tweet=False,
            )

        chunks = [[*chunk] for chunk in divide(math.ceil(len(thread) / tweets_per_image), thread)]

        return [
            render_thread_html(
                chunk,
                is_single_tweet=len(thread) == 1,
                show_connector_on_last=chunk is not chunks[-1],
            )
            for chunk in chunks
        ]


__all__ = [
    "BaseXTwitterThreadDumpClient",
]
