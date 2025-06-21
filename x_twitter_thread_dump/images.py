import base64
import io
from collections.abc import Iterator

from PIL import Image

from .types import ClientBoundingRect, Img


def base64str_to_image(base64_str: str) -> Img:
    content = base64.b64decode(base64_str)
    return bytes_to_image(content)


def image_to_base64str(image: Img) -> str:
    image_bytes = image_to_bytes(image)
    return base64.b64encode(image_bytes).decode("utf-8")


def bytes_to_image(image_bytes: bytes) -> Img:
    return Image.open(io.BytesIO(image_bytes))


def image_to_bytes(image: Img) -> bytes:
    with io.BytesIO() as output:
        image.save(output, format="PNG")
        return output.getvalue()


def scale_image(image: Img, *, scale: float) -> Img:
    new_size = (int(image.width * scale), int(image.height * scale))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def divide_images(
    img: Img,
    rects: list[ClientBoundingRect],
    *,
    max_chunk_height: int,
) -> Iterator[Img]:
    if len(rects) < 2:  # noqa: PLR2004
        yield img
        return

    def _img_from_chunk() -> Img:
        if not chunk:
            return img

        return img.crop(
            (
                0,
                chunk[0]["top"],
                img.width,
                chunk[-1]["bottom"],
            )
        )

    first, *rest = rects
    chunk = [first]

    for rect in rest:
        if rect["bottom"] - chunk[0]["top"] > max_chunk_height:
            yield _img_from_chunk()
            chunk = [rect]
        else:
            chunk.append(rect)

    if chunk:
        yield _img_from_chunk()


__all__ = [
    "base64str_to_image",
    "bytes_to_image",
    "divide_images",
    "image_to_base64str",
    "image_to_bytes",
    "scale_image",
]
