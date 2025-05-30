from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from PIL import Image
from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import BrowserContext as AsyncBrowserContext
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from .images import bytes_to_image

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
    '--font-render-hinting=medium',
    '--enable-font-antialiasing',
]


def html_to_image(
    html: str,
    /,
    *,
    headless: bool = True,
    mobile: bool = False,
) -> Image.Image:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=BROWSER_RUN_ARGS,
        )
        ctx = browser.new_context(**(MOBILE_CONFIG if mobile else {}))  # type: ignore[arg-type]

        page = ctx.new_page()
        page.set_content(html)
        page.wait_for_load_state(state="domcontentloaded")

        screenshot = page.locator(".thread-container").screenshot()
        browser.close()

        return bytes_to_image(screenshot)


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
) -> Image.Image:
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

        screenshot = await page.locator(".thread-container").screenshot()

    return bytes_to_image(screenshot)


__all__ = [
    "AsyncBrowser",
    "AsyncBrowserContext",
    "async_browser",
    "async_browser_ctx",
    "html_to_image",
    "html_to_image_async",
]
