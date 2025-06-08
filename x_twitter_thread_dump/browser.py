import math
from asyncio import gather
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import BrowserContext as AsyncBrowserContext
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from .images import bytes_to_image
from .types import ClientBoundingRect, Img

MOBILE_CONFIG = {
    "color_scheme": "dark",
    "viewport": {"width": 500, "height": 1000},
    "device_scale_factor": 1,
    "is_mobile": True,
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
]


@dataclass
class HTMLToImageResult:
    img: Img
    rects: list[ClientBoundingRect]
    scale: float


def _get_scale(*, mobile: bool) -> float:
    if not mobile:
        return 1.0

    return cast(int, MOBILE_CONFIG["device_scale_factor"])


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


def html_to_image(
    html: str,
    /,
    *,
    headless: bool = True,
    mobile: bool = False,
) -> HTMLToImageResult:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=[*BROWSER_RUN_ARGS],
        )

        with browser:
            ctx = browser.new_context(**(MOBILE_CONFIG if mobile else {}))  # type: ignore[arg-type]

            page = ctx.new_page()
            page.set_content(html)
            page.wait_for_load_state(state="domcontentloaded")

            screenshot = page.locator(".thread-container").screenshot()
            rects = page.locator(".thread-container > .tweet").evaluate_all(
                "(tweets) => tweets.map(el => el.getBoundingClientRect())"
            )

            scale = _get_scale(mobile=mobile)
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


@asynccontextmanager
async def async_browser_ctx(
    *,
    browser: AsyncBrowser | None = None,
    headless: bool = True,
    mobile: bool = False,
) -> AsyncIterator[tuple[AsyncBrowser, AsyncBrowserContext]]:
    async with AsyncExitStack() as stack:
        if browser is None:
            browser = await stack.enter_async_context(async_browser(headless=headless))

        ctx = await browser.new_context(
            **(MOBILE_CONFIG if mobile else {}),  # type: ignore[arg-type]
        )

        async with ctx:
            yield browser, ctx


async def html_to_image_async(
    html: str,
    /,
    *,
    browser: AsyncBrowser | None = None,
    ctx: AsyncBrowserContext | None = None,
    headless: bool = True,
    mobile: bool = False,
) -> HTMLToImageResult:
    async with AsyncExitStack() as stack:
        if ctx is None and browser is None:
            browser = await stack.enter_async_context(async_browser(headless=headless))

        if ctx is None:
            _, ctx = await stack.enter_async_context(
                async_browser_ctx(browser=browser, headless=headless, mobile=mobile)
            )

        page = await ctx.new_page()  # type: ignore[union-attr]
        await page.set_content(html)
        await page.wait_for_load_state(state="domcontentloaded")

        screenshot, rects = await gather(
            page.locator(".thread-container").screenshot(),
            page.locator(".thread-container > .tweet").evaluate_all(
                "(tweets) => tweets.map(el => el.getBoundingClientRect())"
            ),
        )

    scale = _get_scale(mobile=mobile)
    return HTMLToImageResult(
        img=bytes_to_image(screenshot),
        rects=_normalize_reacts(rects, scale=scale),
        scale=scale,
    )


__all__ = [
    "AsyncBrowser",
    "AsyncBrowserContext",
    "HTMLToImageResult",
    "async_browser",
    "async_browser_ctx",
    "html_to_image",
    "html_to_image_async",
]
