from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic.types import PositiveInt


class BaseSchema(BaseModel):
    model_config = {
        "from_attributes": True,
    }


class Base64ImageSchema(BaseSchema):
    content: str


class MediaSchema(BaseSchema):
    url: AnyHttpUrl
    type: Literal["image", "video"]


class ImagesSchema(BaseSchema):
    images: list[Base64ImageSchema]
    media: list[MediaSchema] | None = None


class TweetMediaSchema(BaseModel):
    url: AnyHttpUrl
    preview_url: AnyHttpUrl
    type: Literal["image", "video"]


type TweetID = Annotated[
    str,
    Field(
        description="The ID of the tweet, e.g. '1234567890123456789'",
        pattern=r"^\d+$",
        min_length=1,
        examples=["1782553830305218930"],
    ),
]


class TweetUserSchema(BaseSchema):
    id: TweetID
    name: str
    username: str

    is_verified: bool = False
    is_blue_verified: bool = False
    avatar: TweetMediaSchema | None = None


class TweetSchema(BaseSchema):
    id: TweetID
    text: str
    user: TweetUserSchema

    likes: PositiveInt = 0
    quotes: PositiveInt = 0
    replies: PositiveInt = 0
    retweets: PositiveInt = 0
    views: PositiveInt | None = None
    created_at: datetime | None = None

    parent_id: str | None = None
    quoted_tweet: TweetSchema | None = None

    media: list[TweetMediaSchema] = Field(default_factory=list)


type TikTokShareURL = Annotated[
    str,
    Field(
        description="A TikTok shared-comment link, e.g. 'https://vt.tiktok.com/ZS9jhAMYEWBdw-XAW67/'",
        min_length=1,
        examples=["https://vt.tiktok.com/ZS9jhAMYEWBdw-XAW67/"],
    ),
]


class TikTokMediaSchema(BaseSchema):
    url: str
    preview_url: str
    type: Literal["image", "video"]


class TikTokUserSchema(BaseSchema):
    id: str
    nickname: str
    unique_id: str
    avatar: TikTokMediaSchema | None = None


class TikTokCommentSchema(BaseSchema):
    id: str
    text: str
    user: TikTokUserSchema

    digg_count: int = 0
    reply_total: int = 0
    created: datetime


__all__ = [
    "Base64ImageSchema",
    "ImagesSchema",
    "MediaSchema",
    "TikTokCommentSchema",
    "TikTokMediaSchema",
    "TikTokShareURL",
    "TikTokUserSchema",
    "TweetID",
    "TweetMediaSchema",
    "TweetSchema",
    "TweetUserSchema",
]
