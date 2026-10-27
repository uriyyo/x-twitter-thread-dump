from typing import Literal, final

@final
class Rect:
    """Element bounding box in CSS pixels, relative to the captured element."""

    @property
    def x(self) -> float: ...
    @property
    def y(self) -> float: ...
    @property
    def width(self) -> float: ...
    @property
    def height(self) -> float: ...
    @property
    def left(self) -> float: ...
    @property
    def top(self) -> float: ...
    @property
    def right(self) -> float: ...
    @property
    def bottom(self) -> float: ...

@final
class RenderResult:
    """Rendered image as raw RGBA8 pixels, plus the requested element rects."""

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    @property
    def scale(self) -> float: ...
    @property
    def rects(self) -> list[Rect]: ...
    @property
    def rgba(self) -> bytes: ...
    def png(self, *, fast: bool = True) -> bytes: ...

def render(
    html: str,
    /,
    *,
    width: int = 500,
    height: int = 1000,
    scale: float = 1.0,
    color_scheme: Literal["light", "dark"] = "light",
    selector: str | None = None,
    rects_selector: str | None = None,
    backend: Literal["vello", "skia"] = "skia",
) -> RenderResult: ...
