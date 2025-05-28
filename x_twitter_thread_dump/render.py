import pathlib

import jinja2

from .entities import Thread

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=pathlib.Path(__file__).parent,
    ),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)


def render_thread_html(
    thread: Thread,
    *,
    is_single_tweet: bool = False,
    show_connector_on_last: bool = False,
) -> str:
    template = jinja2_env.get_template("thread_template.html")

    return template.render(
        thread=thread,
        is_single_tweet=is_single_tweet,
        show_connector_on_last=show_connector_on_last,
    )


__all__ = [
    "render_thread_html",
]
