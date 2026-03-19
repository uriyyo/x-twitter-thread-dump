import base64
import pathlib
import re
from datetime import datetime

import jinja2

from .entities import ThreadPost

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=pathlib.Path(__file__).parent,
    ),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)
jinja2_env.filters["b64encode"] = lambda x: base64.b64encode(x).decode("utf-8")
jinja2_env.filters["regex_replace"] = lambda s, pattern, replacement: re.sub(pattern, replacement, s)


def _timeago(dt: datetime) -> str:
    now = datetime.now(tz=dt.tzinfo)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:  # noqa: PLR2004
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:  # noqa: PLR2004
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:  # noqa: PLR2004
        return f"{hours}h"
    days = hours // 24
    if days < 7:  # noqa: PLR2004
        return f"{days}d"

    return dt.strftime("%b %d")


jinja2_env.filters["timeago"] = _timeago


def render_thread_html(
    thread: list[ThreadPost],
) -> str:
    template = jinja2_env.get_template("threads_template.html")

    return template.render(
        thread=thread,
    )


__all__ = [
    "render_thread_html",
]
