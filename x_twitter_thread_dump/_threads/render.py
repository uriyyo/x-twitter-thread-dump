import base64
import pathlib
import re

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
