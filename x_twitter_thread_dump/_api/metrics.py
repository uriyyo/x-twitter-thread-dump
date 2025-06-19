import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import partial
from typing import Literal, assert_never

import logfire
from opentelemetry.metrics import Histogram

html_render_duration = logfire.metric_histogram(
    "html_render_duration",
    description="Duration of HTML rendering in milliseconds",
    unit="ms",
)

shared_browser_age = logfire.metric_histogram(
    "shared_browser_age",
    description="Age of the shared browser in seconds",
    unit="s",
)


@contextmanager
def measure_duration(
    metric: Histogram,
    *,
    unit: Literal["ms", "s"],
) -> Iterator[None]:
    start = time.perf_counter()

    try:
        yield
    finally:
        end = time.perf_counter_ns()
        duration_ns = end - start

        match unit:
            case "ms":
                duration = duration_ns / 1_000_000
            case "s":
                duration = duration_ns / 1_000_000_000
            case _:
                assert_never(unit)

        metric.record(duration)


measure_html_render_duration = partial(measure_duration, html_render_duration, unit="ms")

__all__ = [
    "measure_html_render_duration",
    "shared_browser_age",
]
