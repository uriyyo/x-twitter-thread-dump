from typing import Any, TypedDict

from PIL import Image


class ClientBoundingRect(TypedDict):
    x: int
    y: int
    top: int
    bottom: int
    left: int
    right: int
    width: int
    height: int


type Img = Image.Image
type AnyDict[TKey = str] = dict[TKey, Any]

__all___ = [
    "Img",
    "AnyDict",
    "ClientBoundingRect",
]
