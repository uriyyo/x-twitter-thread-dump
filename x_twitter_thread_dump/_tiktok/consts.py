TIKWM_BASE_URL = "https://www.tikwm.com/"
TIKWM_API_PREFIX = "/api"

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
    "TIKWM_API_PREFIX",
    "TIKWM_BACKOFF",
    "TIKWM_BASE_URL",
    "TIKWM_RETRIES",
]
