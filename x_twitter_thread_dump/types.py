from typing import Any, Literal, NotRequired, TypedDict

from PIL import Image


class Viewport(TypedDict):
    width: int
    height: int


class BrowserCtxConfig(TypedDict):
    user_agent: NotRequired[str]
    offline: NotRequired[bool]

    is_mobile: NotRequired[bool]
    has_touch: NotRequired[bool]

    viewport: NotRequired[Viewport]
    screen: NotRequired[Viewport]
    device_scale_factor: NotRequired[float]

    color_scheme: NotRequired[Literal["dark", "light", "no-preference", "null"]]
    contrast: NotRequired[Literal["more", "no-preference", "null"]]
    forced_colors: NotRequired[Literal["active", "none", "null"]]
    reduced_motion: NotRequired[Literal["no-preference", "null", "reduce"]]

    service_workers: NotRequired[Literal["allow", "block"]]
    java_script_enabled: NotRequired[bool]

    locale: NotRequired[str]
    timezone_id: NotRequired[str]


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
    "Viewport",
    "BrowserContextConfig",
]
