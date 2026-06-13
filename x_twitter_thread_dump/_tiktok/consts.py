TIKWM_BASE_URL = "https://www.tikwm.com/"
TIKWM_API_PREFIX = "/api"

# TikTok's own web API. tikwm serves the reply bodies but strips the
# ``reply_to_reply_id`` threading, so the concrete conversation chain is rebuilt
# from this endpoint. ``aid`` identifies the web client to TikTok.
TIKTOK_API_PREFIX = "https://www.tiktok.com/api"
TIKTOK_WEB_AID = 1988

DEFAULT_USER_AGENT = "Mozilla/5.0"

# tikwm rate-limits aggressively and returns a non-zero ``code`` when hit too
# fast, so api calls are retried with a linear backoff.
TIKWM_RETRIES = 4
TIKWM_BACKOFF = 1.5

# polite delay between the (linear) scan requests while looking for a comment.
SCAN_DELAY = 1.0

# page size used for the comment list / reply endpoints.
PAGE_SIZE = 30


__all__ = [
    "DEFAULT_USER_AGENT",
    "PAGE_SIZE",
    "SCAN_DELAY",
    "TIKTOK_API_PREFIX",
    "TIKTOK_WEB_AID",
    "TIKWM_API_PREFIX",
    "TIKWM_BACKOFF",
    "TIKWM_BASE_URL",
    "TIKWM_RETRIES",
]
