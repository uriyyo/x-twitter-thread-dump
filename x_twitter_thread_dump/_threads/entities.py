from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Self, cast

from x_twitter_thread_dump.types import AnyDict


@dataclass(kw_only=True)
class ThreadMedia:
    url: str
    preview_url: str
    type: Literal["image", "video"]

    raw_data: AnyDict | None = field(default=None, repr=False)
    raw_preview_bytes: bytes | None = field(default=None, repr=False)

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {
                "video_versions": [*video_versions],
                "image_versions2": {"candidates": [*candidates]},
            } if video_versions and candidates:
                best_img, *_ = candidates
                best_vid = max(video_versions, key=lambda v: v["type"])

                return cls(
                    url=best_vid["url"],
                    preview_url=best_img["url"],
                    type="video",
                    raw_data=raw_data,
                )
            case {
                "image_versions2": {"candidates": [*candidates]},
            } if candidates:
                best, *_ = candidates

                return cls(
                    url=best["url"],
                    preview_url=best["url"],
                    type="image",
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for ThreadMedia")

    @classmethod
    def medias_from_raw_response(cls, raw_data: AnyDict, /) -> list[Self]:
        match raw_data:
            case {
                "carousel_media": [*medias],
            } if medias:
                return [cls.from_raw_response(cast(AnyDict, media)) for media in medias]
            case {
                "image_versions2": {"candidates": [*candidates]},
            } if candidates:
                return [cls.from_raw_response(raw_data)]
            case _:
                return []


@dataclass(kw_only=True)
class ThreadUser:
    id: str
    username: str
    full_name: str | None = None
    is_verified: bool
    profile_pic: ThreadMedia

    raw_data: AnyDict | None = field(default=None, repr=False)

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {
                "id": id_,
                "username": username,
                "is_verified": is_verified,
                "profile_pic_url": profile_pic_url,
                **rest,
            }:
                match rest:
                    case {"full_name": str(_full_name)}:
                        full_name: str | None = _full_name
                    case _:
                        full_name = None

                return cls(
                    id=id_,
                    username=username,
                    full_name=full_name,
                    is_verified=is_verified,
                    profile_pic=ThreadMedia(
                        url=profile_pic_url,
                        preview_url=profile_pic_url,
                        type="image",
                    ),
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for ThreadUser")


@dataclass(kw_only=True)
class ThreadPost:
    id: str
    user: ThreadUser
    caption: str
    like_count: int | None = None
    quote_count: int | None = None
    repost_count: int | None = None
    direct_reply_count: int | None = None
    taken_at: datetime
    media: list[ThreadMedia] = field(default_factory=list)
    quoted_thread: Self | None = None

    raw_data: AnyDict | None = field(default=None, repr=False)

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {"post": _post}:
                raw_data = cast(AnyDict, _post)

        match raw_data:
            case {
                "id": id_,
                "user": user,
                "caption": caption,
                "text_post_app_info": post_app_info,
                "taken_at": taken_at,
                **rest,
            }:
                match caption:
                    case {"text": _caption_text}:
                        caption_text = _caption_text
                    case _:
                        caption_text = ""

                match post_app_info:
                    case {
                        "quote_count": _quote_count,
                        "repost_count": _repost_count,
                        "direct_reply_count": _direct_reply_count,
                    }:
                        quote_count = _quote_count
                        repost_count = _repost_count
                        direct_reply_count = _direct_reply_count
                    case _:
                        quote_count = None
                        repost_count = None
                        direct_reply_count = None

                match post_app_info:
                    case {"share_info": {"quoted_post": quoted_post}} if quoted_post:
                        quoted_thread: Self | None = cls.from_raw_response(cast(AnyDict, quoted_post))
                    case _:
                        quoted_thread = None

                match rest:
                    case {"like_count": _like_count}:
                        like_count = _like_count
                    case _:
                        like_count = None

                return cls(
                    id=id_,
                    user=ThreadUser.from_raw_response(user),
                    caption=caption_text,
                    like_count=like_count,
                    quote_count=quote_count,
                    repost_count=repost_count,
                    direct_reply_count=direct_reply_count,
                    taken_at=datetime.fromtimestamp(taken_at),
                    media=ThreadMedia.medias_from_raw_response(rest),
                    quoted_thread=quoted_thread,
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for ThreadTweet")

    @classmethod
    def thread_from_raw_response(cls, raw_data: AnyDict, /) -> list[Self]:
        match raw_data:
            case {"data": {"data": {"edges": [{"node": {"thread_items": [*items]}}, *_]}}}:
                return [cls.from_raw_response(cast(AnyDict, item)) for item in items]
            case _:
                raise ValueError("Invalid raw data format for ThreadTweet")

    def all_media(self) -> Iterator[ThreadMedia]:
        yield from self.media

        if self.quoted_thread:
            yield from self.quoted_thread.all_media()

    def all_preview_media(self) -> Iterator[ThreadMedia]:
        yield from self.all_media()

        if self.user.profile_pic:
            yield self.user.profile_pic

        if self.quoted_thread and self.quoted_thread.user.profile_pic:
            yield self.quoted_thread.user.profile_pic


__all__ = [
    "ThreadMedia",
    "ThreadPost",
    "ThreadUser",
]
