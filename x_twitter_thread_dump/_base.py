from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass

from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers

from .browser import HTMLToImageResult
from .consts import TWEET_RESULT_BY_REST_ID_PARAMS, TWEET_RESULT_BY_REST_ID_PATH
from .images import divide_images
from .types import AnyDict, Img


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

    @classmethod
    def prepare_result_img(
        cls,
        res: HTMLToImageResult,
        *,
        tweets_per_image: int | None = None,
        max_tweet_height: int | None = None,
    ) -> list[Img]:
        if len(res.rects) == 1:
            # If there is only one rectangle, return the image as is
            return [res.img]

        img, rects = res.img, res.rects

        match (tweets_per_image, max_tweet_height):
            case (tweets_per_image, None) if tweets_per_image:
                average_height = sum(rect["height"] for rect in rects) // len(rects)

                return [*divide_images(img, rects, max_chunk_height=average_height * tweets_per_image)]
            case (None, max_tweet_height) if max_tweet_height:
                # we need to adjust the height to the scale of the image
                max_tweet_height = int(max_tweet_height * res.scale)

                return [*divide_images(img, rects, max_chunk_height=max_tweet_height)]
            case _:
                return [img]


__all__ = [
    "BaseXTwitterThreadDumpClient",
]
