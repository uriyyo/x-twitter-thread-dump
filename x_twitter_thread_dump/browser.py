import math
from asyncio import gather
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, cast

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import async_playwright
from playwright.sync_api import Browser as SyncBrowser
from playwright.sync_api import sync_playwright

from .images import bytes_to_image
from .types import BrowserCtxConfig, ClientBoundingRect, Img

DEFAULT_CONFIG: BrowserCtxConfig = {
    "color_scheme": "dark",
    "viewport": {"width": 500, "height": 1000},
    "device_scale_factor": 2.0,
    "is_mobile": True,
    "locale": "en-US",
    "offline": True,
    "reduced_motion": "reduce",
    "service_workers": "block",
    "java_script_enabled": False,
}

BROWSER_RUN_ARGS = [
    "--headless=new",  # Use the new headless mode for better performance
    "--disable-gpu",  # Disable GPU usage
    "--disable-dev-shm-usage",  # Avoid shared memory issues
    "--disable-setuid-sandbox",  # Disable setuid sandbox
    "--no-sandbox",  # Disable sandboxing
    "--disable-extensions",  # Disable extensions
    "--disable-background-timer-throttling",  # Disable throttling of timers
    "--disable-backgrounding-occluded-windows",  # Disable backgrounding
    "--disable-renderer-backgrounding",  # Disable renderer backgrounding
    "--disable-features=TranslateUI,BlinkGenPropertyTrees",  # Disable unused features
    "--disable-sync",  # Disable syncing
    "--disable-notifications",  # Disable notifications
    "--disable-default-apps",  # Disable default apps
    "--disable-popup-blocking",  # Disable popup blocking
    "--disable-crash-reporter",  # Disable crash reporting
    "--disable-component-extensions-with-background-pages",  # Disable background extensions
    "--disable-ipc-flooding-protection",  # Disable IPC flooding protection
    "--disable-hang-monitor",  # Disable hang monitor
    "--disable-client-side-phishing-detection",  # Disable phishing detection
    "--disable-print-preview",  # Disable print preview
    "--disable-translate",  # Disable translation
    "--metrics-recording-only",  # Disable metrics recording
    "--mute-audio",  # Mute audio
    "--no-first-run",  # Skip first run tasks
    "--no-default-browser-check",  # Skip default browser check
    "--single-process",  # Run in a single process
    "--renderer-process-limit=1",  # Limit renderer processes
    "--disable-software-rasterizer",  # Disable software rasterizer
    "--disable-accelerated-2d-canvas",  # Disable 2D canvas acceleration
    "--disable-accelerated-video-decode",  # Disable video decoding acceleration
    "--disable-accelerated-jpeg-decoding",  # Disable JPEG decoding acceleration
    "--disable-background-networking",  # Disable background networking
    "--memory-pressure-off",  # Disable memory pressure handling
    "--disable-logging",  # Disable logging to reduce I/O
    "--disable-domain-reliability",  # Disable domain reliability monitoring
    "--disable-pushstate-throttle",  # Disable throttling of pushState
    "--disable-threaded-animation",  # Disable threaded animations
    "--disable-threaded-scrolling",  # Disable threaded scrolling
    "--disable-checker-imaging",  # Disable checker imaging
    "--disable-gesture-typing",  # Disable gesture typing
    "--disable-cloud-import",  # Disable cloud import
    "--disable-voice-input",  # Disable voice input
    "--disable-background-media-suspend",  # Disable media suspension in the background
    "--disable-remote-fonts",  # Disable loading of remote fonts
    "--disable-webgl",  # Disable WebGL
    "--disable-webrtc",  # Disable WebRTC
    "--disable-file-system",  # Disable file system access
    "--disable-databases",  # Disable database storage
    "--disable-local-storage",  # Disable local storage
    "--disable-session-storage",  # Disable session storage
    "--disable-shared-workers",  # Disable shared workers
    "--disable-service-workers",  # Disable service workers
    "--disable-background-fetch",  # Disable background fetch
    "--disable-background-sync",  # Disable background sync
    "--disable-histogram-customizer",  # Disable histogram customizer
    "--disable-permissions-api",  # Disable permissions API
    "--disable-v8-idle-tasks",  # Disable V8 idle tasks
    "--disable-renderer-accessibility",  # Disable accessibility features
    "--disable-speech-api",  # Disable speech API
    "--disable-translate-new-ux",  # Disable new translation UX
    "--disable-ntp-animations",  # Disable new tab page animations
    "--disable-ntp-customization-menu",  # Disable new tab page customization
    "--disable-ntp-modules",  # Disable new tab page modules
    "--disable-ntp-popular-sites",  # Disable popular sites on new tab page
    "--disable-ntp-snippets",  # Disable snippets on new tab page
    "--disable-ntp-remote-suggestions",  # Disable remote suggestions on new tab page
    "--disable-ntp-tiles",  # Disable tiles on new tab page
    "--disable-ntp-ui",  # Disable new tab page UI
    "--disable-ntp-voice-search",  # Disable voice search on new tab page
]


def _get_ctx_config(config: BrowserCtxConfig | None = None) -> BrowserCtxConfig:
    config = DEFAULT_CONFIG | (config or {})

    if not config.get("is_mobile"):
        config.pop("is_mobile", None)
        config.pop("has_touch", None)
        config.pop("device_scale_factor", None)

    return config


@dataclass
class HTMLToImageResult:
    img: Img
    rects: list[ClientBoundingRect]
    scale: float


def _get_scale(*, mobile: bool) -> float:
    if not mobile:
        return 1.0

    return cast(int, DEFAULT_CONFIG["device_scale_factor"])


def _normalize_reacts(
    rects: list[dict[str, Any]],
    *,
    scale: float = 1.0,
) -> list[ClientBoundingRect]:
    def _normalize_val(val: float, /) -> int:
        return math.floor(val * scale)

    return [
        ClientBoundingRect(
            x=_normalize_val(rect["x"]),
            y=_normalize_val(rect["y"]),
            width=_normalize_val(rect["width"]),
            height=_normalize_val(rect["height"]),
            top=_normalize_val(rect["top"]),
            right=_normalize_val(rect["right"]),
            bottom=_normalize_val(rect["bottom"]),
            left=_normalize_val(rect["left"]),
        )
        for rect in rects
    ]


@contextmanager
def sync_browser(
    *,
    headless: bool = True,
) -> Iterator[SyncBrowser]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=[*BROWSER_RUN_ARGS],
        )

        with browser:
            yield browser


def html_to_image(
    html: str,
    /,
    *,
    headless: bool = True,
    browser: SyncBrowser | None = None,
    config: BrowserCtxConfig | None = None,
) -> HTMLToImageResult:
    with ExitStack() as stack:
        if browser is None:
            browser = stack.enter_context(sync_browser(headless=headless))

        ctx_config = _get_ctx_config(config)
        ctx = browser.new_context(**ctx_config)

        page = ctx.new_page()
        page.set_content(html)
        page.wait_for_load_state(state="domcontentloaded")

        screenshot = page.locator(".thread-container").screenshot()
        rects = page.locator(".thread-container > .tweet").evaluate_all(
            "(tweets) => tweets.map(el => el.getBoundingClientRect())"
        )

        scale = _get_scale(mobile=ctx_config.get("is_mobile", True))
        return HTMLToImageResult(
            img=bytes_to_image(screenshot),
            rects=_normalize_reacts(rects, scale=scale),
            scale=scale,
        )


@asynccontextmanager
async def async_browser(
    *,
    headless: bool = True,
) -> AsyncIterator[AsyncBrowser]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=[*BROWSER_RUN_ARGS],
        )

        async with browser:
            yield browser


async def html_to_image_async(
    html: str,
    /,
    *,
    browser: AsyncBrowser | None = None,
    headless: bool = True,
    config: BrowserCtxConfig | None = None,
) -> HTMLToImageResult:
    async with AsyncExitStack() as stack:
        if browser is None:
            browser = await stack.enter_async_context(async_browser(headless=headless))

        ctx_config = _get_ctx_config(config)
        ctx = await browser.new_context(**ctx_config)

        page = await ctx.new_page()
        await page.set_content(html)
        await page.wait_for_load_state(state="domcontentloaded")

        screenshot, rects = await gather(
            page.locator(".thread-container").screenshot(),
            page.locator(".thread-container > .tweet").evaluate_all(
                "(tweets) => tweets.map(el => el.getBoundingClientRect())"
            ),
        )

    scale = _get_scale(mobile=ctx_config.get("is_mobile", True))
    return HTMLToImageResult(
        img=bytes_to_image(screenshot),
        rects=_normalize_reacts(rects, scale=scale),
        scale=scale,
    )


__all__ = [
    "AsyncBrowser",
    "HTMLToImageResult",
    "SyncBrowser",
    "async_browser",
    "html_to_image",
    "html_to_image_async",
]
