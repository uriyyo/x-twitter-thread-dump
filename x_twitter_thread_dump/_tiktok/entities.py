from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Self

from x_twitter_thread_dump.types import AnyDict


@dataclass(kw_only=True)
class TikTokMedia:
    url: str
    preview_url: str
    type: Literal["image", "video"] = "image"

    raw_data: AnyDict | None = field(default=None, repr=False)
    raw_preview_bytes: bytes | None = field(default=None, repr=False)


@dataclass(kw_only=True)
class TikTokUser:
    id: str
    nickname: str
    unique_id: str
    avatar: TikTokMedia

    raw_data: AnyDict | None = field(default=None, repr=False)

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {
                "id": id_,
                "nickname": nickname,
                "unique_id": unique_id,
                **rest,
            }:
                match rest:
                    case {"avatar": str(avatar_url)} if avatar_url:
                        avatar = TikTokMedia(url=avatar_url, preview_url=avatar_url)
                    case _:
                        avatar = TikTokMedia(url="", preview_url="")

                return cls(
                    id=str(id_),
                    nickname=nickname,
                    unique_id=unique_id,
                    avatar=avatar,
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for TikTokUser")


@dataclass(kw_only=True)
class TikTokComment:
    id: str
    text: str
    user: TikTokUser
    digg_count: int = 0
    reply_total: int = 0
    created: datetime

    raw_data: AnyDict | None = field(default=None, repr=False)

    @classmethod
    def from_raw_response(cls, raw_data: AnyDict, /) -> Self:
        match raw_data:
            case {
                "id": id_,
                "text": text,
                "user": user,
                "create_time": create_time,
                **rest,
            }:
                return cls(
                    id=str(id_),
                    text=text,
                    user=TikTokUser.from_raw_response(user),
                    digg_count=rest.get("digg_count", 0),
                    reply_total=rest.get("reply_total", 0),
                    created=datetime.fromtimestamp(create_time),
                    raw_data=raw_data,
                )
            case _:
                raise ValueError("Invalid raw data format for TikTokComment")

    def all_preview_media(self) -> Iterator[TikTokMedia]:
        if self.user.avatar.preview_url:
            yield self.user.avatar


__all__ = [
    "TikTokComment",
    "TikTokMedia",
    "TikTokUser",
]
