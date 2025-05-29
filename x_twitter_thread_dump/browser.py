from PIL import Image
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from .images import bytes_to_image

MOBILE_CONFIG = {
    "color_scheme": "dark",
    "viewport": {"width": 500, "height": 400},
    "device_scale_factor": 2,
    "is_mobile": True,
}

BROWSER_RUN_ARGS = [
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--disable-setuid-sandbox',
    '--no-sandbox',
    '--js-flags=--expose-gc,--max-old-space-size=500',  # Limit JS heap to 500MB
    '--single-process',
    '--disable-extensions',
    '--disable-component-extensions-with-background-pages',
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


async def html_to_image_async(
    html: str,
    /,
    *,
    headless: bool = True,
    mobile: bool = False,
) -> Image.Image:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=BROWSER_RUN_ARGS,
        )
        ctx = await browser.new_context(**(MOBILE_CONFIG if mobile else {}))  # type: ignore[arg-type]

        page = await ctx.new_page()
        await page.set_content(html)
        await page.wait_for_load_state(state="domcontentloaded")

        screenshot = await page.locator(".thread-container").screenshot()
        await browser.close()

        return bytes_to_image(screenshot)


__all__ = [
    "html_to_image",
    "html_to_image_async",
]
