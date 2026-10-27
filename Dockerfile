FROM rust:1-bookworm AS blitz-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends libfontconfig1-dev libfreetype-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_DOWNLOADS=automatic \
    UV_PYTHON=3.13

WORKDIR /build

COPY blitz_render ./blitz_render
# runtime image already ships fontconfig/freetype, so no need to vendor them into the wheel
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/build/blitz_render/target \
    uvx maturin build --release --auditwheel skip --manifest-path blitz_render/Cargo.toml --out /wheels


FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=automatic \
    UV_PYTHON=3.13 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY blitz_render/pyproject.toml ./blitz_render/pyproject.toml
RUN uv sync --frozen --extra server --no-dev --no-install-project

COPY x_twitter_thread_dump ./x_twitter_thread_dump
RUN uv sync --frozen --extra server --no-dev

RUN uv run playwright install --with-deps chrome

# prebuilt in the rust stage, so the final image doesn't need a rust toolchain
# (installed after the last `uv sync`/`uv run`, which would otherwise remove it)
COPY --from=blitz-builder /wheels /tmp/wheels
RUN uv pip install --no-deps /tmp/wheels/*.whl && rm -rf /tmp/wheels

CMD ["uvicorn", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*", \
     "--host=0.0.0.0", \
     "--port=8000", \
     "--no-access-log", \
     "x_twitter_thread_dump._api:app"]
