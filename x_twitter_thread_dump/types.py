from typing import Any

from PIL import Image

type Img = Image.Image
type AnyDict[TKey = str] = dict[TKey, Any]

__all___ = [
    "Img",
    "AnyDict",
]
