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


__all__ = [
    "Base64ImageSchema",
    "ImagesSchema",
    "MediaSchema",
    "TweetID",
    "TweetMediaSchema",
    "TweetSchema",
    "TweetUserSchema",
]
