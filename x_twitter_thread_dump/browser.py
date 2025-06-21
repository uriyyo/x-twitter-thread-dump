import math
from asyncio import gather
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, Literal, cast

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import async_playwright
from playwright.sync_api import Browser as SyncBrowser
from playwright.sync_api import sync_playwright

from .images import bytes_to_image
from .types import BrowserCtxConfig, ClientBoundingRect, Img, Viewport

DEFAULT_CONFIG: BrowserCtxConfig = {
    "color_scheme": "dark",
    "viewport": {"width": 500, "height": 1000},
    "device_scale_factor": 1.5,
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
    "--disable-http2",  # Disable HTTP/2
    "--disable-quic",  # Disable QUIC protocol
    "--disable-image-animation",  # Disable animated images
    "--disable-media-session-api",  # Disable Media Session API
    "--disable-video-capture",  # Disable video capture
    "--disable-audio-capture",  # Disable audio capture
    "--disable-remote-playback-api",  # Disable Remote Playback API
    "--disable-usb",  # Disable USB access
    "--disable-bluetooth",  # Disable Bluetooth access
    "--disable-midi",  # Disable MIDI access
    "--disable-webusb",  # Disable WebUSB
    "--disable-web-bluetooth",  # Disable Web Bluetooth
    "--disable-web-midi",  # Disable Web MIDI
    "--disable-background-tasks",  # Disable background tasks
    "--disable-network-throttling",  # Disable network throttling
    "--disable-network-prediction",  # Disable network prediction
    "--disable-preconnect",  # Disable preconnect
    "--disable-prerender",  # Disable prerendering
    "--disable-offline-pages",  # Disable offline pages
    "--disable-save-password-bubble",  # Disable save password bubble
    "--disable-password-generation",  # Disable password generation
    "--disable-autofill",  # Disable autofill
    "--disable-autofill-keyboard-accessory-view",  # Disable autofill keyboard accessory
    "--process-per-site",  # Use one process per site instead of per tab
    "--disable-component-update",  # Disable browser component updates
    "--disable-site-isolation-trials",  # Disable site isolation (uses fewer processes)
    "--aggressive-cache-discard",  # Aggressively discard cache to save memory
    "--disable-pinch",  # Disable pinch gestures
    "--disable-prefetch",  # Disable prefetching resources
    "--disk-cache-size=1",  # Minimal disk cache (1MB)
    "--disable-smooth-scrolling",  # Disable smooth scrolling
    "--disable-reading-from-canvas",  # Disable canvas readback
    "--enable-tab-discarding",  # Allow discarding tabs to save memory
    "--js-flags=--lite-mode --jitless --no-opt",  # Extreme JS memory optimization
    # "--force-gpu-mem-available-mb=32",  # Limit GPU memory | warn! This flag cause issues with long threads rendering
    "--disable-font-subpixel-positioning",  # Disable font subpixel positioning
    "--disable-composited-antialiasing",  # Disable composited antialiasing
    "--disable-zero-copy",  # Disable zero-copy texture uploads
    "--disable-2d-canvas-clip-aa",  # Disable antialiasing on canvas clip
    "--disable-2d-canvas-image-chromium",  # Use skia for canvas
    "--disable-presentation-api",  # Disable presentation API
    "--disable-permissions-api",  # Disable permissions API
    # Additional flags for extreme resource constraints in 1GB RAM VM
    "--memory-limit=256",  # Limit Chrome's memory usage to 256MB
    "--in-process-gpu",  # Run GPU process inside browser process to reduce process count
    "--enable-low-end-device-mode",  # Enable optimizations for low-memory devices
    # More aggressive process consolidation
    "--disable-features=ProcessPerSiteUpToMainFrameThreshold,IsolateOrigins,site-per-process",
    "--renderer-process-limit=1",  # Ensure only one renderer process (reinforcing existing setting)
    "--blink-settings=preferredImageFormat=webp",  # Use more efficient image format
    "--use-gl=swiftshader",  # Use more efficient software rendering
    "--force-wave-audio",  # Use less memory-intensive audio system
    "--shared-array-buffer=false",  # Disable shared array buffer to save memory
    "--minimal-hints-renderer",  # Reduce renderer features
    "--v8-cache-options=none",  # Disable V8 script caching to reduce memory
    "--no-zygote",  # Disable the zygote process to reduce process count
]


def _get_ctx_config(config: BrowserCtxConfig | None = None) -> BrowserCtxConfig:
    config = DEFAULT_CONFIG | (config or {})

    if not config.get("is_mobile"):
        config.pop("is_mobile", None)
        config.pop("has_touch", None)
        config.pop("device_scale_factor", None)

    return config


def get_browser_ctx_config(  # noqa: PLR0913
    *,
    is_mobile: bool | None = None,
    viewport_height: int | None = None,
    viewport_width: int | None = None,
    screen_height: int | None = None,
    screen_width: int | None = None,
    device_scale_factor: float | None = None,
    color_scheme: Literal["dark", "light", "no-preference", "null"] | None = None,
    contrast: Literal["more", "no-preference", "null"] | None = None,
    forced_colors: Literal["active", "none", "null"] | None = None,
    locale: str | None = None,
    timezone_id: str | None = None,
) -> BrowserCtxConfig:
    config = BrowserCtxConfig()

    if is_mobile is not None:
        config["is_mobile"] = is_mobile
    if viewport_height is not None and viewport_width is not None:
        config["viewport"] = Viewport(width=viewport_width, height=viewport_height)
    if screen_height is not None and screen_width is not None:
        config["screen"] = Viewport(width=screen_width, height=screen_height)
    if device_scale_factor is not None:
        config["device_scale_factor"] = device_scale_factor
    if color_scheme is not None:
        config["color_scheme"] = color_scheme
    if contrast is not None:
        config["contrast"] = contrast
    if forced_colors is not None:
        config["forced_colors"] = forced_colors
    if locale is not None:
        config["locale"] = locale
    if timezone_id is not None:
        config["timezone_id"] = timezone_id

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
            page.locator(".main-container").screenshot(),
            page.locator(".main-container > .container-item").evaluate_all(
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
    "get_browser_ctx_config",
    "html_to_image",
    "html_to_image_async",
]
