import base64
import io

from PIL import Image

from .types import Img


def base64str_to_image(base64_str: str) -> Img:
    content = base64.b64decode(base64_str)
    return bytes_to_image(content)


def bytes_to_image(image_bytes: bytes) -> Img:
    return Image.open(io.BytesIO(image_bytes))


def image_to_bytes(image: Img) -> bytes:
    with io.BytesIO() as output:
        image.save(output, format="PNG")
        return output.getvalue()


def scale_image(image: Img, *, scale: float) -> Img:
    new_size = (int(image.width * scale), int(image.height * scale))
    return image.resize(new_size, Image.Resampling.LANCZOS)


__all__ = [
    "base64str_to_image",
    "bytes_to_image",
    "image_to_bytes",
]
