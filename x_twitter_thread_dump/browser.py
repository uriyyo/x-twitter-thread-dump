import math
from asyncio import gather
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, cast

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import BrowserContext as AsyncBrowserContext
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from .images import bytes_to_image
from .types import ClientBoundingRect, Img

MOBILE_CONFIG = {
    "color_scheme": "dark",
    "viewport": {"width": 450, "height": 400},
    "device_scale_factor": 2,
    "is_mobile": True,
}

BROWSER_RUN_ARGS = [
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
    "--js-flags=--expose-gc,--max-old-space-size=100",  # Limit JS heap to 100MB
    "--single-process",
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
    "--font-render-hinting=medium",
    "--enable-font-antialiasing",
    # Additional CPU-saving args
    "--disable-accelerated-2d-canvas",
    "--disable-accelerated-jpeg-decoding",
    "--disable-accelerated-video-decode",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-features=TranslateUI,BlinkGenPropertyTrees",
    "--disable-background-networking",
    "--disable-notifications",
    "--disable-print-preview",
    "--renderer-process-limit=1",
    "--memory-pressure-off",
]


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
) -> tuple[Img, list[ClientBoundingRect]]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=BROWSER_RUN_ARGS,
        )

        with browser:
            ctx = browser.new_context(**(MOBILE_CONFIG if mobile else {}))  # type: ignore[arg-type]

            page = ctx.new_page()
            page.set_content(html)
            page.wait_for_load_state(state="domcontentloaded")

            screenshot = page.locator(".thread-container").screenshot()
            rects = page.locator(".tweet").evaluate_all("(tweets) => tweets.map(el => el.getBoundingClientRect())")

            return bytes_to_image(screenshot), _normalize_reacts(rects, scale=_get_scale(mobile=mobile))


@asynccontextmanager
async def async_browser(
    *,
    headless: bool = True,
) -> AsyncIterator[AsyncBrowser]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=BROWSER_RUN_ARGS,
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
) -> tuple[Img, list[ClientBoundingRect]]:
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
            page.locator(".tweet").evaluate_all("(tweets) => tweets.map(el => el.getBoundingClientRect())"),
        )

    return bytes_to_image(screenshot), _normalize_reacts(rects, scale=_get_scale(mobile=mobile))


__all__ = [
    "AsyncBrowser",
    "AsyncBrowserContext",
    "async_browser",
    "async_browser_ctx",
    "html_to_image",
    "html_to_image_async",
]
