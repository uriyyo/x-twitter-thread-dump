from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Self, cast

from .types import AnyDict


@dataclass(kw_only=True)
class Media:
    url: str
    preview_url: str
    type: Literal["image", "video"]

    raw_data: AnyDict | None = None
    raw_preview_bytes: bytes | None = None

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {
                "media_url_https": preview_url,
                "video_info": {"variants": [*variants]},
            }:
                mp4s = [v for v in variants if v["content_type"] == "video/mp4"]
                url = max(mp4s, key=lambda v: v["bitrate"])["url"]

                return cls(
                    url=url,
                    preview_url=preview_url,
                    type="video",
                    raw_data=raw_data,
                )
            case {
                "media_url_https": url,
            }:
                return cls(
                    url=url,
                    preview_url=url,
                    type="image",
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for Media")


_USERNAME_REGEX = re.compile(r"^(@\w+\s+)+", flags=re.MULTILINE | re.DOTALL)


def _remove_usernames_from_full_text_start(full_text: str, /) -> str:
    return _USERNAME_REGEX.sub("", full_text).strip()


_LAST_LINK_REGEX = re.compile(r"https://t\.co/\w+$")


def _remove_last_link(full_text: str, /) -> str:
    return _LAST_LINK_REGEX.sub("", full_text).strip()


def _preprocess_full_text(full_text: str, /) -> str:
    full_text = _remove_usernames_from_full_text_start(full_text)
    return _remove_last_link(full_text)


def _prepare_user_avatar_url(url: str, /) -> str:
    # we need to use better quality avatar
    if url.endswith("_normal.jpg"):
        return url.removesuffix("_normal.jpg") + "_200x200.jpg"

    return url


@dataclass(kw_only=True)
class User:
    id: str
    username: str
    avatar: Media | None = None

    raw_data: AnyDict | None = None

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {
                "rest_id": id_,
                "core": {
                    "screen_name": username,
                },
                "avatar": {
                    "image_url": avatar_url,
                },
            }:
                avatar_url = _prepare_user_avatar_url(avatar_url)

                return cls(
                    id=id_,
                    username=username,
                    avatar=Media(
                        url=avatar_url,
                        preview_url=avatar_url,
                        type="image",
                    ),
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for User")


@dataclass(kw_only=True)
class Tweet:
    id: str
    text: str
    user: User

    likes: int = 0
    quotes: int = 0
    replies: int = 0
    retweets: int = 0
    views: int | None = None
    created_at: datetime | None = None

    parent_id: str | None = None
    quoted_tweet: Tweet | None = None

    media: list[Media] = field(default_factory=list)

    raw_data: AnyDict | None = None

    def all_media(self) -> Iterable[Media]:
        yield from self.media

        if self.quoted_tweet:
            yield from self.quoted_tweet.all_media()

    def all_preview_media(self) -> Iterable[Media]:
        yield from self.all_media()

        if self.user.avatar:
            yield self.user.avatar

        if self.quoted_tweet and self.quoted_tweet.user.avatar:
            yield self.quoted_tweet.user.avatar

    @classmethod
    def _parse_tweet_result(cls, result: AnyDict, /) -> Self:
        match result:
            case {
                "result": {
                    "rest_id": id_,
                    "core": {
                        "user_results": {
                            "result": {**user_data},
                        },
                    },
                    "legacy": {
                        "full_text": text,
                        "quote_count": quotes,
                        "reply_count": replies,
                        "retweet_count": retweets,
                        "created_at": created_at,
                        "favorite_count": likes,
                        "entities": {**entities},
                        **legacy_rest,
                    },
                    **rest,
                },
            }:
                quoted_tweet: Tweet | None
                match rest:
                    case {"quoted_status_result": {**_quoted_status_result}}:
                        quoted_tweet = cls._parse_tweet_result(cast(AnyDict, _quoted_status_result))
                    case _:
                        quoted_tweet = None

                views: int | None
                match rest:
                    case {"views": {"count": _views}}:
                        views = int(_views)
                    case _:
                        views = None

                parent_id: str | None
                match legacy_rest:
                    case {"in_reply_to_status_id_str": str() as _parent_id}:
                        parent_id = _parent_id
                    case _:
                        parent_id = None

                match entities:
                    case {"media": [*_media]}:
                        media = [Media.from_raw_response(cast(AnyDict, m)) for m in _media]
                    case _:
                        media = []

                return cls(
                    id=id_,
                    user=User.from_raw_response(cast(AnyDict, user_data)),
                    text=_preprocess_full_text(text),
                    parent_id=parent_id,
                    quotes=int(quotes),
                    replies=int(replies),
                    retweets=int(retweets),
                    likes=int(likes),
                    views=views,
                    created_at=datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y") if created_at else None,
                    media=media,
                    quoted_tweet=quoted_tweet,
                )
            case _:
                raise ValueError("Invalid raw data format for Tweet")

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {"data": {"tweetResult": result}}:
                return cls._parse_tweet_result(result)
            case _:
                raise ValueError("Invalid raw data format for Tweet")


type Thread = list[Tweet]


__all__ = [
    "Media",
    "Thread",
    "Tweet",
]
